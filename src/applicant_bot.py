"""
Auto-Applicant Bot Module
Selenium-based bot for automatically applying to jobs on Indeed and LinkedIn.
Uses undetected-chromedriver to bypass Cloudflare and other anti-bot protections.
Falls back to guided mode for other platforms.
"""

import os
import sys
import time
import random
import logging
from pathlib import Path
from datetime import datetime
import json
import re
from typing import Optional
from urllib.parse import urlparse

# Add project root to path if running directly
sys.path.append(str(Path(__file__).parent.parent))

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    WebDriverException
)
from selenium.webdriver.common.action_chains import ActionChains
import subprocess

import config
from src.llm_provider import get_llm
from src.form_filler import auto_fill_page
from src.applicant_profile import ApplicantProfile


def _human_delay(min_s: float = 1.5, max_s: float = 4.0):
    """Sleep for a random duration to mimic human behavior. Respects STEALTH_MODE."""
    if config.STEALTH_MODE:
        time.sleep(random.uniform(min_s, max_s))
    else:
        time.sleep(random.uniform(0.1, 0.3))  # Minimal delay for speed mode


def _short_delay():
    """Short delay for quick actions."""
    if config.STEALTH_MODE:
        time.sleep(random.uniform(0.5, 1.5))
    else:
        time.sleep(random.uniform(0.05, 0.15))

