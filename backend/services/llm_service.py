import os
from dotenv import load_dotenv

load_dotenv()


class LLMService:
    """
    Unified LLM service supporting:
    - 'ollama'    → Local Ollama          (no key needed)
    - 'gemini'    → Google Gemini         (GEMINI_API_KEY)
    - 'groq'      → Groq API              (GROQ_API_KEY)
    - 'anthropic' → Anthropic Claude      (ANTHROPIC_API_KEY)
    - 'openai'    → OpenAI GPT            (OPENAI_API_KEY)
    - 'grok'      → xAI Grok              (XAI_API_KEY)
    """

    PROVIDER_CONFIG = {
        "grok":      ("XAI_API_KEY",       "https://api.x.ai/v1",                                      "grok-beta"),
        "groq":      ("GROQ_API_KEY",      "https://api.groq.com/openai/v1",                           "llama-3.3-70b-versatile"),
        "gemini":    ("GEMINI_API_KEY",    "https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-2.0-flash"),
        "openai":    ("OPENAI_API_KEY",    "https://api.openai.com/v1",                                "gpt-4o"),
        "anthropic": ("ANTHROPIC_API_KEY", None,                                                        "claude-sonnet-4-20250514"),
    }

    def __init__(self, provider: str = None, model: str = None):
        self.provider = (provider or os.environ.get("LLM_PROVIDER", "ollama")).lower()
        self.model = model or os.environ.get("LLM_MODEL") or self._default_model()
        self.client = self._init_client()

    def _default_model(self) -> str:
        if self.provider == "ollama":
            return "qwen2.5-coder:7b"
        if self.provider in self.PROVIDER_CONFIG:
            return self.PROVIDER_CONFIG[self.provider][2]
        return "qwen2.5-coder:7b"

    def _init_client(self):
        if self.provider == "ollama":
            return None

        if self.provider not in self.PROVIDER_CONFIG:
            raise ValueError(
                f"Unknown LLM_PROVIDER: '{self.provider}'. "
                f"Choose from: ollama, gemini, groq, anthropic, openai, grok"
            )

        env_key, base_url, _ = self.PROVIDER_CONFIG[self.provider]
        api_key = os.environ.get(env_key)

        if not api_key:
            raise RuntimeError(
                f"{env_key} not set in .env. Required for provider '{self.provider}'."
            )

        # Anthropic has its own SDK
        if self.provider == "anthropic":
            try:
                import anthropic
                return anthropic.Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("Run: pip install anthropic")

        # All others use OpenAI-compatible SDK
        try:
            from openai import OpenAI
            return OpenAI(api_key=api_key, base_url=base_url)
        except ImportError:
            raise ImportError("Run: pip install openai")

    def chat(self, messages: list, temperature: float = 0.2) -> dict:
        """Always returns: {'message': {'content': str}}"""

        if self.provider == "anthropic":
            # Anthropic uses a different messages format — system prompt must be separate
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
            user_msgs = [m for m in messages if m["role"] != "system"]

            kwargs = dict(
                model=self.model,
                max_tokens=4096,
                messages=user_msgs,
                temperature=temperature,
            )
            if system_msg:
                kwargs["system"] = system_msg

            response = self.client.messages.create(**kwargs)
            return {"message": {"content": response.content[0].text}}

        elif self.provider in ("grok", "groq", "gemini", "openai"):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                timeout=30,
            )
            return {"message": {"content": response.choices[0].message.content}}

        elif self.provider == "ollama":
            try:
                import ollama
            except ImportError:
                raise ImportError("Run: pip install ollama")
            response = ollama.chat(model=self.model, messages=messages)
            return response

        else:
            raise ValueError(f"Unknown provider: {self.provider}")