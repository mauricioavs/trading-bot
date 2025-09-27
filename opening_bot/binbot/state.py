import json
import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class BotState:
    last_open_iso_by_symbol: Dict[str, str] = field(default_factory=dict)

    # scheduler de stops
    last_stops_check_ts: float = 0.0
    last_stop_attempt_ts_by_symbol: dict[str, float] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str) -> "BotState":
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "last_open_iso_by_symbol": self.last_open_iso_by_symbol,
                    "last_stops_check_ts": self.last_stops_check_ts,
                    "last_stop_attempt_ts_by_symbol": self.last_stop_attempt_ts_by_symbol,
                },
                f,
                indent=2,       # sangría de 2 espacios
                sort_keys=True  # opcional: ordena las claves alfabéticamente
            )
