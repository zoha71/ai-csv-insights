"""Load settings from environment variables. Never hardcode secrets."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".csv"}


@dataclass(frozen=True)
class AISettings:
    api_key: str
    base_url: str
    model: str
    chat_path: str
    timeout_seconds: int

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key.strip())

    @property
    def chat_url(self) -> str:
        return self.base_url.rstrip("/") + "/" + self.chat_path.lstrip("/")


def get_ai_settings() -> AISettings:
    timeout_raw = os.getenv("AI_TIMEOUT_SECONDS", "45").strip()
    try:
        timeout = int(timeout_raw)
    except ValueError:
        timeout = 45
    return AISettings(
        api_key=os.getenv("AI_API_KEY", "").strip(),
        base_url=os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1").strip(),
        model=os.getenv("AI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
        chat_path=os.getenv("AI_CHAT_PATH", "/chat/completions").strip() or "/chat/completions",
        timeout_seconds=max(5, timeout),
    )
