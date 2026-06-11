from typing import Annotated, TypedDict, Literal
import operator


class Argument(TypedDict):
    role: Literal["proponent", "opponent"]
    round: int
    content: str
    evidence: list[str]
    fallacies_detected: list[str]


class DebateState(TypedDict):
    # Core input
    decision_question: str
    context_docs: list[str]          # business docs for RAG

    # Debate config
    max_rounds: int
    current_round: int

    # Framing (set by Moderator)
    framed_question: str
    debate_rules: str
    key_criteria: list[str]

    # Accumulated arguments (reducer appends each new one)
    arguments: Annotated[list[Argument], operator.add]

    # Judge output
    verdict: str
    winning_side: Literal["proponent", "opponent", "tie", ""]
    confidence_score: float
    reasoning_chain: list[str]
    recommended_action: str
