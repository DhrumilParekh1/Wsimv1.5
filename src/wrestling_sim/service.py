"""Single-process game service shared by API and CLI."""
from __future__ import annotations
from pathlib import Path
import os
from threading import RLock
from .starter import new_game
from .storage import load_game, save_game


class GameService:
    @staticmethod
    def _new_state(seed=2026):
        # Offline and self-contained: no source downloads during browser startup.
        # The curated 80-person roster is bundled as data; the optional Wikidata
        # catalogue enriches identities if it already exists.
        if os.getenv("RINGSIDE_START_MODE","fictional").lower()=="real":
            from .real_universe import build_universe
            return build_universe(
                catalogue=os.getenv("RINGSIDE_REAL_DATA_DB","data/real_wrestlers.db"),
                seed=seed)
        return new_game(seed)

    def __init__(self, save_path: str | Path = 'saves/game.db') -> None:
        self.path = Path(save_path)
        self.lock = RLock()
        if self.path.suffix == '.db':
            from .database import has_save, load_database
            if has_save(self.path):
                self.state = load_database(self.path)
            else:
                legacy = self.path.with_suffix('.json')
                self.state = load_game(legacy) if legacy.exists() else self._new_state()
                self.save()  # Automatic non-destructive JSON -> SQLite migration
        else:
            self.state = load_game(self.path) if self.path.exists() else self._new_state()

    def save(self) -> None:
        if self.path.suffix == '.db':
            from .database import save_database
            save_database(self.state,self.path)
        else:
            save_game(self.state, self.path)

    def reset(self, seed: int = 2026) -> None:
        with self.lock:
            self.state = self._new_state(seed)
            self.save()
