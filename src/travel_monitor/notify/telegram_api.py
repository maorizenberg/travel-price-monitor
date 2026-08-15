import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

def _load_dotenv():
    env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip("\"'")
                if k not in os.environ:
                    os.environ[k] = v

_load_dotenv()


class TelegramSender:
    API_URL = "https://api.telegram.org/bot{token}"

    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

        if not self.token or not self.chat_id:
            logger.warning("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.")

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def _post(self, method: str, **kwargs) -> dict:
        url = f"{self.API_URL.format(token=self.token)}/{method}"
        resp = requests.post(url, **kwargs, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def send_text(self, text: str) -> dict:
        if not self.configured:
            raise RuntimeError("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")

        logger.info(f"Sending Telegram message to chat {self.chat_id}")
        return self._post(
            "sendMessage",
            json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
