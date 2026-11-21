from langgraph.graph import END, START, StateGraph

from .nodes import (
    archive_spam,
    auto_reply,
    billing_check,
    classify,
    manual_review,
    router,
    tech_ticket,
    urgent_alert,
)
from .state import TicketState


def build_graph(checkpointer=None):
    graph = StateGraph(TicketState)

    graph.add_node("classify", classify)
    graph.add_node("faq", auto_reply)
    graph.add_node("technique", tech_ticket)
    graph.add_node("facturation", billing_check)
    graph.add_node("urgent", urgent_alert)
    graph.add_node("spam", archive_spam)
    graph.add_node("review", manual_review)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        router,
        {
            "faq": "faq",
            "technique": "technique",
            "facturation": "facturation",
            "urgent": "urgent",
            "spam": "spam",
            "review": "review",
        },
    )

    for node in ("faq", "technique", "facturation", "urgent", "spam", "review"):
        graph.add_edge(node, END)

    return graph.compile(checkpointer=checkpointer)
