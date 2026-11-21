import json
import logging
from pathlib import Path

from src.triage.service import TicketTriageService

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    project_dir = Path(__file__).resolve().parent
    tickets = json.loads(
        (project_dir / "data" / "sample_tickets.json").read_text(encoding="utf-8")
    )
    service = TicketTriageService.from_sqlite()

    try:
        for ticket in tickets:
            out = service.process(ticket)
            if out.get("__interrupt__"):
                logger.info(
                    "Ticket %s en attente de validation humaine.", ticket["ticket_id"]
                )
                decision = input(
                    f"Ticket {ticket['ticket_id']} urgent : approuver ou rejeter ? "
                    "[approve/reject] "
                ).strip().lower()
                if decision not in ("approve", "reject"):
                    raise ValueError("Réponse invalide; utilisez approve ou reject.")
                out = service.resume(out["thread_id"], decision)
            print(f"{out['category']:<12} -> {out['result']}")
    finally:
        service.close()


if __name__ == "__main__":
    main()
