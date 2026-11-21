import json
import logging
from pathlib import Path

import streamlit as st

from src.triage.service import TicketTriageService

PROJECT_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)


@st.cache_resource
def get_service() -> TicketTriageService:
    return TicketTriageService.from_sqlite()


def show_result(result: dict) -> None:
    st.success(f"Catégorie : {result['category']}")
    st.write(f"Confiance : {result.get('confidence', 0):.0%}")
    st.write(f"Source : {result.get('classification_source', 'workflow')}")
    st.write(result.get("summary", ""))
    st.info(result["result"])


def main() -> None:
    st.set_page_config(page_title="Support Ticket Triage", page_icon="📨")
    st.title("Triage des tickets de support")
    st.caption("La classification OpenAI utilise la clé de l’environnement local.")

    service = get_service()
    pending = st.session_state.get("pending_ticket")
    if pending:
        st.warning("Ce ticket urgent attend une décision humaine.")
        st.write(pending["interrupt"])
        approve, reject = st.columns(2)
        if approve.button("Confirmer l’urgence", type="primary"):
            try:
                result = service.resume(pending["thread_id"], "approve")
                st.session_state["last_result"] = result
                st.session_state.pop("pending_ticket", None)
                st.rerun()
            except Exception:
                logger.exception("Échec de la reprise du ticket urgent.")
                st.error("Impossible de reprendre le ticket. Consultez les journaux.")
        if reject.button("Rejeter l’urgence"):
            try:
                result = service.resume(pending["thread_id"], "reject")
                st.session_state["last_result"] = result
                st.session_state.pop("pending_ticket", None)
                st.rerun()
            except Exception:
                logger.exception("Échec de la reprise du ticket urgent.")
                st.error("Impossible de reprendre le ticket. Consultez les journaux.")

    if not pending:
        with st.form("ticket_form"):
            ticket_id = st.text_input("Identifiant", value="T-STREAMLIT")
            subject = st.text_input("Sujet")
            body = st.text_area("Description")
            submitted = st.form_submit_button("Classer le ticket")

        if submitted:
            try:
                result = service.process(
                    {"ticket_id": ticket_id, "subject": subject, "body": body}
                )
                interrupts = result.get("__interrupt__", ())
                if interrupts:
                    interrupt_value = getattr(interrupts[0], "value", interrupts[0])
                    st.session_state["pending_ticket"] = {
                        "thread_id": result["thread_id"],
                        "interrupt": interrupt_value,
                    }
                    st.rerun()
                st.session_state["last_result"] = result
            except Exception:
                logger.exception("Échec du traitement d'un ticket.")
                st.error("Le ticket n'a pas pu être traité. Consultez les journaux.")

    last_result = st.session_state.get("last_result")
    if last_result:
        st.subheader("Résultat")
        show_result(last_result)

    with st.expander("Exemples de tickets"):
        sample_path = PROJECT_DIR / "data" / "sample_tickets.json"
        samples = json.loads(sample_path.read_text(encoding="utf-8"))
        st.json(samples)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