def _slow_type(element, text: str, delay_range: tuple = (0.05, 0.2)):
    """Type into an element with human-like variability in speed."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(*delay_range))

def _safe_print(obj):
    """Print that handles Windows console encoding issues."""
    msg = str(obj)
    try:
        # Try to print normally
        print(msg)
    except UnicodeEncodeError:
        # Fallback: strip or replace non-encodable characters
        if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding:
            encoded = msg.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)
            print(encoded)
        else:
            # Absolute fallback: strip non-ascii
            print(msg.encode('ascii', errors='ignore').decode('ascii'))


# Directory for persistent browser sessions
SESSIONS_DIR = config.DATA_DIR / "browser_sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class ApplicantBot:
    """Base bot with shared browser functionality."""

    _chrome_version: Optional[int] = None  # Cached across all instances
    _browser_path: Optional[str] = None

    def __init__(self, profile_name: str = "default", profile: Optional[ApplicantProfile] = None):
        self.driver: Optional[uc.Chrome] = None
        self.profile_name = profile_name
        self.profile = profile or ApplicantProfile()
        self.profile_dir = SESSIONS_DIR / profile_name
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.breadcrumbs = []  # Last 10 actions/URLs
        self.last_action_time = time.time()
        self.browser_executable = self._find_browser_path()
        self.last_scroll_time = time.time()

    def _mimic_reading(self):
        """Randomly scroll and pause to look like a human reading a description."""
        try:
            self._log("Mimicking reading behavior (Stealth Phase 26.0)...")
            h = self.driver.execute_script("return document.body.scrollHeight")
            # Scroll down to a random point (30-70% of page)
            scroll_to = int(h * random.uniform(0.3, 0.7))
            self.driver.execute_script(f"window.scrollTo({{top: {scroll_to}, behavior: 'smooth'}});")
            _human_delay(2, 5) # Spend time 'reading'
            
            # Phase 28: Human-Parallelism Jitter
            for _ in range(random.randint(1, 3)):
                jitter = random.randint(-50, 50)
                self.driver.execute_script(f"window.scrollBy(0, {jitter});")
                time.sleep(random.uniform(0.2, 0.5))
            
            # Small wiggle
            self.driver.execute_script("window.scrollBy(0, 150);")
            _short_delay()
            self.driver.execute_script("window.scrollBy(0, -100);")
            _human_delay(1, 3)
            
            # Scroll back to top for the button search
            self.driver.execute_script("window.scrollTo({top: 0, behavior: 'smooth'});")
            _human_delay(1, 2)
        except:
            pass

    def _find_browser_path(self) -> Optional[str]:
        """Automatically find the Chrome/Edge/Brave executable on the system."""
        if ApplicantBot._browser_path:
            return ApplicantBot._browser_path

        # Priority list of browsers and paths
        if sys.platform == "win32":
            paths = [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
            
            # Phase 30.5: Registry Discovery Fallback
            try:
                import winreg
                for key in [r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"]:
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as k:
                            p, _ = winreg.QueryValueEx(k, "")
                            if p and os.path.exists(p):
                                paths.insert(0, p)
                    except: continue
            except: pass
        elif sys.platform == "darwin": # macOS
            paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            ]
        else: # Linux
            paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/microsoft-edge",
                "/usr/bin/brave-browser",
            ]

        for p in paths:
            if os.path.exists(p):
                ApplicantBot._browser_path = p
                return p
        
        return None

    def _log(self, message: str, level: str = "INFO"):

        """Log a message to breadcrumbs and potentially more."""
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        self.breadcrumbs.append(entry)
        if len(self.breadcrumbs) > 20:
            self.breadcrumbs.pop(0)
        
        # Phase 24: Enable console logging for better diagnostics
        _safe_print(f"  [grey42]{entry}[/]")

    @classmethod
    def _detect_chrome_version(cls) -> Optional[int]:
        """Auto-detect installed Chrome major version from Windows registry."""
        if cls._chrome_version is not None:
            return cls._chrome_version

        import subprocess
        try:
            result = subprocess.run(
                ['reg', 'query',
                 r'HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon',
                 '/v', 'version'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if 'version' in line.lower():
                        ver = line.strip().split()[-1]
                        cls._chrome_version = int(ver.split('.')[0])
                        return cls._chrome_version
        except Exception:
            pass

        try:
            result = subprocess.run(
                [r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--version'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                ver = result.stdout.strip().split()[-1]
                # Handle cases like "Google Chrome 145.0.7632.160" or just "145.0.7632.160"
                if '.' in ver:
                    cls._chrome_version = int(ver.split('.')[0])
                    return cls._chrome_version
        except Exception:
            pass

        return None

    def _create_driver(self) -> uc.Chrome:
        """Create an undetected Chrome browser with persistent profile, with retry logic."""
        def get_options():
            options = uc.ChromeOptions()
            options.add_argument("--no-first-run")
            options.add_argument("--no-service-autorun")
            options.add_argument("--password-store=basic")
            
            # Phase 25.1: Force remote debugging port to vary
            # options.add_argument(f"--remote-debugging-port={random.randint(9222, 9899)}")
            
            w = random.randint(1850, 1920)
            h = random.randint(950, 1080)
            options.add_argument(f"--window-size={w},{h}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            
            # Phase 36.1: Enhanced Stealth Headers
            options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
            options.add_argument("--lang=en-US,en;q=0.9")
            options.add_argument("--accept-lang=en-US,en;q=0.9")
            
            # Client Hints Masking
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            
            return options

        chrome_ver = self._detect_chrome_version()
        self._log(f"Detected Chrome major version: {chrome_ver}")
        
        # Phase 36.1: Version Anomaly Masking
        effective_ver = chrome_ver if (chrome_ver and chrome_ver < 140) else 123
        
        common_kwargs = {
            "user_data_dir": str(self.profile_dir),
            "headless": config.HEADLESS_BROWSER,
            "version_main": effective_ver,
            "browser_executable_path": self.browser_executable
        }
        
        # Phase 25.1: RETRY ENGINE (Up to 3 attempts)
        last_error = None
        for attempt in range(1, 4):
            try:
                if attempt > 1:
                    self._log(f"Retry attempt {attempt}/3 after failure...")
                    cleanup_browser_processes() # Aggressive clear between retries
                    time.sleep(2)

                # Use the options and pathing from common_kwargs but refresh each time
                kwargs = {**common_kwargs, "options": get_options()}
                
                driver = uc.Chrome(**kwargs)
                
                # Phase 36.3: Aggressive Identity Masking (CDP Force)
                # Overrides UA in both headers and JS to bypass UC's default v147 patches
                stable_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                
                driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                    "userAgent": stable_ua
                })
                
                # Mask navigator via CDP
                driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": f"Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}}); Object.defineProperty(navigator, 'userAgent', {{get: () => '{stable_ua}'}});"
                })
                
                driver.set_page_load_timeout(300)
                driver.set_script_timeout(120)
                return driver
                
            except Exception as e:
                last_error = e
                self._log(f"Browser start attempt {attempt} failed: {str(e)[:100]}")
                time.sleep(attempt * 2)

        raise RuntimeError(f"Failed to start browser after 3 attempts. Last error: {last_error}")

    def start(self):
        """Initialize the browser. Raises RuntimeError if it can't start."""
        if self.driver:
            return  # Already running
        self.driver = self._create_driver()

    def quit(self):
        """Close the browser (handles UC Windows cleanup errors)."""
        if self.driver:
            try:
                self.driver.quit()
            except (OSError, Exception):
                pass  # UC on Windows throws OSError on quit — safe to ignore
            self.driver = None

    def _move_mouse_to_element(self, element):
        """Move the mouse to an element with a randomized human-like curve and offset."""
        try:
            actions = ActionChains(self.driver)
            # Add randomized offset within the element
            width = element.size['width']
            height = element.size['height']
            offset_x = random.randint(-int(width/4), int(width/4))
            offset_y = random.randint(-int(height/4), int(height/4))
            
            # Move in multiple small steps to simulate a curve (simple version)
            # In a full premium version, we'd use Bezier curves
            actions.move_to_element_with_offset(element, offset_x, offset_y)
            actions.perform()
            time.sleep(random.uniform(0.1, 0.3)) # Human hesitation
        except Exception as e:
            self._log(f"Mouse move failed: {e}", level="DEBUG")
            pass

    def _wait_and_click(self, by: str, value: str, timeout: int = 10):
        """Wait for an element, move humanly, hover, then click."""
        for attempt in range(3):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((by, value))
                )
                
                # Humanize interaction
                self._move_mouse_to_element(element)
                _short_delay()
                
                # Double check enabled before click
                if element.is_enabled():
                    element.click()
                    return
            except StaleElementReferenceException:
                if attempt == 2: raise
                _short_delay()

    def _wait_and_type(self, by: str, value: str, text: str, timeout: int = 10, clear: bool = True):
        """Wait for an input element and type into it."""
        element = WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        _short_delay()
        if clear:
            element.clear()
        # Type character by character for more human-like behavior
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.02, 0.08))

    def _element_exists(self, by: str, value: str) -> bool:
        """Check if an element exists on the page."""
        try:
            self.driver.find_element(by, value)
            return True
        except NoSuchElementException:
            return False

    def _human_click(self, element):
        """Move mouse to element with random offset before clicking."""
        try:
            # Random offset to avoid clicking exact center every time
            w, h = element.size['width'], element.size['height']
            off_x = random.randint(-int(w/4), int(w/4))
            off_y = random.randint(-int(h/4), int(h/4))
            
            actions = ActionChains(self.driver)
            actions.move_to_element_with_offset(element, off_x, off_y)
            actions.pause(random.uniform(0.1, 0.4))
            actions.click()
            actions.perform()
        except Exception:
            # Fallback to direct script click if ActionChains fails
            try:
                self.driver.execute_script("arguments[0].click();", element)
            except: pass

    def _safe_click(self, element, max_retries: int = 3):
        """Try to click an element, handling common issues including stale references."""
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    self._human_click(element)
                else:
                    self.driver.execute_script("arguments[0].click();", element)
                return
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", element)
                return
            except StaleElementReferenceException:
                if attempt == max_retries - 1: raise
                _short_delay()

    def _scroll_modal_container(self):
        """Phase 27.5: Scavenge for lazy-loaded buttons inside the active modal."""
        try:
            self.driver.execute_script("""
                let modal = document.querySelector('.artdeco-modal__content, .jobs-easy-apply-modal, #indeed-modal-content');
                if (modal) {
                    modal.scrollTop = modal.scrollHeight;
                    return true;
                }
                window.scrollBy(0, 300); // Fallback to global scroll
                return false;
            """)
            _short_delay()
        except: pass

    def _find_nav_button(self):
        """
        Comprehensive button scanner that checks root and all iframes for
        'Next', 'Continue', 'Review', or 'Submit' buttons.
        """
        nav_selectors = [
            "//button[contains(@aria-label, 'Continue')]",
            "//button[contains(@aria-label, 'Review')]",
            "//button[contains(@aria-label, 'Submit')]",
            "//button[contains(@aria-label, 'next step')]",
            # Modern ID/Data Attributes
            "//button[@data-testid='indeed-apply-continue-button']",
            "//button[contains(@class, 'jobs-apply-button--top-card')]",
            "//button[contains(@class, 'artdeco-button--primary')]",
            "//button[contains(@class, 'artdeco-button--3')]",
            "//button[contains(@class, 'artdeco-button--secondary')]",
            # Priority selectors for modal interior
            "//button[contains(., 'Next')]",
            "//button[contains(., 'Review')]",
            "//button[contains(., 'Submit')]",
            "//button[contains(., 'Done')]",
            "//button[contains(., 'Continue')]",
            "//button[contains(., 'Save')]",
            "//*[@data-control-name='continue_unify']",
            "//*[@data-control-name='submit_unify']",
            "//*[contains(translate(text(), 'NEXT', 'next'), 'next')]/ancestor::button",
            "//*[contains(translate(text(), 'REVIEW', 'review'), 'review')]/ancestor::button",
            "//*[contains(translate(text(), 'SUBMIT', 'submit'), 'submit')]/ancestor::button",
            "//span[contains(text(), 'Next')]/ancestor::button",
            "//span[contains(text(), 'Review')]/ancestor::button",
            "//span[contains(text(), 'Submit')]/ancestor::button",
            "//div[contains(@class, 'artdeco-modal')]//button[contains(., 'Next')]",
        ]

        # 0. Try Shadow DOM buttons (Phase 12: common in newer Artdeco updates)
        try:
            shadow_btns = self.driver.execute_script("""
                var buttons = [];
                function findInShadow(root) {
                    if (!root) return;
                    if (root.tagName === 'BUTTON') buttons.push(root);
                    if (root.shadowRoot) findInShadow(root.shadowRoot);
                    for (var i = 0; i < root.childNodes.length; i++) {
                        findInShadow(root.childNodes[i]);
                    }
                }
                findInShadow(document.body);
                return buttons.filter(b => b.innerText.match(/Next|Continue|Review|Submit|Apply/i));
            """)
            if shadow_btns and len(shadow_btns) > 0:
                return shadow_btns[0]
        except: pass

        # 1. Check root document
        for xpath in nav_selectors:
            try:
                btns = self.driver.find_elements(By.XPATH, xpath)

                for btn in btns:
                    if btn.is_displayed():
                        # SANITIZATION: Skip decorative buttons (e.g., photo carousels)
                        btn_text = (btn.get_attribute("aria-label") or btn.text or "").lower()
                        # CRITICAL: "view next page" and "next photo" are carousel buttons, NOT modal buttons.
                        filter_terms = [
                            "photo", "image", "carousel", "slide", "member", 
                            "see more", "view next page", "next photo", 
                            "similar jobs", "browse", "previous", "previous photo"
                        ]
                        if any(term in btn_text for term in filter_terms):
                            continue
                        
                        # VERBOSE LOGGING:
                        self._log(f"Found navigation candidate: '{btn_text}'")
                        return btn
            except: continue

        # 2. Check all iframes
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        for i, iframe in enumerate(iframes):
            try:
                self.driver.switch_to.frame(iframe)
                for xpath in nav_selectors:
                    btns = self.driver.find_elements(By.XPATH, xpath)
                    for btn in btns:
                        if btn.is_displayed():
                            btn_text = (btn.get_attribute("aria-label") or btn.text or "").lower()
                            # Standardized filters for iframes too
                            filter_terms = [
                                "photo", "image", "carousel", "slide", "member", 
                                "see more", "view next page", "next photo", 
                                "similar jobs", "browse"
                            ]
                            if any(term in btn_text for term in filter_terms):
                                continue
                            self._log(f"Found navigation button in iframe #{i}: '{btn_text}'")
                            return btn
                self.driver.switch_to.default_content()
            except:
                self.driver.switch_to.default_content()
                continue

        # 3. Check Shadow DOMs (Experimental but necessary for modern web components)
        try:
            shadow_btns = self.driver.execute_script("""
                function findButtonsInShadows(root) {
                    let found = [];
                    let elements = root.querySelectorAll('*');
                    for (let el of elements) {
                        if (el.shadowRoot) {
                            found = found.concat(findButtonsInShadows(el.shadowRoot));
                            let btns = el.shadowRoot.querySelectorAll('button, [role="button"]');
                            for (let b of btns) {
                                if (b.offsetParent !== null) found.push(b);
                            }
                        }
                    }
                    return found;
                }
                return findButtonsInShadows(document);
            """)
            if shadow_btns:
                for btn in shadow_btns:
                    btn_text = (btn.get_attribute("aria-label") or btn.text or "").lower()
                    if any(kw in btn_text for kw in ["next", "continue", "review", "submit", "apply"]):
                        if not any(term in btn_text for term in ["photo", "carousel", "slide"]):
                            self._log(f"Found navigation button in Shadow DOM: '{btn_text}'")
                            return btn
        except: pass

        return None

    def _save_debug_info(self, prefix: str):
        """Saves a screenshot, page source, and breadcrumbs for debugging failures."""
        if not config.OUTPUT_DIR: return
        debug_dir = config.OUTPUT_DIR.parent / "debug"
        debug_dir.mkdir(exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{prefix}_{timestamp}"
        
        try:
            # 1. Screenshot
            self.driver.save_screenshot(str(debug_dir / f"{filename}.png"))
            
            # 2. Page Source (HTML)
            source = f"URL: {self.driver.current_url}\n\n"
            source += self.driver.page_source
            (debug_dir / f"{filename}.html").write_text(source, encoding="utf-8")
            
            # 3. Breadcrumbs (Logic Trace)
            trace = f"URL: {self.driver.current_url}\n"
            trace += "BREADCRUMBS:\n" + "\n".join(self.breadcrumbs)
            (debug_dir / f"{filename}_trace.txt").write_text(trace, encoding="utf-8")
            
            _safe_print(f"  📸 Debug info saved to {debug_dir.name}/{filename}.png")
        except Exception as e:
            _safe_print(f"  ⚠ Failed to save debug info: {e}")

    def _human_scroll(self):
        """Simulate human-like scrolling to trigger lazy loading."""
        try:
            h = self.driver.execute_script("return document.body.scrollHeight")
            # Random partial scrolls
            for _ in range(random.randint(2, 4)):
                scroll_to = random.randint(300, min(1200, h))
                self.driver.execute_script(f"window.scrollTo(0, {scroll_to});")
                _human_delay(0.5, 1.5)
            self.driver.execute_script("window.scrollTo(0, 0);")
        except:
            pass

    def _dismiss_popups(self):
        """Try to close common popups/banners that block buttons."""
        selectors = [
            "//button[contains(., 'Accept')]",
            "//button[contains(., 'Got it')]",
            "//button[contains(., 'Dismiss')]",
            "//button[contains(@aria-label, 'Dismiss')]",
            "//button[contains(@class, 'artdeco-modal__dismiss')]",
            "//button[contains(@class, 'cookie')]"
        ]
        for xpath in selectors:
            try:
                # Use a very short timeout
                btn = self.driver.find_element(By.XPATH, xpath)
                if btn.is_displayed():
                    _safe_print(f"  🧹 Dismissing popup: {btn.text[:20]}...")
                    self._safe_click(btn)
                    _human_delay(1, 2)
            except:
                continue
    
    def _check_for_bot_challenges(self):
        """Scans the page for common bot-check artifacts (Cloudflare, HCaptcha) and pauses for manual resolution."""
        challenge_selectors = [
            "//iframe[contains(@src, 'cloudflare')]",
            "//iframe[contains(@src, 'hcaptcha')]",
            "//div[contains(@class, 'cf-turnstile')]",
            "//h1[contains(text(), 'Verify you are human')]",
            "//title[contains(text(), 'Attention Required')]"
        ]
        for selector in challenge_selectors:
            try:
                if self.driver.find_elements(By.XPATH, selector):
                    self._log("🚨 Bot challenge detected! Pausing for manual resolution...", level="WARNING")
                    _safe_print("\n  [bold red]🚨 BOT CHALLENGE DETECTED![/]")
                    _safe_print("  [yellow]Please complete the CAPTCHA/Verification in the browser window.[/]")
                    _safe_print("  [yellow]The bot will resume automatically once the challenge is cleared.[/]")
                    
                    # Wait until the challenge is gone
                    start_wait = time.time()
                    while time.time() - start_wait < 300: # 5 minute max wait
                        time.sleep(5)
                        if not self.driver.find_elements(By.XPATH, selector):
                            self._log("✓ Bot challenge cleared. Resuming...")
                            return True
                    return False
            except: continue
        return True


class IndeedBot(ApplicantBot):
    """Automated Indeed Easy Apply bot."""

    def __init__(self, profile: Optional[ApplicantProfile] = None):
        super().__init__(profile_name="indeed", profile=profile)
        self.logged_in = False

    def _is_session_active(self) -> bool:
        """Check if we already have a valid Indeed session from a previous run."""
        try:
            self.driver.get("https://secure.indeed.com/settings")
            _human_delay(2, 3)
            # If we're not redirected to login, session is still active
            if "login" not in self.driver.current_url.lower():
                return True
        except Exception:
            pass
        return False

    def login(self) -> bool:
        """Log in to Indeed. Checks for saved session first."""
        if self.logged_in:
            return True

        self.start()

        # Check if previous session is still valid (saved cookies)
        _safe_print("  🔍 Checking for saved Indeed session...")
        if self._is_session_active():
            self.logged_in = True
            _safe_print("  ✓ Restored saved Indeed session (no login needed!)")
            return True

        if not config.INDEED_EMAIL or not config.INDEED_PASSWORD:
            _safe_print("  ✗ Indeed credentials not configured in .env")
            _safe_print("    Opening Indeed. Please log in manually in the browser window...")
            self.driver.get("https://secure.indeed.com/auth/login")
            input("    Press Enter after you have successfully logged in...")
            if self._is_session_active():
                self.logged_in = True
                return True
            return False

        _safe_print("  🔐 Logging in to Indeed (session will be saved for next time)...")

        try:
            self.driver.get("https://secure.indeed.com/account/login")
            _human_delay(2, 4)

            # Enter email
            self._wait_and_type(By.ID, "ifl-InputFormField-3", config.INDEED_EMAIL)
            _human_delay()

            # Click continue/submit
            try:
                self._wait_and_click(By.CSS_SELECTOR, "button[type='submit']")
            except TimeoutException:
                self._wait_and_click(By.XPATH, "//button[contains(text(), 'Continue')]")

            _human_delay(2, 4)

            # Enter password (if password field appears)
            try:
                self._wait_and_type(By.ID, "ifl-InputFormField-7", config.INDEED_PASSWORD, timeout=5)
                _human_delay()
                self._wait_and_click(By.CSS_SELECTOR, "button[type='submit']")
                _human_delay(3, 5)
            except TimeoutException:
                # May use different auth flow
                _safe_print("  ⚠ Password field not found. Indeed may require verification.")
                _safe_print("    Please complete login manually in the browser window.")
                _safe_print("    (Your session will be saved for future runs!)")
                input("    Press Enter when login is complete...")

            self.logged_in = True
            _safe_print("  ✓ Logged in to Indeed (session saved!)")
            return True

        except Exception as e:
            _safe_print(f"  ✗ Indeed login failed: {e}")
            return False

    def apply(self, apply_url: str, resume_path: str = "", cover_letter_path: str = "", resume_text: str = "", guided: bool = False) -> dict:
        """
        Apply to a job on Indeed. Handles both Easy Apply and external links.
        """
        result = {"success": False, "message": "Unknown failure"}

        if not self.login():
            result["message"] = "Login failed"
            return result

        try:
            _safe_print(f"  📋 Opening job page...")
            self.driver.get(apply_url)
            _human_delay(3, 5)

            # 1. Humanize & Cleanup
            self._dismiss_popups()
            self._human_scroll()
            
            # Phase 31.0: Indeed Iframe Switching Logic
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    if "indeed-apply-iframe" in (iframe.get_attribute("id") or "") or "indeed-apply-iframe" in (iframe.get_attribute("name") or ""):
                        self._log("Indeed Apply iframe detected. Switching context...")
                        self.driver.switch_to.frame(iframe)
                        break
            except: pass

            # 2. Check if already applied
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            if any(phrase in body_text for phrase in ["applied", "application sent", "view application"]):
                _safe_print("  ✓ Already applied to this job.")
                return {"success": True, "message": "Already applied"}

            # 3. Look for Easy Apply button with retry
            apply_button = None
            apply_selectors = [
                (By.CSS_SELECTOR, "#indeedApplyButton"),
                (By.CSS_SELECTOR, "button.indeed-apply-button"),
                (By.XPATH, "//button[contains(., 'Apply now')]"),
                (By.XPATH, "//button[contains(., 'Easy Apply')]"),
                (By.XPATH, "//button[contains(@aria-label, 'Apply')]"),
                (By.XPATH, "//span[contains(., 'Apply now')]/ancestor::button"),
            ]

            for attempt in range(2):
                for by, selector in apply_selectors:
                    try:
                        apply_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((by, selector))
                        )
                        if apply_button: break
                    except TimeoutException:
                        continue
                if apply_button: break
                if attempt == 0:
                    _safe_print("  ⚠ Indeed Apply button not found. Retrying with scroll...")
                    self._human_scroll()

            if not apply_button:
                # 4. Check for "Apply on company site"
                try:
                    # Look for both the text and the 'external' icon variants
                    ext_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Apply on company site')] | //a[contains(., 'Apply on company site')] | //button[contains(., 'Apply')] | //a[contains(., 'Apply')]")
                    
                    if "easy apply" not in ext_btn.text.lower():
                        _safe_print("  🔗 External application detected. Following link...")
                        self._safe_click(ext_btn)
                        _human_delay(3, 5)
                        return self._apply_external(resume_path, cover_letter_path, resume_text)
                except NoSuchElementException:
                    # Generic fallback
                    try:
                        apply_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Apply')] | //a[contains(., 'Apply')]")
                        if "easy apply" not in apply_btn.text.lower(): # Ensure it's not an Easy Apply button we missed
                            _safe_print("  🔗 Generic Apply button found on Indeed. Following...")
                            self._safe_click(apply_btn)
                            _human_delay(3, 5)
                            return self._apply_external(resume_path, cover_letter_path, resume_text)
                    except NoSuchElementException:
                        result["message"] = "No apply button found"
                        self._save_debug_info("indeed_no_apply")
                        return result

            # Click Easy Apply
            self._safe_click(apply_button)
            _human_delay(2, 4)

            # Handle the application wizard using form_filler
            max_steps = 15
            last_page_state = ""
            for step in range(max_steps):
                self._log(f"Handling Indeed step {step+1}...")
                _human_delay(1.5, 3.5) 
                
                # Check for stall
                current_state = self.driver.current_url + self.driver.page_source[:1000]
                if current_state == last_page_state and step > 0:
                    self._log("Stall detected: Page content hasn't changed. Attempting recovery...")
                    self._scroll_modal_container() # Phase 27.5 Scavenge
                    _human_delay(1, 2)
                last_page_state = current_state

                # Jittery scroll before filling
                if random.random() < 0.3: self._scroll_modal_container()
                
                auto_fill_page(
                    self.driver, 
                    self.profile.get_form_data(), 
                    resume_path, 
                    cover_letter_path, 
                    resume_text
                )

                # Phase 27.5: Use Unified Navigation Engine
                nav_btn = self._find_nav_button()
                if not nav_btn:
                    self._log("No navigation button found. Scavenging modal...")
                    self._scroll_modal_container()
                    nav_btn = self._find_nav_button()

                if nav_btn:
                    btn_text = (nav_btn.get_attribute("aria-label") or nav_btn.text or "").lower()
                    self._safe_click(nav_btn)
                    _human_delay(2, 3)
                    
                    if any(kw in btn_text for kw in ["submit", "finish", "done"]):
                        if guided:
                            self._log("GUIDED MODE: Application ready for submission. Please review in browser.")
                            _safe_print("\n  [bold yellow]✋ GUIDED STOP: Please review the application in the browser.[/]")
                            _safe_print("  [yellow]Click 'Submit' manually OR press ENTER here to let the bot click it...[/]")
                            input("  > Press Enter to continue (or manual click in browser)...")
                            
                        self._safe_click(nav_btn)
                        _human_delay(2, 3)
                        
                        if any(kw in btn_text for kw in ["submit", "finish", "done"]):
                            result["success"] = True
                            result["message"] = "Application submitted successfully"
                            _safe_print("  ✓ Indeed Application submitted!")
                            return result
                else:
                    self._log("Indeed navigation stalled: No 'Next' or 'Submit' button detected.")
                    if "application sent" in self.driver.page_source.lower():
                        result["success"] = True
                        return result
                    break

                if not clicked:
                    # Check if finished
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                    if any(phrase in body_text for phrase in ["applied", "submitted", "application sent"]):
                        result["success"] = True
                        result["message"] = "Application submitted"
                        return result
                    break

            return result

        except Exception as e:
            result["message"] = f"Indeed error: {str(e)}"
            return result

    def search(self, keywords: str, location: str, limit: int = 15) -> list[dict]:
        """Search for jobs on Indeed and return a list of job data."""
        self.start()
        self.login() 

        # sc=0kf%3Aattr%28V7L7S%29%3B is the "Apply with Indeed resume" filter (Easy Apply)
        # Using .com or .ca based on location or default to .com
        # Phase 28: Global Domain Resolver
        # Automatically detect and use the appropriate regional Indeed domain
        base_domain = "www.indeed.com"
        if "canada" in location.lower() or "ca" in location.lower(): base_domain = "ca.indeed.com"
        elif "uk" in location.lower() or "kingdom" in location.lower(): base_domain = "uk.indeed.com"
        elif "india" in location.lower() or "in" in location.lower(): base_domain = "in.indeed.com"
        elif "australia" in location.lower() or "au" in location.lower(): base_domain = "au.indeed.com"
        # Add more mappings as needed, default to .com
        
        search_url = f"https://{base_domain}/jobs?q={keywords}&l={location}&sc=0kf%3Aattr%28V7L7S%29%3B"
        
        _safe_print(f"  🔍 Searching Indeed: [cyan]{keywords}[/] in [cyan]{location}[/]")
        self.driver.get(search_url)
        _human_delay(3, 5)
        
        # Phase 35.0: Robust Search Trigger
        # Indeed sometimes populates but doesn't trigger search, or redirects to homepage
        try:
            # Check if we are actually on a results page or need to click search
            if not self._element_exists(By.CSS_SELECTOR, ".job_seen_beacon, .result"):
                self._log("Results not detected. Attempting to trigger search button...")
                
                # Check for "Find jobs" button
                search_btns = [
                    (By.CSS_SELECTOR, "button.yosegi-InlineWhatWhere-primaryButton"),
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.XPATH, "//button[contains(., 'Find jobs')]"),
                    (By.XPATH, "//button[contains(., 'Search')]")
                ]
                
                for by, sel in search_btns:
                    try:
                        btn = self.driver.find_element(by, sel)
                        if btn.is_displayed():
                            self._log(f"Triggering search button: {sel}")
                            self._safe_click(btn)
                            _human_delay(4, 6)
                            break
                    except: continue
        except Exception as e:
            self._log(f"Search trigger warning: {e}")

        # Final check: if still no results, try typing manually (Nuclear Option)
        if not self._element_exists(By.CSS_SELECTOR, ".job_seen_beacon, .result"):
            self._log("Total search stall. Attempting manual input injection...")
            try:
                self.driver.get(f"https://{base_domain}/")
                _human_delay(2, 4)
                self._wait_and_type(By.NAME, "q", keywords)
                _human_delay(0.5, 1)
                # Clear 'where' if needed
                loc_input = self.driver.find_element(By.NAME, "l")
                loc_input.send_keys(Keys.CONTROL + "a")
                loc_input.send_keys(Keys.DELETE)
                self._wait_and_type(By.NAME, "l", location)
                _human_delay(0.5, 1)
                loc_input.send_keys(Keys.ENTER)
                _human_delay(5, 8)
            except: pass

        jobs = []
        try:
            # Dismiss any popups that might block the view
            self._dismiss_popups()
            
            # Indeed specific selectors (2026 update)
            cards = self.driver.find_elements(By.CSS_SELECTOR, ".job_seen_beacon, .result, .cardOutline, [id^='job_']")
            for card in cards[:limit]:
                try:
                    title = "Untitled"
                    url = ""
                    # 1. Broad Title & URL detection
                    for sel in ["h2.jobTitle a", "a.jcs-JobTitle", "a[id^='job_']", "h2.jobTitle span", "span[id^='jobTitle']"]:
                        try:
                            el = card.find_element(By.CSS_SELECTOR, sel)
                            url = el.get_attribute("href")
                            text = el.get_attribute("title") or el.text
                            if text: title = text.strip().split('\n')[0]
                            if url: break
                        except: continue
                    
                    if not url:
                        try:
                            el = card.find_element(By.TAG_NAME, "a")
                            url = el.get_attribute("href")
                        except: pass

                    # 2. Robust Company Detection
                    company = "Unknown Company"
                    for sel in ["[data-testid='company-name']", ".companyName", ".css-1x7z1ps", ".company_location span", ".job-Snippet-company"]:
                        try:
                            co_el = card.find_element(By.CSS_SELECTOR, sel)
                            if co_el.text:
                                company = co_el.text.strip().split('\n')[0]
                                break
                        except: continue
                    
                    if url:
                        jobs.append({
                            "job_title": title,
                            "company": company,
                            "apply_url": url,
                            "source": "Indeed"
                        })
                except Exception: continue
        except Exception as e:
            _safe_print(f"  [red]Search error on Indeed: {e}[/]")

        return jobs

    def _apply_external(self, resume_path, cover_letter_path, resume_text) -> dict:
        """Helper to fill external forms reached via platform."""
        # This mirrors ExternalBot logic
        _human_delay(3, 5)
        # Switch to the new tab if Indeed opened one
        if len(self.driver.window_handles) > 1:
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
        _safe_print(f"  🤖 Filling external form at {self.driver.current_url[:50]}...")
        auto_fill_page(
            self.driver, 
            self.profile.get_form_data(), 
            resume_path, 
            cover_letter_path,
            resume_text
        )
        return {"success": False, "message": "External form filled. Please review and submit manually."}


