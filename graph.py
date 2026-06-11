from functools import partial
from langgraph.graph import StateGraph, END

from state import DebateState
from agents.nodes import (
    moderator_node,
    proponent_node,
    opponent_node,
    judge_node,
    should_continue,
)
from tools.retriever import EvidenceRetriever


def build_debate_graph(retriever: EvidenceRetriever) -> StateGraph:
    
    graph = StateGraph(DebateState)

    
    pro_node = partial(proponent_node, retriever=retriever)
    opp_node = partial(opponent_node, retriever=retriever)

  
    graph.add_node("moderator", moderator_node)
    graph.add_node("proponent", pro_node)
    graph.add_node("opponent", opp_node)
    graph.add_node("judge", judge_node)


    graph.set_entry_point("moderator")


    graph.add_edge("moderator", "proponent")
    graph.add_edge("proponent", "opponent")

    graph.add_conditional_edges(
        "opponent",
        should_continue,
        {
            "continue": "proponent",
            "judge": "judge",
        },
    )

    graph.add_edge("judge", END)

    return graph.compile()
