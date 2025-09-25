import json
import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class BotState:
    last_open_iso_by_symbol: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str) -> "BotState":
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def save(self, path: str):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"last_open_iso_by_symbol": self.last_open_iso_by_symbol}, f, indent=2)
        os.replace(tmp, path)