class LinkedInBot(ApplicantBot):
    """Automated LinkedIn Easy Apply bot."""

    def __init__(self, profile: Optional[ApplicantProfile] = None):
        super().__init__(profile_name="linkedin", profile=profile)
        self.logged_in = False

    def _is_session_active(self) -> bool:
        """Check if we already have a valid LinkedIn session from a previous run."""
        try:
            self.driver.get("https://www.linkedin.com/feed/")
            _human_delay(2, 3)
            # If we're not redirected to login, session is still active
            if "login" not in self.driver.current_url.lower() and "authwall" not in self.driver.current_url.lower():
                return True
        except Exception:
            pass
        return False

    def login(self) -> bool:
        """Log in to LinkedIn. Checks for saved session first."""
        if self.logged_in:
            return True

        self.start()

        # Check if previous session is still valid (saved cookies)
        _safe_print("  🔍 Checking for saved LinkedIn session...")
        if self._is_session_active():
            self.logged_in = True
            _safe_print("  ✓ Restored saved LinkedIn session (no login needed!)")
            return True

        if not config.LINKEDIN_EMAIL or not config.LINKEDIN_PASSWORD:
            _safe_print("  ✗ LinkedIn credentials not configured in .env")
            _safe_print("    Opening LinkedIn. Please log in manually in the browser window...")
            self.driver.get("https://www.linkedin.com/login")
            input("    Press Enter after you have successfully logged in...")
            if self._is_session_active():
                self.logged_in = True
                return True
            return False

        _safe_print("  🔐 Logging in to LinkedIn (session will be saved for next time)...")
        try:
            # Add timeout recovery for frequent "renderer" hangs on LinkedIn
            try:
                self.driver.get("https://www.linkedin.com/login")
            except TimeoutException:
                self._log("Initial login page load timed out. Refreshing...")
                self.driver.refresh()
            
            _human_delay(2, 4)

            # Enter email
            self._wait_and_type(By.ID, "username", config.LINKEDIN_EMAIL)
            _human_delay(0.5, 1)

            # Enter password
            self._wait_and_type(By.ID, "password", config.LINKEDIN_PASSWORD)
            _human_delay(0.5, 1.5)

            # Click Sign in
            self._wait_and_click(By.CSS_SELECTOR, "button[type='submit']")
            _human_delay(3, 6)

            # Check for security verification
            if "challenge" in self.driver.current_url or "checkpoint" in self.driver.current_url:
                _safe_print("  ⚠ LinkedIn security challenge detected.")
                _safe_print("    Please complete verification in the browser window.")
                _safe_print("    (Your session will be saved for future runs!)")
                input("    Press Enter when verification is complete...")

            self.logged_in = True
            _safe_print("  ✓ Logged in to LinkedIn (session saved!)")
            return True

        except Exception as e:
            err_msg = str(e).split('\n')[0] if str(e) else type(e).__name__
            _safe_print(f"  ✗ LinkedIn login failed: {err_msg}")
            return False

    def _answer_question_with_llm(self, question_text: str, resume_text: str = "") -> str:
        """Use LLM to generate an answer for a screening question."""
        try:
            llm = get_llm()
            prompt = f"""Answer this job application screening question concisely and professionally.
            
Question: {question_text}

Candidate Background: {resume_text[:1000] if resume_text else 'Not provided'}

Rules:
- Keep answer brief (1-3 sentences max)
- Be professional and positive
- If it's a yes/no question, answer yes (assume candidate is qualified)
- If asking for years of experience, give a reasonable number based on the resume
- If asking about salary, say "Open to discussion" or "Flexible"
"""
            return llm.generate(prompt, "You are helping fill out a job application form. Be concise.")
        except Exception:
            return ""

    def apply(self, apply_url: str, resume_path: str = "", cover_letter_path: str = "", resume_text: str = "", guided: bool = False) -> dict:
        """
        Apply to a job on LinkedIn. Handles Easy Apply and external links.
        """
        result = {"success": False, "message": "Applying..."}

        if not self.login():
            result["message"] = "Login failed"
            return result

        try:
            self._log(f"Opening job page: {apply_url}")
            self.driver.get(apply_url)
            _human_delay(3, 5)
            
            # 1. Humanize & Cleanup
            self._dismiss_popups()
            self._mimic_reading() # Phase 26.0 Stealth

            # 2. Check for redirections or security challenges
            current_url = self.driver.current_url.lower()
            if "login" in current_url or "checkpoint" in current_url or "authwall" in current_url:
                self._log("Redirected to login/security challenge. Attempting fresh login...")
                if not self.login():
                    result["message"] = "LinkedIn re-login failed"
                    return result
                self.driver.get(apply_url)
                _human_delay(3, 5)

            # 2. Check if job is closed (Phase 23: Narrowed scope to avoid sidebar false positives)
            closed_indicators = [
                "no longer accepting applications",
                "this job is closed",
                "application for this job is closed",
                "not accepting responses"
            ]
            
            # Target the main job card/details specifically
            try:
                main_content = self.driver.find_element(By.CSS_SELECTOR, ".jobs-unified-top-card, .job-details, #main")
                main_text = main_content.text.lower()
                if any(indicator in main_text for indicator in closed_indicators):
                    self._log("Job is closed (detected in main content). Skipping.")
                    result["message"] = "Job closed"
                    return result
            except NoSuchElementException:
                # Fallback to broader check but ONLY if main container not found
                page_text = self.driver.page_source.lower()
                # Check for larger "This job is closed" banners that might be outside the top card
                if any(indicator in page_text[:5000] for indicator in closed_indicators):
                    self._log("Job is closed (detected in page start). Skipping.")
                    result["message"] = "Job closed"
                    return result

            # 3. Check if already applied (Refined Phase 32.4)
            try:
                # Look for explicit Artdeco indicators first
                top_card_indicators = self.driver.find_elements(By.CSS_SELECTOR, ".artdeco-inline-feedback--success, .jobs-s-apply--success")
                if top_card_indicators:
                    self._log("Already applied (detected via Artdeco success indicator).")
                    return {"success": True, "message": "Already applied"}
                
                top_card = self.driver.find_element(By.CSS_SELECTOR, ".jobs-unified-top-card, .job-details").text.lower()
                applied_indicators = ["applied", "application sent", "view application", "applied on"]
                # Only trust "applied" if it's not part of "applied for" or other phrases
                if any(phrase in top_card for phrase in applied_indicators):
                    # Final check: is there a prominent "Applied" badge?
                    if "applied" in top_card[:500]:
                       self._log("Already applied to this job.")
                       return {"success": True, "message": "Already applied"}
            except: pass

            # 4. Look for Easy Apply button
            easy_apply_btn = None
            selectors = [
                (By.CSS_SELECTOR, "button.jobs-apply-button"),
                (By.CSS_SELECTOR, "a.jobs-apply-button"),
                (By.XPATH, "//button[contains(@aria-label, 'Easy Apply')]"),
                (By.XPATH, "//a[contains(@aria-label, 'Easy Apply')]"), # Added link variant
                (By.XPATH, "//*[contains(text(), 'Easy Apply')]/ancestor::button"),
                (By.XPATH, "//*[contains(text(), 'Easy Apply')]/ancestor::a"), # Added link variant
                (By.XPATH, "//button[contains(., 'Easy Apply')]"),
                (By.XPATH, "//a[contains(., 'Easy Apply')]"), # Added link variant
                (By.XPATH, "//button[contains(., 'Apply')]"),
                (By.CSS_SELECTOR, "button[data-control-name='jobdetails_topcard_inapply']"),
                (By.XPATH, "//button[contains(@aria-label, 'Apply now')]"),
                (By.XPATH, "//button[contains(., 'Apply now')]"),
            ]

            for attempt in range(3):
                _safe_print(f"  🔍 Searching for apply button (attempt {attempt + 1}/3)...")
                for by, sel in selectors:
                    try:
                        btns = self.driver.find_elements(by, sel)
                        for btn in btns:
                            if btn.is_displayed() and btn.is_enabled():
                                # Scroll to it to make sure it's actually interactable
                                try:
                                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", btn)
                                    _short_delay()
                                except: pass

                                btn_text = btn.text.lower().strip()
                                if "easy apply" in btn_text or "apply now" in btn_text:
                                    easy_apply_btn = btn
                                    break
                                elif attempt == 2: # Last resort: any button that just says "Apply"
                                    easy_apply_btn = btn
                                    break
                        if easy_apply_btn: break
                    except: continue
                
                if easy_apply_btn: break
                
                if attempt == 0:
                    self._human_scroll()
                elif attempt == 1:
                    self._log("Easy Apply button not found. Refreshing page...")
                    self.driver.refresh()
                    _human_delay(3, 5)
                
                _human_delay(1, 2)

            if not easy_apply_btn:
                # Check for External Apply
                try:
                    ext_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Apply')] | //a[contains(., 'Apply')]")
                    if "easy apply" not in ext_btn.text.lower():
                        self._log("External Apply button detected.")
                        self._safe_click(ext_btn)
                        return self._apply_external(resume_path, cover_letter_path, resume_text)
                except: pass
                
                result["message"] = "No apply button found"
                self._save_debug_info("linkedin_no_apply")
                return result

            # 5. Click Easy Apply
            self._log(f"Clicking Easy Apply button: {easy_apply_btn.text.strip()}")
            self._safe_click(easy_apply_btn)
            _human_delay(2, 4)

            # 6. Handle Modal Wizard
            max_steps = 15
            modal_selectors = [
                "//div[contains(@class, 'jobs-easy-apply-modal')]",
                "//div[contains(@role, 'dialog') and .//*[contains(text(), 'Apply')]]",
                "//div[contains(@id, 'artdeco-modal-container')]"
            ]

            last_page_state = ""
            for step in range(max_steps):
                self._log(f"Handling LinkedIn step {step+1}...")
                _human_delay(1.5, 4.0)

                # 6.1 Identify Modal
                current_modal = None
                for selector in modal_selectors:
                    try:
                        m = self.driver.find_elements(By.XPATH, selector)
                        if m and m[0].is_displayed():
                            current_modal = m[0]
                            break
                    except: continue

                if not current_modal and step > 0:
                    if any(kw in self.driver.page_source.lower() for kw in ["application was sent", "successfully applied"]):
                        self._log("Application sent successfully!")
                        result["success"] = True
                        result["message"] = "Applied"
                        return result

                # 6.2 Check for external redirects (New Tab)
                if len(self.driver.window_handles) > 1:
                    self._log("New tab detected during modal step. Handling as external redirect...")
                    return self._apply_external(resume_path, cover_letter_path, resume_text)

                # 6.3 Check for stall using modal text
                current_state = "".join([e.text for e in self.driver.find_elements(By.TAG_NAME, "h3")]) + \
                                "".join([e.text for e in self.driver.find_elements(By.CSS_SELECTOR, "div.pb4")])
                
                stall_count = getattr(self, "_stall_count", 0)
                if current_state == last_page_state and step > 0:
                    stall_count += 1
                    self._stall_count = stall_count
                    self._log(f"Stall detected ({stall_count}/3): Modal content hasn't changed.")
                    
                    if stall_count >= 3:
                        self._log("Hard stall: Modal refused to advance after 3 attempts.")
                        # Phase 28: Attempt one last "Total AI Overhaul" fill before giving up
                        self._log("Attempting Emergency Smart AI Analysis...")
                        from src.form_filler import smart_analyze_page
                        smart_data = smart_analyze_page(self.driver, self.profile.get_form_data(), resume_text)
                        if smart_data:
                            for sel, val in smart_data.items():
                                try:
                                    el = self.driver.find_element(By.CSS_SELECTOR, sel)
                                    if el.is_displayed():
                                        el.send_keys(val)
                                except: pass
                        
                        self._save_debug_info("linkedin_hard_stall")
                        return {"success": False, "message": "Stuck in modal (Hard Stall)"}
                    
                    from src.form_filler import auto_fill_page
                    
                    # 6.2.1 Check for errors
                    error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".artdeco-inline-feedback--error, .fb-form-element__error")
                    visible_errors = [e.text.strip() for e in error_elements if e.is_displayed()]
                    
                    if visible_errors:
                        self._log(f"Validation errors detected: {visible_errors}")
                    
                    # Phase 12: Always try a re-fill on stall, even if no explicit error
                    # This handles fields that are left blank but don't show red yet.
                    auto_fill_page(self.driver, self.profile.get_form_data(), resume_path, cover_letter_path, resume_text)
                    
                    # Scroll and Wait
                    self.driver.execute_script("window.scrollBy(0, 150);")
                    _human_delay(1, 2)
                else:
                    self._stall_count = 0 # Reset on progress
                last_page_state = current_state

                # 6.3 Proactive Fill
                # Fill on every step because LinkedIn often leaves 'Next' enabled even with missing fields
                self._log("Proactively filling fields for this step...")
                from src.form_filler import auto_fill_page
                
                # Phase 28: Force Resume Step Logic
                # If the modal contains "resume", we want to ensure we "Upload" the new one
                modal_text = self.driver.find_element(By.CSS_SELECTOR, ".jobs-easy-apply-modal").text.lower()
                if "resume" in modal_text and resume_path:
                    try:
                        # Check if "Upload resume" button exists and click it to reveal the input
                        upload_btns = self.driver.find_elements(By.XPATH, "//button[contains(., 'Upload resume')]")
                        for btn in upload_btns:
                            if btn.is_displayed():
                                self._log("Forcing tailored resume upload...")
                                self.driver.execute_script("arguments[0].click();", btn)
                                _short_delay()
                                break
                    except: pass

                auto_fill_page(self.driver, self.profile.get_form_data(), resume_path, cover_letter_path, resume_text)
                _human_delay(1, 2)

                # 6.4 Find and Click Navigation
                nav_btn = self._find_nav_button()
                if not nav_btn:
                    if any(kw in self.driver.page_source.lower() for kw in ["application was sent", "successfully applied"]):
                        result["success"] = True
                        result["message"] = "Applied"
                        return result
                    self._log("No navigation button found in modal.")
                    self._save_debug_info("linkedin_modal_stuck")
                    result["message"] = "Stuck in modal"
                    return result

                btn_text = (nav_btn.get_attribute("aria-label") or nav_btn.text or "").lower()
                self._log(f"Step {step+1}: Found button '{btn_text}'")

                # Handle disabled button (missing required fields)
                if not nav_btn.is_enabled() or "disabled" in (nav_btn.get_attribute("class") or "").lower():
                    self._log("Button is disabled after proactive fill. Attempting one more fill...")
                    auto_fill_page(self.driver, self.profile.get_form_data(), resume_path, cover_letter_path, resume_text)
                    _human_delay(1, 2)
                    
                    if not nav_btn.is_enabled() or "disabled" in (nav_btn.get_attribute("class") or "").lower():
                        self._log("Button remains disabled. Modal requires manual intervention or LLM can't handle.")
                        self._save_debug_info("linkedin_modal_stalled_required")
                        result["message"] = "Required fields missing"
                        return result

                # Click button
                for click_attempt in range(3):
                    try:
                        nav_btn.click()
                        break
                    except Exception:
                        try:
                            self.driver.execute_script("arguments[0].click();", nav_btn)
                            break
                        except Exception as e:
                            if click_attempt == 2: self._log(f"Failed all click strategies: {e}")

                _human_delay(2, 4)
                
                # Phase 32.4 Stability: Ensure we're in the right context
                try:
                    self.driver.switch_to.default_content()
                except: pass

                # 6.5 Post-Click Validation
                try:
                    error_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.artdeco-inline-feedback--error, .fb-form-element__error")
                    visible_errors = [e.text.strip() for e in error_elements if e.is_displayed()]
                    if visible_errors:
                        self._log(f"Validation errors after click: {', '.join(visible_errors)[:100]}")
                        auto_fill_page(self.driver, self.profile.get_form_data(), resume_path, cover_letter_path, resume_text)
                except: pass

                if "submit" in btn_text or "post-apply" in btn_text or "apply" in btn_text:
                    # Final check if modal closed or shows success
                    _human_delay(3, 5)
                    success_phrases = ["application was sent", "successfully applied", "thank you for applying"]
                    page_src = self.driver.page_source.lower()
                    if any(p in page_src for p in success_phrases):
                        self._log("Application sent successfully!")
                        return {"success": True, "message": "Applied"}
                    
                    if guided:
                        self._log("GUIDED MODE: LinkedIn Application ready. Please review.")
                        _safe_print("\n  [bold yellow]✋ GUIDED STOP: Please review the application in the browser.[/]")
                        input("  > Press Enter to continue and submit...")
                        
                    self._log("Submit clicked. Waiting for final confirmation...")
                    _human_delay(2, 5)
                    # Even if success text not found, if modal is gone, it's likely a win
                    result["success"] = True
                    result["message"] = "Applied"
                    return result

            result["message"] = "Max steps reached in modal"
            return result

        except Exception as e:
            self._log(f"Crash in LinkedIn apply: {e}")
            self._save_debug_info("linkedin_apply_crash")
            result["message"] = f"Crash: {str(e).splitlines()[0]}"
            return result

    def search(self, keywords: str, location: str, limit: int = 15) -> list[dict]:
        """Search for jobs on LinkedIn and return a list of job data."""
        self.start()
        if not self.login():
            return []

        # f_AL=true filters for Easy Apply
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}&f_AL=true"
        _safe_print(f"  🔍 Searching LinkedIn: [cyan]{keywords}[/] in [cyan]{location}[/]")
        self.driver.get(search_url)
        _human_delay(5, 8)
        
        # Phase 35.1: Global Search Trigger (LinkedIn)
        try:
            if not self._element_exists(By.CSS_SELECTOR, ".job-card-container, .jobs-search-results-list__list-item"):
                self._log("LinkedIn results stalled. Clicking search trigger...")
                trigger = self.driver.find_element(By.CSS_SELECTOR, "button.jobs-search-box__submit-button, button[type='submit']")
                self._safe_click(trigger)
                _human_delay(4, 6)
        except: pass
        
        jobs = []
        try:
            # Dismiss any popups/cookie banners
            self._dismiss_popups()
            
            # Scroll the results list to load more
            try:
                results_container = self.driver.find_element(By.CSS_SELECTOR, ".jobs-search-results-list")
                for _ in range(3):
                    self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_container)
                    _human_delay(1, 2)
            except: pass
            
            # Find job cards
            cards = self.driver.find_elements(By.CSS_SELECTOR, ".job-card-container, .jobs-search-results-list__list-item")
            for card in cards[:limit]:
                try:
                    # Extract title and URL
                    title = "Untitled"
                    url = ""
                    for sel in ["a.job-card-container__link", "a.job-card-list__title", ".job-card-list__title a", ".job-card-container__title"]:
                        try:
                            link_el = card.find_element(By.CSS_SELECTOR, sel)
                            url = link_el.get_attribute("href")
                            if url: url = url.split("?")[0]
                            
                            # Try multiple ways to get the title text 
                            # .text might be empty if not visible or icon-only
                            t = link_el.get_attribute("aria-label") or link_el.text
                            if not t:
                                # Try specifically for spans or inner text
                                try:
                                    t = link_el.find_element(By.CSS_SELECTOR, "span, strong").text
                                except: pass
                            
                            if t:
                                title = t.strip().split('\n')[0]
                                break
                        except: continue
                    
                    if not url: continue
                    
                    # Company name
                    company = "Unknown Company"
                    for sel in [".job-card-container__company-name", ".artdeco-entity-lockup__subtitle", ".job-card-container__primary-description", ".job-card-container__company-link"]:
                        try:
                            company_el = card.find_element(By.CSS_SELECTOR, sel)
                            t = company_el.get_attribute("aria-label") or company_el.text
                            if t:
                                company = t.strip().split('\n')[0]
                                break
                        except: continue
                    
                    jobs.append({
                        "job_title": title,
                        "company": company,
                        "apply_url": url,
                        "source": "LinkedIn"
                    })
                except Exception: continue
        except Exception as e:
            _safe_print(f"  [red]Search error on LinkedIn: {e}[/]")
            
        return jobs

    def _apply_external(self, resume_path, cover_letter_path, resume_text) -> dict:
        """Helper to fill external forms reached via LinkedIn."""
        self._log("Waiting for external redirect...")
        
        # Phase 28: Improved Tab Detection Logic
        start_time = time.time()
        found_redirect = False
        while time.time() - start_time < 15:
            # Check for new tabs
            if len(self.driver.window_handles) > 1:
                self._log("Switching to new tab...")
                self.driver.switch_to.window(self.driver.window_handles[-1])
                found_redirect = True
                break
                
            # Check for same-tab URL changes
            current_url = self.driver.current_url.lower()
            if "linkedin.com" not in current_url:
                found_redirect = True
                break
                
            time.sleep(1)
            
        if not found_redirect:
             self._log("Warning: No clear redirect detected. Attempting to scan current page anyway.")
            
        # Final safety check
        if "linkedin.com" in self.driver.current_url.lower() and "/jobs/view/" in self.driver.current_url:
             return {"success": False, "message": "Failed to redirect away from LinkedIn"}

        # Use the powerful ExternalBot engine to handle the company site
        ext_bot = ExternalBot(profile_name="external_redir", profile=self.profile)
        ext_bot.driver = self.driver # Share the driver
        return ext_bot.apply(self.driver.current_url, resume_path, cover_letter_path, resume_text, guided=guided)


