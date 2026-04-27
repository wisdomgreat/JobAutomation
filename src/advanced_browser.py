import asyncio
import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import stealth

import config
from src.llm_provider import get_llm

logger = logging.getLogger(__name__)

class AdvancedBrowser:
    """
    Antigravity Advanced Browsing Engine (AABE).
    Uses Playwright and Accessibility Tree (AXTree) for semantic interaction.
    """

    def __init__(self, headless: bool = None):
        self.headless = headless if headless is not None else config.HEADLESS_BROWSER
        self.pw = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.llm = get_llm()
        self.user_data_dir = config.DATA_DIR / "playwright_profile"
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

    async def start(self):
        """Initialize the Playwright browser context."""
        if self.page:
            return

        self.pw = await async_playwright().start()
        
        # Launch with persistent context for sessions
        self.context = await self.pw.chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=self.headless,
            channel="chrome", # Prefer official chrome if available
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        self.page = self.context.pages[0]
        await stealth(self.page)
        
        # Standard timeouts
        self.page.set_default_timeout(30000)

    async def stop(self):
        """Clean up resources."""
        if self.context:
            await self.context.close()
        if self.pw:
            await self.pw.stop()
        self.page = None
        self.context = None
        self.browser = None
        self.pw = None

    async def get_ax_tree(self) -> Dict[str, Any]:
        """Extract the Accessibility Tree (AXTree) snapshot of the current page."""
        if not self.page:
            await self.start()
        
        # Capture AXTree
        snapshot = await self.page.accessibility.snapshot()
        return snapshot

    def _simplify_ax_tree(self, node: Dict[str, Any], depth: int = 0) -> Optional[Dict[str, Any]]:
        """Prune non-interactive or redundant nodes from the AXTree for LLM efficiency."""
        if depth > 15: # Depth limit
            return None

        # Keys we care about
        role = node.get("role", "")
        name = node.get("name", "").strip()
        
        # Keep interactive elements or those with names
        interactive_roles = ["button", "link", "textbox", "checkbox", "radio", "combobox", "listbox", "menuitem"]
        is_interactive = role in interactive_roles
        
        simplified_children = []
        for child in node.get("children", []):
            simplified_child = self._simplify_ax_tree(child, depth + 1)
            if simplified_child:
                simplified_children.append(simplified_child)

        if not is_interactive and not name and not simplified_children:
            return None

        result = {"role": role}
        if name: result["name"] = name
        if simplified_children: result["children"] = simplified_children
        
        # Add state info for interactive elements
        if is_interactive:
            for key in ["pressed", "checked", "disabled", "expanded", "focused"]:
                if key in node:
                    result[key] = node[key]

        return result

    async def plan_action(self, objective: str) -> Dict[str, Any]:
        """Ask the LLM to decide the next action based on the AXTree and objective."""
        raw_tree = await self.get_ax_tree()
        clean_tree = self._simplify_ax_tree(raw_tree)
        
        prompt = f"""
        Objective: {objective}
        Current Page URL: {self.page.url}
        
        Accessibility Tree:
        {json.dumps(clean_tree, indent=2)}
        
        Rules:
        1. Identify the element that most likely advances the objective.
        2. If you see a "Next", "Continue", or "Submit" button and the page seems filled, choose it.
        3. Return a JSON object with:
           - "action": "click" | "type" | "scroll" | "wait" | "complete"
           - "element_name": The exact 'name' of the element in the tree.
           - "value": (Only for 'type') The text to type.
           - "reason": Brief explanation of why this action was chosen.
        
        JSON Result:"""

        system_msg = "You are an expert web automation agent. You navigate complex job sites by understanding their semantic structure."
        
        response = self.llm.generate(prompt, system_prompt=system_msg)
        try:
            # Clean LLM response (handle markdown blocks)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            return json.loads(response)
        except Exception as e:
            logger.error(f"Failed to parse LLM action: {e} | Response: {response}")
            return {"action": "wait", "reason": "Error parsing AI command, retrying..."}

    async def execute_action(self, command: Dict[str, Any]):
        """Execute the command decided by the LLM."""
        action = command.get("action")
        name = command.get("element_name")
        value = command.get("value")

        print(f"  🤖 AABE Action: {action.upper()} on '{name}' - {command.get('reason')}")

        try:
            if action == "click":
                # Find element by accessible name
                loc = self.page.get_by_role(command.get("role", "button"), name=name)
                if await loc.count() == 0:
                    # Fallback: simple text match
                    loc = self.page.get_by_text(name, exact=False).first
                
                await loc.click()
                await self.page.wait_for_load_state("networkidle")
            
            elif action == "type":
                loc = self.page.get_by_label(name)
                if await loc.count() == 0:
                    loc = self.page.get_by_placeholder(name)
                if await loc.count() == 0:
                    loc = self.page.get_by_role("textbox", name=name)
                
                await loc.fill(value)
            
            elif action == "scroll":
                await self.page.mouse.wheel(0, 500)
            
            elif action == "wait":
                await asyncio.sleep(2)
            
            elif action == "complete":
                print("  ✓ Objective completed according to AABE.")

        except Exception as e:
            print(f"  ⚠ AABE Execution Error: {e}")

    async def navigate_to(self, url: str):
        """Navigate to a URL with human-like delays."""
        await self.start()
        await self.page.goto(url, wait_until="networkidle")
        await asyncio.sleep(random.uniform(1, 3))

    async def solve_application(self, apply_url: str, objective: str = "Apply to this job"):
        """Full autonomous loop to solve a job application."""
        await self.navigate_to(apply_url)
        
        max_steps = 20
        for step in range(max_steps):
            command = await self.plan_action(objective)
            if command.get("action") == "complete":
                break
            await self.execute_action(command)
            await asyncio.sleep(random.uniform(1, 2))
            
            # Check for bot checks
            if "verify you are human" in await self.page.content():
                print("  🚨 Bot challenge detected! Pause for manual resolution...")
                await asyncio.sleep(10) # Simple wait for now
