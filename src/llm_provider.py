import json
import sys
from pathlib import Path
import requests
from openai import OpenAI

# Add project root to path if running directly
sys.path.append(str(Path(__file__).parent.parent))

import config


class LLMProvider:
    """Base class for LLM providers."""

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (GPT-4o, etc.)."""

    def __init__(self):
        if not config.OPENAI_API_KEY:
            raise ValueError(
                "OpenAI API key is missing. "
                "Please run 'Option 10: Profile Setup' or set OPENAI_API_KEY in your .env file."
            )
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
        )
        return response.choices[0].message.content.strip()


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider. Supports both old and new API endpoints."""

    def __init__(self):
        self.base_url = config.OLLAMA_BASE_URL.rstrip("/")
        self.model = config.OLLAMA_MODEL
        self._use_generate = False  # Will switch to True if /api/chat fails with 404

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        try:
            if self._use_generate:
                return self._generate_legacy(prompt, system_prompt)
            else:
                return self._generate_chat(prompt, system_prompt)
        except requests.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running (run 'ollama serve' in a terminal)."
            )
        except requests.Timeout:
            raise TimeoutError(
                "Ollama request timed out. The model may be loading or the prompt is very long."
            )

    def _generate_chat(self, prompt: str, system_prompt: str = "") -> str:
        """Use the newer /api/chat endpoint."""
        url = f"{self.base_url}/api/chat"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 4096},
        }

        resp = requests.post(url, json=payload, timeout=600)

        # If 404, fall back to legacy /api/generate
        if resp.status_code == 404:
            self._use_generate = True
            return self._generate_legacy(prompt, system_prompt)

        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip()

    def _generate_legacy(self, prompt: str, system_prompt: str = "") -> str:
        """Use the older /api/generate endpoint (Ollama < 0.1.14)."""
        url = f"{self.base_url}/api/generate"
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 4096},
        }

        resp = requests.post(url, json=payload, timeout=600)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()


class GeminiProvider(LLMProvider):
    """Google Gemini AI provider."""

    def __init__(self):
        import google.generativeai as genai
        if not config.GEMINI_API_KEY:
            raise ValueError(
                "Gemini API key is missing. "
                "Please run 'Option 10: Profile Setup' or set GEMINI_API_KEY in your .env file."
            )
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(config.GEMINI_MODEL or "gemini-1.5-flash")

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        try:
            # Gemini typically combines system and user prompts
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = self.model.generate_content(
                full_prompt,
                generation_config={"temperature": 0.7, "max_output_tokens": 4096}
            )
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}")


class AnthropicProvider(LLMProvider):
    """Anthropic Claude AI provider."""

    def __init__(self):
        import anthropic
        if not config.ANTHROPIC_API_KEY:
            raise ValueError(
                "Anthropic API key is missing. "
                "Please run 'Option 10: Profile Setup' or set ANTHROPIC_API_KEY in your .env file."
            )
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = config.ANTHROPIC_MODEL or "claude-3-5-sonnet-20240620"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {e}")


class GroqProvider(LLMProvider):
    """Groq AI provider (OpenAI-compatible)."""

    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=config.GROQ_API_KEY
        )
        self.model = config.GROQ_MODEL

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"Groq API error: {e}")


class LMStudioProvider(LLMProvider):
    """LM Studio local LLM provider (OpenAI-compatible API)."""

    def __init__(self):
        self.client = OpenAI(
            base_url=config.LMSTUDIO_BASE_URL,
            api_key="lm-studio",  # LM Studio doesn't need a real key
        )
        self.model = config.LMSTUDIO_MODEL

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "Connection" in str(type(e).__name__) or "connect" in str(e).lower():
                raise ConnectionError(
                    f"Cannot connect to LM Studio at {config.LMSTUDIO_BASE_URL}. "
                    "Make sure LM Studio is running with the local server enabled."
                )
            raise
            