class ExternalBot(ApplicantBot):
    """Bot for handling applications on any external website."""

    def apply(self, apply_url: str, resume_path: str = "", cover_letter_path: str = "", resume_text: str = "", guided: bool = False) -> dict:
        """Navigate to any URL and attempt to fill the application form."""
        self.start()
        _safe_print(f"  🌐 Navigating to {apply_url[:50]}...")
        self.driver.get(apply_url)
        _human_delay(4, 6)

        try:
            # Multi-page form handling
            max_steps = 12
            recent_urls = []
            
            for step in range(max_steps):
                _human_delay(2, 4)
                current_url = self.driver.current_url
                self._log(f"Handling external page {step+1}: {current_url}")
                
                # Phase 27.3: Domain Safety Check (Prevent LinkedIn Loops)
                if any(domain in current_url.lower() for domain in ["linkedin.com", "indeed.com"]):
                    if "/jobs/view/" in current_url or "/viewjob" in current_url:
                        self._log("Critical: ExternalBot trapped on major platform page. Aborting loop.")
                        break

                _safe_print(f"  🤖 Analyzing company page {step+1}...")
                
                # EXPLORATION: Scroll down and up to trigger lazy-loaded components
                self._human_scroll()
                _human_delay(1, 2)
                # 0. Check for Success
                body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                if any(phrase in body_text for phrase in ["applied", "submitted", "thank you", "received", "success"]):
                    return {"success": True, "message": "External application submitted!"}

                # 1. LOOP DETECTION
                recent_urls.append(current_url)
                if len(recent_urls) > 3:
                    recent_urls.pop(0)
                    if len(set(recent_urls)) == 1:
                        # Attempt a scroll to reveal more if stuck
                        self._human_scroll()
                        _human_delay(1, 2)

                # 2. PROACTIVE FORM FILLING
                filled = auto_fill_page(
                    self.driver, 
                    self.profile.get_form_data(), 
                    resume_path, 
                    cover_letter_path,
                    resume_text
                )
                self._log(f"Filled {filled} fields")
                
                # 3. TRANSITION & NAVIGATION
                clicked_action = False
                
                # Check for loading spinners first
                try:
                    spinners = self.driver.find_elements(By.CSS_SELECTOR, "[class*='spinner'], [class*='loading'], .wait-overlay")
                    if any(s.is_displayed() for s in spinners):
                        self._log("Spinner detected, waiting...")
                        time.sleep(3)
                except: pass

                # Try Transition Buttons (Apply, Start, I am interested)
                transition_selectors = [
                    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
                    "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
                    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'interested')]",
                    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'start')]",
                    "//button[contains(., 'Upload')]",
                    "//button[contains(., 'Select File')]",
                    "//*[@data-automation='apply-button']",
                    "//*[contains(text(), 'Apply Now')]/ancestor::button",
                    # Greenhouse / Lever common patterns
                    "//a[contains(@class, 'button') and contains(., 'Apply')]",
                    "//button[contains(@class, 'primary')]",
                ]
                
                for xpath in transition_selectors:
                    try:
                        btn = self.driver.find_element(By.XPATH, xpath)
                        if btn.is_displayed():
                            btn_text = btn.text.lower()
                            if any(bad in btn_text for bad in ["privacy", "cookies", "terms"]): continue
                            
                            self._log(f"Clicking: {btn_text[:20]}")
                            self._safe_click(btn)
                            clicked_action = True
                            _human_delay(3, 5)
                            break
                    except: continue

                # Try Navigation (Next, Continue, Review, Submit)
                if not clicked_action:
                    nav_selectors = [
                        "//button[contains(., 'Continue')]",
                        "//button[contains(., 'Next')]",
                        "//button[contains(., 'Review')]",
                        "//button[contains(., 'Submit')]",
                        "//button[contains(., 'Finish')]",
                        "//button[contains(@class, 'submit')]",
                        "//input[@type='submit']",
                        "//button[contains(translate(., 'NEXT', 'next'), 'next')]"
                    ]
                    for xpath in nav_selectors:
                        try:
                            btn = self.driver.find_element(By.XPATH, xpath)
                            if btn.is_displayed():
                                self._log(f"Navigating: {btn.text[:20]}")
                                self._safe_click(btn)
                                clicked_action = True
                                _human_delay(3, 5)
                                break
                        except: continue

                if not clicked_action and step > 1:
                    break # No more actions found
            
            return {"success": False, "message": "External form handled. Please review manually."}
        except Exception as e:
            return {"success": False, "message": f"External bot error: {e}"}




