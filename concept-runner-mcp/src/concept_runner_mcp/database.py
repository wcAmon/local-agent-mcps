"""Lazy SQLite engine initialization for Concept Runner."""

import os
from pathlib import Path

from sqlmodel import SQLModel, create_engine

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        data_dir = Path(os.environ.get("DATA_DIR", str(Path(__file__).resolve().parent.parent.parent / "data")))
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "concepts.db"
        _engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        SQLModel.metadata.create_all(_engine)
    return _engine
