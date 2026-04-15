# 🧠 AI Setup Guide: Powering the Sovereign Agent

Sovereign is built on an "Open-Brain" architecture. You can connect it to any modern Large Language Model (LLM). This guide will help you set up your intelligence core with $0 upfront costs.

---

## 🌩️ Option 1: OpenRouter (Best for 99% of Users)
**Cost: FREE Tier Available**  
[OpenRouter](https://openrouter.ai) acts as a gateway to dozens of top-tier AI models. It is the easiest way to get started.

### Setup Steps:
1.  **Sign Up**: Go to [OpenRouter.ai](https://openrouter.ai).
2.  **Create API Key**: Navigate to the **Keys** section and create a new key.
3.  **Fund your account (Optional)**: Most users can start for free, but adding $5 will give you access to premium models like GPT-4o.
4.  **Configure .env**:
    ```env
    LLM_PROVIDER=openrouter
    OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
    OPENROUTER_MODEL=google/gemini-2.0-flash-001
    ```
    *Note: `gemini-2.0-flash-001` is currently the best balance of speed, cost (free), and intelligence.*

---

## 🏠 Option 2: Ollama (Local & Private)
**Cost: 100% FREE**  
Host your own AI locally. No data leaves your machine. This is the ultimate privacy configuration.

### Setup Steps:
1.  **Download Ollama**: Get it for Windows/Mac/Linux at [ollama.com](https://ollama.com).
2.  **Download a Model**: Open your terminal and run:
    ```bash
    ollama run llama3.1
    ```
3.  **Keep it Running**: Ensure the Ollama app is running in your system tray.
4.  **Configure .env**:
    ```env
    LLM_PROVIDER=ollama
    OLLAMA_BASE_URL=http://localhost:11434
    OLLAMA_MODEL=llama3.1
    ```

---

## 💎 Option 3: Direct API (OpenAI / Anthropic)
**Cost: Pay-per-use**  
For high-stakes senior-level campaigns, you may want the absolute "Executive Polish" of specialized models.

### Setup Steps:
1.  **Get Key**: Visit [OpenAI](https://platform.openai.com) or [Anthropic](https://console.anthropic.com).
2.  **Configure .env**:
    ```env
    LLM_PROVIDER=openai # or anthropic
    OPENAI_API_KEY=sk-YOUR_KEY_HERE
    OPENAI_MODEL=gpt-4o
    ```

---

## ❓ Troubleshooting

### "Model Not Found"
Ensure your `MODEL` string matches exactly what is listed on the provider's website. For OpenRouter, always include the prefix (e.g., `google/` or `meta/`).

### "Connection Refused" (Ollama)
Ensure Ollama is running and that you have downloaded the model using `ollama run [model_name]`.

### "Match Score is always 0"
Check the Live Console in the Dashboard. This usually means the AI returned a malformed response due to an invalid model selection.

---

*Need help? Open an issue on GitHub!*
