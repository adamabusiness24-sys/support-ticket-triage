from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .config import get_settings
from .schemas import TicketClassification, TicketInput

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Classifie le ticket de support dans une seule catégorie parmi "
            "faq, technique, facturation, urgent et spam. "
            "Utilise urgent pour les interruptions majeures, pertes de données "
            "ou incidents de sécurité. Retourne une confiance entre 0 et 1 et "
            "un résumé bref en français. N'invente pas d'informations.",
        ),
        (
            "human",
            "Sujet : {subject}\nTicket : {body}",
        ),
    ]
)


def classify_with_llm(ticket: TicketInput) -> TicketClassification:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("La variable OPENAI_API_KEY n'est pas configurée.")

    model = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
        timeout=20,
        max_retries=1,
    )
    chain = _PROMPT | model.with_structured_output(TicketClassification)
    output = chain.invoke(
        {"subject": ticket.subject, "body": ticket.body}
    )
    return TicketClassification.model_validate(output)
