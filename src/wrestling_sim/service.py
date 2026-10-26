"""Single-process game service shared by API and CLI."""
from __future__ import annotations
from pathlib import Path
from threading import RLock
from .starter import new_game
from .storage import load_game, save_game


class GameService:
    def __init__(self, save_path: str | Path = 'saves/game.db') -> None:
        self.path = Path(save_path)
        self.lock = RLock()
        if self.path.suffix == '.db':
            from .database import has_save, load_database
            if has_save(self.path):
                self.state = load_database(self.path)
            else:
                legacy = self.path.with_suffix('.json')
                self.state = load_game(legacy) if legacy.exists() else new_game()
                self.save()  # Automatic non-destructive JSON -> SQLite migration
        else:
            self.state = load_game(self.path) if self.path.exists() else new_game()

    def save(self) -> None:
        if self.path.suffix == '.db':
            from .database import save_database
            save_database(self.state,self.path)
        else:
            save_game(self.state, self.path)

    def reset(self, seed: int = 2026) -> None:
        with self.lock:
            self.state = new_game(seed)
            self.save()
