import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from .config import get_settings
from .graph import build_graph
from .schemas import TicketInput

logger = logging.getLogger(__name__)


class TicketTriageService:
    def __init__(self, app, connection: sqlite3.Connection | None = None):
        self._app = app
        self._connection = connection

    @classmethod
    def from_sqlite(cls, database_path: Path | None = None):
        settings = get_settings()
        path = database_path or settings.checkpoint_db
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, check_same_thread=False)
        try:
            checkpointer = SqliteSaver(connection)
            checkpointer.setup()
            return cls(build_graph(checkpointer=checkpointer), connection)
        except Exception:
            connection.close()
            raise

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def process(self, ticket: dict, thread_id: str | None = None) -> dict:
        validated_ticket = TicketInput.model_validate(ticket)
        resolved_thread_id = thread_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": resolved_thread_id}}
        logger.info("Traitement du ticket %s démarré.", validated_ticket.ticket_id)
        result = self._app.invoke(validated_ticket.model_dump(), config=config)
        return {**result, "thread_id": resolved_thread_id}

    def resume(
        self,
        thread_id: str,
        decision: Literal["approve", "reject"],
    ) -> dict:
        config = {"configurable": {"thread_id": thread_id}}
        result = self._app.invoke(
            Command(resume={"decision": decision}),
            config=config,
        )
        return {**result, "thread_id": thread_id}