class OpenRouterProvider(LLMProvider):
    """OpenRouter AI provider (OpenAI-compatible)."""

    def __init__(self):
        # OpenRouter uses the OpenAI SDK but with a different base URL
        if not config.OPENROUTER_API_KEY:
            raise ValueError(
                "OpenRouter API key is missing. "
                "Please run 'Option 10: Profile Setup' or set OPENROUTER_API_KEY in your .env file."
            )
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config.OPENROUTER_API_KEY,
        )
        self.model = config.OPENROUTER_MODEL or "google/gemini-2.0-flash-001"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # OpenRouter specific headers can be added here if needed, 
            # but for anonymity we keep it minimal.
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"OpenRouter API error: {e}")


class ResilientLLM(LLMProvider):
    """
    Wrapper that tries the primary LLM and falls back to a reliable cloud 
    provider (OpenAI or Gemini) if the primary fails.
    """
    def __init__(self, primary: LLMProvider):
        self.primary = primary
        self.fallback = None
        
        # Determine fallback (Cloud providers are most reliable)
        try:
            if config.OPENAI_API_KEY:
                self.fallback = OpenAIProvider()
            elif config.GEMINI_API_KEY:
                self.fallback = GeminiProvider()
            elif config.GROQ_API_KEY:
                self.fallback = GroqProvider()
        except Exception:
            pass

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        try:
            return self.primary.generate(prompt, system_prompt)
        except Exception as e:
            # If we don't have a fallback or the primary is already the fallback, just fail
            if not self.fallback or type(self.primary) == type(self.fallback):
                raise
            
            error_msg = str(e)
            # Only fallback on transient/connectivity errors
            if any(kw in error_msg.lower() for kw in ["connection", "timeout", "404", "not found", "reachable"]):
                print(f"\n  [yellow]! Primary LLM ({type(self.primary).__name__}) unreachable. Retrying with fallback...[/]")
                try:
                    return self.fallback.generate(prompt, system_prompt)
                except Exception as fe:
                    raise fe from e
            raise


# ── Factory ──────────────────────────────────────────────────

_providers = {
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
    "lmstudio": LMStudioProvider,
    "gemini": GeminiProvider,
    "claude": AnthropicProvider,
    "groq": GroqProvider,
    "openrouter": OpenRouterProvider,
}

_current_provider: LLMProvider | None = None


def get_llm() -> LLMProvider:
    """Get the configured LLM provider instance (wrapped in Resilience)."""
    global _current_provider
    if _current_provider is None:
        provider_name = config.LLM_PROVIDER
        if provider_name not in _providers:
            raise ValueError(
                f"Unknown LLM provider: '{provider_name}'. "
                f"Choose from: {', '.join(_providers.keys())}"
            )
        base_provider = _providers[provider_name]()
        _current_provider = ResilientLLM(base_provider)
    return _current_provider


def switch_provider(provider_name: str) -> LLMProvider:
    """Switch to a different LLM provider at runtime (wrapped in Resilience)."""
    global _current_provider
    provider_name = provider_name.lower().strip()
    if provider_name not in _providers:
        raise ValueError(
            f"Unknown LLM provider: '{provider_name}'. "
            f"Choose from: {', '.join(_providers.keys())}"
        )
    base_provider = _providers[provider_name]()
    _current_provider = ResilientLLM(base_provider)
    return _current_provider


def test_connection() -> bool:
    """Test if the current LLM provider is reachable."""
    try:
        llm = get_llm()
        response = llm.generate("Say 'hello' in one word.", "You are a helpful assistant.")
        return bool(response)
    except Exception as e:
        print(f"[LLM TEST FAILED] {e}")
        return False


if __name__ == "__main__":
    config.validate()
    print(f"Testing {config.LLM_PROVIDER} provider...")
    if test_connection():
        llm = get_llm()
        result = llm.generate(
            "What is 2+2? Answer in one sentence.",
            "You are a helpful math tutor."
        )
        print(f"✓ Connection successful!")
        print(f"  Response: {result}")
    else:
        print("✗ Connection failed. Check your configuration.")