# ── Specialized Platform Bots ────────────────────────────────
class ZipRecruiterBot(ExternalBot):
    def __init__(self, profile: Optional[ApplicantProfile] = None):
        super().__init__(profile_name="ziprecruiter", profile=profile)

    def search(self, keywords: str, location: str, limit: int = 15) -> list[dict]:
        self.start()
        
        # Phase 36.2: Interactive Home Navigation (Stealth Upgrade)
        self.driver.get("https://www.ziprecruiter.com/")
        _human_delay(3, 5)
        
        try:
            # Dismiss any "Are you a business?" overlays
            self._dismiss_popups()
            
            # Phase 36.4: Resilient Input Discovery
            def get_inputs():
                # Attempt 1: Specific Name/ID
                try:
                    kw = self.driver.find_element(By.NAME, "search")
                    loc = self.driver.find_element(By.NAME, "location")
                    return kw, loc
                except: pass

                # Attempt 2: Placeholder Match
                try:
                    inputs = self.driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])")
                    kw, loc = None, None
                    for i in inputs:
                        ph = (i.get_attribute("placeholder") or "").lower()
                        if "job" in ph or "keyword" in ph or "title" in ph: kw = i
                        if "city" in ph or "location" in ph or "zip" in ph or "where" in ph: loc = i
                    if kw and loc: return kw, loc
                except: pass

                # Attempt 3: Positional Fallback (Left is Keywords, Right is Location)
                try:
                    vis_inputs = [i for i in self.driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])") if i.is_displayed()]
                    if len(vis_inputs) >= 2:
                        return vis_inputs[0], vis_inputs[1]
                except: pass
                
                return None, None

            kw_input, loc_input = get_inputs()
            
            if kw_input and loc_input:
                # Perform human-like entry with JS Fallback
                self.driver.execute_script("arguments[0].scrollIntoView();", kw_input)
                kw_input.click()
                _short_delay()
                
                # Double-tap: Standard typing + JS Force
                kw_input.send_keys(Keys.CONTROL + "a")
                kw_input.send_keys(Keys.BACKSPACE)
                _slow_type(kw_input, keywords)
                self.driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', { bubbles: true })); arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", kw_input, keywords)
                _short_delay()
                
                loc_input.click()
                loc_input.send_keys(Keys.CONTROL + "a")
                loc_input.send_keys(Keys.BACKSPACE)
                _slow_type(loc_input, location)
                self.driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', { bubbles: true })); arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", loc_input, location)
                _human_delay(1, 2)
                
                # Submit via the button to trigger analytics correctly
                submit_btn = None
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .search_button")
                except:
                    try:
                        submit_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Search')]")
                    except: pass
                
                if submit_btn:
                    self._safe_click(submit_btn)
                else:
                    loc_input.send_keys(Keys.ENTER)
                
                _human_delay(4, 7)
            else:
                self._log("Search inputs not found. Fallback to direct navigation.")
                search_url = f"https://www.ziprecruiter.com/jobs-search?search={keywords}&location={location}"
                self.driver.get(search_url)
                _human_delay(4, 6)
            
            # Detect Cloudflare/Block Page
            if "just a moment" in self.driver.title.lower() or "verify you are human" in self.driver.page_source.lower():
                _safe_print("  [bold red]⚠️  Security Block: ZipRecruiter requires manual Human Verification.[/]")
                time.sleep(10)
                
        except Exception as e:
            self._log(f"Search trigger failed: {e}")
            search_url = f"https://www.ziprecruiter.com/jobs-search?search={keywords}&location={location}"
            self.driver.get(search_url)
            _human_delay(4, 6)
            
        jobs = []
        try:
            # 2026 Resilient Selectors
            selectors = [
                ".job_content", 
                ".job_result", 
                "article.job_result",
                "[data-testid='job-list-item']",
                ".job_card"
            ]
            cards = []
            for sel in selectors:
                cards = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if cards: break
                
            for card in cards[:limit]:
                try:
                    # Robust extraction cluster
                    title = "Untitled Role"
                    for ts in [".job_title", "h2", "h3", ".title"]:
                        try:
                            el = card.find_element(By.CSS_SELECTOR, ts)
                            if el.text.strip():
                                title = el.text.strip()
                                break
                        except: continue
                    
                    company = "Unknown Company"
                    for cs in [".company_name", ".name", ".company_location", "span[class*='company']"]:
                        try:
                            el = card.find_element(By.CSS_SELECTOR, cs)
                            if el.text.strip():
                                company = el.text.strip().split('\n')[0]
                                break
                        except: continue
                        
                    url = card.find_element(By.TAG_NAME, "a").get_attribute("href")
                    if url:
                        jobs.append({"job_title": title, "company": company, "apply_url": url, "source": "ZipRecruiter"})
                except: continue
        except: pass
        return jobs

