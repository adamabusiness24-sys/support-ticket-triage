from typing import Literal, TypedDict

from .schemas import Category


class TicketState(TypedDict, total=False):
    """État partagé entre les nœuds du workflow."""

    ticket_id: str
    subject: str
    body: str
    category: Category
    confidence: float
    summary: str
    classification_source: Literal["openai", "fallback"]
    result: str
    human_decision: Literal["approve", "reject"]
