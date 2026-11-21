import pytest
from langgraph.checkpoint.memory import MemorySaver
from pydantic import ValidationError

from src.triage.graph import build_graph
from src.triage.schemas import TicketClassification
from src.triage.service import TicketTriageService


def create_service():
    return TicketTriageService(build_graph(checkpointer=MemorySaver()))


def fail_llm(_ticket):
    raise RuntimeError("LLM indisponible pour le test")


@pytest.mark.parametrize(
    "subject, body, expected",
    [
        ("Horaires", "Quels sont vos horaires ?", "faq"),
        ("Erreur", "L'application plante", "technique"),
        ("Facture", "Problème de paiement", "facturation"),
        ("URGENT", "Panne totale", "urgent"),
        ("Gagnez", "Cliquez ici", "spam"),
    ],
)
def test_fallback_classification(subject, body, expected, monkeypatch):
    monkeypatch.setattr("src.triage.nodes.classify_with_llm", fail_llm)
    service = create_service()
    out = service.process(
        {"ticket_id": "T-0", "subject": subject, "body": body}
    )

    assert out["category"] == expected
    assert out["classification_source"] == "fallback"
    if expected != "urgent":
        assert out["result"].startswith("[T-0]")


def test_urgent_ticket_waits_for_human_decision(monkeypatch):
    monkeypatch.setattr("src.triage.nodes.classify_with_llm", fail_llm)
    service = create_service()
    pending = service.process(
        {"ticket_id": "T-URGENT", "subject": "URGENT", "body": "Panne totale"}
    )

    assert pending["__interrupt__"]
    completed = service.resume(pending["thread_id"], "approve")
    assert completed["human_decision"] == "approve"
    assert "approuvée" in completed["result"]


def test_unknown_ticket_is_sent_to_manual_review(monkeypatch):
    monkeypatch.setattr("src.triage.nodes.classify_with_llm", fail_llm)
    service = create_service()
    out = service.process(
        {"ticket_id": "T-UNKNOWN", "subject": "Autre demande", "body": "Bonjour"}
    )

    assert out["category"] == "faq"
    assert out["confidence"] == 0
    assert "Révision manuelle" in out["result"]


def test_structured_llm_classification_routes_without_fallback(monkeypatch):
    monkeypatch.setattr(
        "src.triage.nodes.classify_with_llm",
        lambda _ticket: TicketClassification(
            category="facturation",
            confidence=0.92,
            summary="Question sur un prélèvement.",
        ),
    )
    service = create_service()
    out = service.process(
        {"ticket_id": "T-LLM", "subject": "Demande", "body": "Mon dossier"}
    )

    assert out["category"] == "facturation"
    assert out["classification_source"] == "openai"
    assert out["confidence"] == 0.92


def test_invalid_structured_output_uses_keyword_fallback(monkeypatch):
    monkeypatch.setattr(
        "src.triage.nodes.classify_with_llm",
        lambda _ticket: {
            "category": "inconnue",
            "confidence": 0.95,
            "summary": "Sortie invalide.",
        },
    )
    service = create_service()
    out = service.process(
        {"ticket_id": "T-INVALID-LLM", "subject": "Erreur", "body": "Le site plante"}
    )

    assert out["category"] == "technique"
    assert out["classification_source"] == "fallback"


def test_sqlite_checkpoint_can_resume_after_service_recreation(
    monkeypatch, tmp_path
):
    monkeypatch.setattr("src.triage.nodes.classify_with_llm", fail_llm)
    database_path = tmp_path / "checkpoints.sqlite"
    service = TicketTriageService.from_sqlite(database_path)
    pending = service.process(
        {"ticket_id": "T-SQLITE", "subject": "Urgent", "body": "Panne totale"}
    )
    service.close()

    resumed_service = TicketTriageService.from_sqlite(database_path)
    try:
        completed = resumed_service.resume(pending["thread_id"], "approve")
    finally:
        resumed_service.close()

    assert completed["human_decision"] == "approve"


def test_invalid_ticket_is_rejected_before_graph_execution():
    service = create_service()

    with pytest.raises(ValidationError):
        service.process({"ticket_id": "T-INVALID", "subject": "Sujet"})