class DiceBot(ExternalBot):
    def __init__(self, profile: Optional[ApplicantProfile] = None):
        super().__init__(profile_name="dice", profile=profile)

    def search(self, keywords: str, location: str, limit: int = 15) -> list[dict]:
        self.start()
        search_url = f"https://www.dice.com/jobs?q={keywords}&l={location}"
        self.driver.get(search_url)
        _human_delay(4, 6)
        
        # Phase 35.1: Global Search Trigger (Dice)
        try:
            if not self._element_exists(By.CSS_SELECTOR, "d-job-card"):
                self._log("Dice results stalled. Clicking search trigger...")
                trigger = self.driver.find_element(By.ID, "submitSearch-button")
                self._safe_click(trigger)
                _human_delay(4, 6)
        except: pass
        jobs = []
        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR, "d-job-card, .search-results-list .card, .current-job-card")
            for card in cards[:limit]:
                try:
                    title_el = card.find_element(By.CSS_SELECTOR, "a.card-title-link, h3 a, [data-cy='card-title-link']")
                    title = title_el.text.strip()
                    url = title_el.get_attribute("href")
                    # Try to find company via link or text span
                    try:
                        company = card.find_element(By.CSS_SELECTOR, "a.card-company-link, .company-name, [data-cy='card-company-link']").text.strip()
                    except:
                        company = "Unknown"
                    if url:
                        jobs.append({"job_title": title, "company": company, "apply_url": url, "source": "Dice"})
                except: continue
        except: pass
        return jobs

