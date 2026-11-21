import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_model: str
    confidence_threshold: float
    checkpoint_db: Path


def get_settings() -> Settings:
    threshold = float(os.getenv("TICKET_CONFIDENCE_THRESHOLD", "0.65"))
    if not 0 <= threshold <= 1:
        raise ValueError("TICKET_CONFIDENCE_THRESHOLD doit être compris entre 0 et 1.")

    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        confidence_threshold=threshold,
        checkpoint_db=Path(
            os.getenv("TRIAGE_CHECKPOINT_DB", "data/triage_checkpoints.sqlite")
        ),
    )
