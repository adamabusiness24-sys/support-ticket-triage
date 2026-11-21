from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

Category: TypeAlias = Literal[
    "faq", "technique", "facturation", "urgent", "spam"
]


class TicketInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ticket_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)


class TicketClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(min_length=1, max_length=300)