class WellfoundBot(ExternalBot):
    def __init__(self, profile: Optional[ApplicantProfile] = None):
        super().__init__(profile_name="wellfound", profile=profile)

    def search(self, keywords: str, location: str, limit: int = 15) -> list[dict]:
        self.start()
        search_url = f"https://wellfound.com/jobs?q={keywords}"
        self.driver.get(search_url)
        _human_delay(6, 10)
        
        # Phase 35.1: Global Search Trigger (Wellfound)
        try:
            if not self._element_exists(By.CSS_SELECTOR, "[data-test='JobListingCard']"):
                self._log("Wellfound results stalled. Pressing Enter to trigger...")
                # Wellfound results often trigger on Enter in the input
                act = self.driver.find_element(By.TAG_NAME, "body")
                act.send_keys(Keys.ENTER)
                _human_delay(5, 8)
        except: pass
        jobs = []
        try:
            # Phase 33.0: Deep Card Analysis for 2026/2026 dynamic UI
            selectors = [
                "[data-test='JobListingCard']",
                ".styles_result__",
                ".finding-jobs_jobCard__",
                "//div[contains(@class, 'job-card')]",
                "//div[contains(@aria-label, 'Job listing')]"
            ]
            
            cards = []
            for sel in selectors:
                if sel.startswith("//"):
                    cards = self.driver.find_elements(By.XPATH, sel)
                else:
                    cards = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if cards: break

            for card in cards[:limit]:
                try:
                    # Extraction cluster with robust fallbacks
                    title_sel = ["[data-test='JobTitle']", "h3", ".styles_jobTitle__", "h2", "a.title"]
                    company_sel = ["[data-test='CompanyLink']", ".styles_companyName__", "a.company", "div.name"]
                    
                    title = "Unknown Role"
                    for ts in title_sel:
                        try:
                            el = card.find_element(By.CSS_SELECTOR, ts)
                            if el.text.strip():
                                title = el.text.strip()
                                break
                        except: continue
                        
                    company = "Unknown Company"
                    for cs in company_sel:
                        try:
                            el = card.find_element(By.CSS_SELECTOR, cs)
                            if el.text.strip():
                                company = el.text.strip()
                                break
                        except: continue
                        
                    try:
                        url = card.find_element(By.TAG_NAME, "a").get_attribute("href")
                    except: url = None

                    if url and "/jobs/" in url:
                        jobs.append({"job_title": title, "company": company, "apply_url": url.split("?")[0], "source": "Wellfound"})
                except: continue
        except: pass
        return jobs

class IPRecruiterBot(ExternalBot):
    """Specialized Bot for iprecruiter.com and similar niche niche niches."""
    def __init__(self, profile: Optional[ApplicantProfile] = None):
        super().__init__(profile_name="iprecruiter", profile=profile)

    def search(self, keywords: str, location: str, limit: int = 15) -> list[dict]:
        self.start()
        # IPRecruiter often uses Google Jobs or a standard WP listing
        search_url = f"https://iprecruiter.com/?s={keywords}"
        self.driver.get(search_url)
        _human_delay(4, 6)
        jobs = []
        try:
            # Common patterns for iprecruiter / niche boards
            cards = self.driver.find_elements(By.CSS_SELECTOR, "article, .job-listing, .post, .entry")
            for card in cards[:limit]:
                try:
                    title_el = card.find_element(By.CSS_SELECTOR, "h2, h3, .title, a")
                    title = title_el.text.strip()
                    url = title_el.get_attribute("href") or card.find_element(By.TAG_NAME, "a").get_attribute("href")
                    if url and title:
                        jobs.append({"job_title": title, "company": "IP Recruiter", "apply_url": url, "source": "IPRecruiter"})
                except: continue
        except: pass
        return jobs

class BuiltInBot(ExternalBot):
    def __init__(self, profile: Optional[ApplicantProfile] = None):
        super().__init__(profile_name="builtin", profile=profile)

    def search(self, keywords: str, location: str, limit: int = 15) -> list[dict]:
        self.start()
        # Custom search redirect based on common BuiltIn patterns
        search_url = f"https://builtin.com/jobs?search={keywords}"
        self.driver.get(search_url)
        _human_delay(5, 8)
        
        # Phase 35.1: Global Search Trigger (BuiltIn)
        try:
            if not self._element_exists(By.CSS_SELECTOR, ".card-item, [data-id='job-card']"):
                self._log("BuiltIn results stalled. Clicking search trigger...")
                trigger = self.driver.find_element(By.CSS_SELECTOR, "button.search-btn, button[type='submit']")
                self._safe_click(trigger)
                _human_delay(4, 6)
        except: pass
        jobs = []
        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR, ".card-item, [data-id='job-card']")
            for card in cards[:limit]:
                try:
                    title = card.find_element(By.CSS_SELECTOR, ".job-title, h2").text.strip()
                    company = card.find_element(By.CSS_SELECTOR, ".company-name, .company-title").text.strip()
                    url = card.find_element(By.TAG_NAME, "a").get_attribute("href")
                    if url:
                        jobs.append({"job_title": title, "company": company, "apply_url": url.split("?")[0], "source": "BuiltIn"})
                except: continue
        except: pass
        return jobs

# ── Singleton Bot Manager ────────────────────────────────────
# One browser per platform, reused across all jobs in a session.

_active_bots: dict[str, ApplicantBot] = {}


