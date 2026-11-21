"""Nœuds métier du workflow de triage."""
import logging
import unicodedata

from langgraph.types import interrupt

from .config import get_settings
from .llm import classify_with_llm
from .schemas import TicketClassification, TicketInput
from .state import TicketState

logger = logging.getLogger(__name__)

KEYWORDS = {
    "spam": ["gagnez", "gratuit", "promo exclusive", "cliquez ici", "loterie"],
    "urgent": ["urgent", "panne totale", "production arretee", "donnees perdues", "piratage"],
    "facturation": ["facture", "paiement", "rembours", "abonnement", "prelevement"],
    "technique": ["erreur", "bug", "plante", "ne marche pas", "impossible de", "crash"],
    "faq": ["horaires", "comment", "quels sont", "quelle est", "information"],
}


def _normalize(text: str) -> str:
    """Minuscules et sans accents, pour comparer simplement."""
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def classify_with_keywords(ticket: TicketInput) -> TicketClassification:
    text = _normalize(f"{ticket.subject} {ticket.body}")
    for category in ("spam", "urgent", "facturation", "technique", "faq"):
        if any(word in text for word in KEYWORDS[category]):
            return TicketClassification(
                category=category,
                confidence=0.75,
                summary="Catégorie déterminée par les règles locales.",
            )
    return TicketClassification(
        category="faq",
        confidence=0,
        summary="Aucun mot-clé fiable; une révision est nécessaire.",
    )


def classify(state: TicketState) -> dict:
    ticket = TicketInput.model_validate(state)
    source = "openai"
    try:
        classification = TicketClassification.model_validate(
            classify_with_llm(ticket)
        )
    except Exception as exc:
        logger.warning(
            "Échec de la classification LLM pour le ticket %s (%s); utilisation du fallback.",
            ticket.ticket_id,
            type(exc).__name__,
        )
        classification = classify_with_keywords(ticket)
        source = "fallback"

    return {
        "category": classification.category,
        "confidence": classification.confidence,
        "summary": classification.summary,
        "classification_source": source,
    }


def auto_reply(state: TicketState) -> dict:
    return {"result": f"[{state['ticket_id']}] Réponse automatique envoyée (FAQ)."}


def tech_ticket(state: TicketState) -> dict:
    return {"result": f"[{state['ticket_id']}] Ticket créé pour l'équipe technique."}


def billing_check(state: TicketState) -> dict:
    return {"result": f"[{state['ticket_id']}] Transmis à l'équipe comptabilité."}


def urgent_alert(state: TicketState) -> dict:
    decision = interrupt(
        {
            "ticket_id": state["ticket_id"],
            "category": state["category"],
            "summary": state.get("summary", ""),
            "message": "Confirmer ou rejeter le traitement comme incident urgent.",
        }
    )
    if isinstance(decision, dict):
        decision = decision.get("decision")
    if decision not in ("approve", "reject"):
        raise ValueError("Décision humaine invalide; utilisez approve ou reject.")
    if decision == "approve":
        result = "Alerte urgente approuvée par validation humaine."
    else:
        result = "Urgence rejetée par validation humaine; révision requise."
    return {"human_decision": decision, "result": f"[{state['ticket_id']}] {result}"}


def archive_spam(state: TicketState) -> dict:
    return {"result": f"[{state['ticket_id']}] Spam archivé."}


def manual_review(state: TicketState) -> dict:
    return {
        "result": (
            f"[{state['ticket_id']}] Révision manuelle requise "
            f"(confiance : {state.get('confidence', 0):.0%})."
        )
    }


def router(state: TicketState) -> str:
    settings = get_settings()
    if state.get("confidence", 0) < settings.confidence_threshold:
        return "review"
    return state["category"]
