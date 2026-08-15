import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class PriceHistory:
    DATA_DIR = Path(__file__).resolve().parent.parent.parent / ".travel-monitor"
    DATA_FILE = DATA_DIR / "price_history.json"

    WATCH_FIELDS = ["price", "seats", "days", "dates", "depart", "return"]

    def __init__(self):
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.DATA_FILE.exists():
            try:
                self._data = json.loads(self.DATA_FILE.read_text())
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load snapshot history: {e}")
                self._data = {}

    def _save(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_FILE.write_text(json.dumps(self._data, indent=2, ensure_ascii=False))

    def update(self, key: str, row: dict) -> dict:
        prev = self._data.get(key, {})
        prev_snapshot = prev.get("snapshot", {})
        new_snapshot = {k: row.get(k, "") for k in self.WATCH_FIELDS}

        def _num(s):
            try:
                return int(s.replace("\u20ac", "").replace(",", ""))
            except (ValueError, AttributeError):
                return None

        changes = []
        for k in self.WATCH_FIELDS:
            old = prev_snapshot.get(k, "")
            new = new_snapshot.get(k, "")
            if old and old != new:
                if k == "price":
                    n_new = _num(new)
                    n_old = _num(old)
                    if n_new is not None and n_old is not None:
                        changes.append(f"Price\u2193\u20ac{n_old - n_new}" if n_new < n_old else f"Price\u2191\u20ac{n_new - n_old}")
                    else:
                        changes.append(f"Price {old}\u2192{new}")
                elif k == "seats":
                    n_new = _num(new)
                    n_old = _num(old)
                    if n_new is not None and n_old is not None:
                        changes.append(f"Seats\u2193{n_old}\u2192{new}" if n_new < n_old else f"Seats\u2191{n_old}\u2192{new}")
                    else:
                        changes.append(f"Seats {old}\u2192{new}")
                else:
                    changes.append(f"{k.capitalize()} {old}\u2192{new}")

        self._data[key] = {
            "snapshot": new_snapshot,
            "updated_at": datetime.now().isoformat(),
        }
        self._save()

        return {
            "is_new": not prev,
            "changes": changes,
            "change_label": ", ".join(changes) if changes else "",
        }