def _get_platform(url: str) -> str:
    """Identify platform from URL using robust parsing."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Exact domain match or subdomains
        if domain == "indeed.com" or domain.endswith(".indeed.com"):
            return "indeed"
        if domain == "linkedin.com" or domain.endswith(".linkedin.com"):
            return "linkedin"
        if domain == "ziprecruiter.com" or domain.endswith(".ziprecruiter.com"):
            return "ziprecruiter"
        if domain == "dice.com" or domain.endswith(".dice.com"):
            return "dice"
        if domain == "wellfound.com" or domain.endswith(".wellfound.com") or domain == "angel.co":
            return "wellfound"
        if domain == "builtin.com" or domain.endswith(".builtin.com"):
            return "builtin"
        if "iprecruiter.com" in domain:
            return "iprecruiter"
    except Exception:
        pass
        
    return "other"


def get_bot(url: str, platform: Optional[str] = None) -> ApplicantBot:
    """
    Get or create a bot for the given URL's platform.
    Reuses existing browser sessions — never creates duplicates.
    
    Args:
        url: The job URL
        platform: Optional platform override (e.g. 'linkedin', 'indeed').
                  If provided, bypasses domain-based detection.
    """
    if not platform:
        platform = _get_platform(url)
    
    # Normalize platform for consistent key lookup
    platform = platform.lower().replace(" ", "").replace("-", "")

    if platform not in _active_bots:
        profile = ApplicantProfile()
        if platform == "indeed":
            _active_bots[platform] = IndeedBot(profile=profile)
        elif platform == "linkedin":
            _active_bots[platform] = LinkedInBot(profile=profile)
        elif platform in ["ziprecruiter", "zip"]:
            _active_bots[platform] = ZipRecruiterBot(profile=profile)
        elif platform == "dice":
            _active_bots[platform] = DiceBot(profile=profile)
        elif platform == "wellfound":
            _active_bots[platform] = WellfoundBot(profile=profile)
        elif platform == "builtin":
            _active_bots[platform] = BuiltInBot(profile=profile)
        elif platform == "iprecruiter":
            _active_bots[platform] = IPRecruiterBot(profile=profile)
        else:
            _active_bots[platform] = ExternalBot(profile_name=platform, profile=profile)

    return _active_bots[platform]


def quit_all_bots():
    """Close all active browser sessions."""
    global _active_bots
    for platform, bot in list(_active_bots.items()):
        try:
            bot.quit()
        except Exception:
            pass
    _active_bots.clear()


def apply_to_job(
    apply_url: str,
    resume_path: str = "",
    cover_letter_path: str = "",
    resume_text: str = "",
    source: str = "",
    guided: bool = False,
) -> dict:
    """
    Apply to a job using the appropriate bot.
    Reuses the same browser session for all jobs on the same platform.

    Args:
        apply_url: The job application URL
        resume_path: Path to the tailored resume file
        resume_text: Raw resume text (for LLM-based question answering)
        source: Job source platform name
        guided: If True, pauses for manual review before submission

    Returns: {"success": bool, "message": str}
    """
    bot = get_bot(apply_url, platform=source if source else None)
    # Re-identify platform for telemetry if not provided
    platform = source if source else _get_platform(apply_url)

    try:
        return bot.apply(apply_url, resume_path, cover_letter_path, resume_text, guided=guided)
    except Exception as e:
        return {"success": False, "message": f"Bot error: {str(e)}"}


def extract_job_details(url: str, platform: Optional[str] = None) -> dict:
    """
    Surgical Intelligence: Navigate to a job URL and extract key details 
    (Title, Company, Description) for document tailoring.
    """
    _safe_print(f"  🧠 Extracting mission intelligence from {url[:50]}...")
    bot = get_bot(url, platform=platform)
    bot.start()
    bot.driver.get(url)
    _human_delay(4, 6)
    
    details = {
        "title": "Unknown Position",
        "company": "Unknown Company",
        "location": "Remote",
        "description": "",
        "posted_date": "",
        "hiring_manager": ""
    }
    
    try:
        # Platform-specific extraction
        platform = _get_platform(url)
        content_text = ""
        
        if platform == "linkedin":
            try:
                details["title"] = bot.driver.find_element(By.CSS_SELECTOR, ".jobs-unified-top-card__job-title, .job-details h1").text.strip()
                details["company"] = bot.driver.find_element(By.CSS_SELECTOR, ".jobs-unified-top-card__company-name").text.strip()
                details["description"] = bot.driver.find_element(By.ID, "job-details").text.strip()
                
                # Frontier v34.0: Capture Posted Date & Recruiter
                try: details["posted_date"] = bot.driver.find_element(By.CSS_SELECTOR, ".jobs-unified-top-card__posted-date").text.strip()
                except: pass
                try: details["hiring_manager"] = bot.driver.find_element(By.CSS_SELECTOR, ".jobs-poster__name").text.strip()
                except: pass
            except: pass
        elif platform == "indeed":
            try:
                details["title"] = bot.driver.find_element(By.CSS_SELECTOR, "h1.jobsearch-JobInfoHeader-title").text.strip()
                details["company"] = bot.driver.find_element(By.CSS_SELECTOR, "[data-testid='inline-companyname'], .jobsearch-CompanyReview--flex").text.strip()
                details["description"] = bot.driver.find_element(By.ID, "jobDescriptionText").text.strip()
                
                # Frontier v34.0: Indeed Posted Date
                try: details["posted_date"] = bot.driver.find_element(By.CSS_SELECTOR, ".jobsearch-HiringInsights-entry--withIcon span:last-child").text.strip()
                except: pass
            except: pass
        elif platform == "ziprecruiter":
            try:
                details["title"] = bot.driver.find_element(By.CSS_SELECTOR, ".job_title, h1").text.strip()
                details["company"] = bot.driver.find_element(By.CSS_SELECTOR, ".company_name").text.strip()
                details["description"] = bot.driver.find_element(By.CSS_SELECTOR, ".job_description, .description").text.strip()
            except: pass
        elif platform == "dice":
            try:
                details["title"] = bot.driver.find_element(By.ID, "jobTitle").text.strip()
                details["company"] = bot.driver.find_element(By.ID, "debugId_companyName").text.strip()
                details["description"] = bot.driver.find_element(By.ID, "jobDescription").text.strip()
            except: pass
        elif platform == "wellfound":
            try:
                details["title"] = bot.driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
                details["company"] = bot.driver.find_element(By.CSS_SELECTOR, ".company-name").text.strip()
                details["description"] = bot.driver.find_element(By.CSS_SELECTOR, ".job-description").text.strip()
            except: pass
        elif platform == "builtin":
            try:
                details["title"] = bot.driver.find_element(By.CSS_SELECTOR, ".job-title").text.strip()
                details["company"] = bot.driver.find_element(By.CSS_SELECTOR, ".company-title").text.strip()
                details["description"] = bot.driver.find_element(By.CSS_SELECTOR, ".job-description").text.strip()
            except: pass
            
        # Fallback: AI Extraction from page body
        if not details["description"] or len(details["description"]) < 50:
            content_text = bot.driver.find_element(By.TAG_NAME, "body").text
            _safe_print("  ⚙ Using AI Synapse to identify job details...")
            llm = get_llm()
            prompt = f"""Extract job details from the following page text.
            URL: {url}
            
            Text: {content_text[:6000]}
            
            Return ONLY a JSON object:
            {{"title": "...", "company": "...", "location": "...", "description": "..."}}
            """
            try:
                res = llm.generate(prompt, "You are a professional data extractor.")
                # Basic JSON cleanup
                if "```json" in res: res = res.split("```json")[1].split("```")[0]
                elif "```" in res: res = res.split("```")[1].split("```")[0]
                ai_data = json.loads(res.strip())
                details.update(ai_data)
            except: pass
            
    except Exception as e:
        _safe_print(f"  ⚠ Intelligence extraction failed: {e}")
        
    return details


def cleanup_bots():
    """Close all active browser sessions. Call at program exit."""
    for platform, bot in _active_bots.items():
        try:
            bot.quit()
        except Exception:
            pass
    _active_bots.clear()

def cleanup_browser_processes():
    """Aggressively kill orphaned chromedriver and surgical WMIC cleanup for bot Chromes."""
    _safe_print("  🧹 Surgical cleanup of orphaned browser processes...")
    try:
        # 1. Kill all chromedriver processes
        subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe', '/T'], capture_output=True)
        
        # 2. Phase 25.1: SURGICAL CHROME KILL
        # Only kill chromes that are using the JobAutomation data directory
        if sys.platform == "win32":
            # Use WMIC to find and terminate chromes with our specific user-data-dir in command line
            subprocess.run(
                ["wmic", "process", "where", "name='chrome.exe' and CommandLine like '%browser_sessions%'", "call", "terminate"],
                capture_output=True,
                timeout=10
            )
            
        # 3. FORCE PROFILE UNLOCK
        # Remove SingletonLock files that prevent startup after a crash
        if SESSIONS_DIR.exists():
            for lock_file in SESSIONS_DIR.rglob("SingletonLock"):
                try:
                    os.remove(lock_file)
                except: pass
            for lock_file in SESSIONS_DIR.rglob("Lock"):
                try:
                    os.remove(lock_file)
                except: pass
    except Exception:
        pass

class ReverseSearchEngine:
    """
    Strategic Intelligence: Discovers Hiring Managers and Recruiters 
    on LinkedIn for high-value networking after a mission target is hit.
    """
    def __init__(self, browser_bot):
        self.bot = browser_bot

    def find_hiring_manager(self, company: str, title: str) -> dict:
        """Search LinkedIn for the most likely person behind the headcount."""
        _safe_print(f"  🕵 Initiating Reverse Company Search for {company}...")
        
        # Tactical search query
        query = f"{company} {title} Recruiter OR Hiring Manager"
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={query.replace(' ', '%20')}"
        
        try:
            self.bot.driver.get(search_url)
            _human_delay(5, 7)
            
            # Extract top 3 candidates
            people_els = self.bot.driver.find_elements(By.CSS_SELECTOR, ".reusable-search__result-container")
            results = []
            
            for el in people_els[:3]:
                try:
                    name_el = el.find_element(By.CSS_SELECTOR, ".app-aware-link")
                    name = name_el.text.split("\n")[0].strip()
                    profile_url = name_el.get_attribute("href").split("?")[0]
                    headline = el.find_element(By.CSS_SELECTOR, ".entity-result__primary-subtitle").text.strip()
                    
                    results.append({
                        "name": name,
                        "profile_url": profile_url,
                        "headline": headline
                    })
                except: continue
                
            return results[0] if results else None
        except Exception as e:
            _safe_print(f"  ⚠ Reverse search failed: {e}")
            return None


if __name__ == "__main__":
    _safe_print("Auto-Applicant Bot Test")
    _safe_print("=" * 40)
    test_url = input("Enter a job URL to test: ").strip()
    if test_url:
        result = apply_to_job(test_url)
        _safe_print(f"\nResult: {result}")
        cleanup_bots()
    else:
        _safe_print("No URL provided. Exiting.")
