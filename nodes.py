import json
import re
import time
from functools import partial
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from state import DebateState, Argument
from prompts.system_prompts import (
    MODERATOR_PROMPT,
    PROPONENT_PROMPT,
    OPPONENT_PROMPT,
    JUDGE_PROMPT,
)
from tools.retriever import EvidenceRetriever


def _parse_json(text: str) -> dict:
    if not text or not text.strip():
        return {}
   
    cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
   
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    matches = list(re.finditer(r'\{[^{}]*\}', cleaned, re.DOTALL))
    for match in reversed(matches):
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
    return {}


def _llm(model: str = "llama-3.3-70b-versatile") -> ChatGroq:
    return ChatGroq(model=model, max_tokens=1024)



def moderator_node(state: DebateState) -> dict:
    llm = _llm()
    user_msg = f"""Decision question: {state["decision_question"]}

Business context summary:
{chr(10).join(state.get("context_docs", [])[:3])}

Frame this for structured debate."""

    response = llm.invoke([
        SystemMessage(content=MODERATOR_PROMPT),
        HumanMessage(content=user_msg),
    ])

    parsed = _parse_json(response.content)
    return {
        "framed_question": parsed.get("framed_question", state["decision_question"]),
        "key_criteria": parsed.get("key_criteria", []),
        "debate_rules": parsed.get("debate_rules", ""),
        "current_round": 1,
    }



def proponent_node(state: DebateState, retriever: EvidenceRetriever) -> dict:
    llm = _llm("llama-3.1-8b-instant")
    evidence = retriever.retrieve_for_side(state["framed_question"], "proponent")

    opp_args = [a for a in state.get("arguments", []) if a["role"] == "opponent"]
    last_opp = opp_args[-1]["content"] if opp_args else "None yet."

    user_msg = f"""Question: {state["framed_question"]}
Criteria: {", ".join(state.get("key_criteria", []))}
Round: {state["current_round"]}

Evidence available:
{chr(10).join(f"- {e}" for e in evidence)}

Opponent's last argument:
{last_opp}

Make your argument."""

    response = llm.invoke([
        SystemMessage(content=PROPONENT_PROMPT),
        HumanMessage(content=user_msg),
    ])

    parsed = _parse_json(response.content)
    arg: Argument = {
        "role": "proponent",
        "round": state["current_round"],
        "content": parsed.get("argument", response.content),
        "evidence": parsed.get("evidence_used", evidence),
        "fallacies_detected": parsed.get("fallacies_detected", []),
    }
    time.sleep(3)  
    return {"arguments": [arg]}



def opponent_node(state: DebateState, retriever: EvidenceRetriever) -> dict:
    llm = _llm("llama-3.1-8b-instant")
    evidence = retriever.retrieve_for_side(state["framed_question"], "opponent")

    pro_args = [a for a in state.get("arguments", []) if a["role"] == "proponent"]
    last_pro = pro_args[-1]["content"] if pro_args else "None yet."

    user_msg = f"""Question: {state["framed_question"]}
Criteria: {", ".join(state.get("key_criteria", []))}
Round: {state["current_round"]}

Evidence available:
{chr(10).join(f"- {e}" for e in evidence)}

Proponent's last argument:
{last_pro}

Make your counter-argument."""

    response = llm.invoke([
        SystemMessage(content=OPPONENT_PROMPT),
        HumanMessage(content=user_msg),
    ])

    parsed = _parse_json(response.content)
    arg: Argument = {
        "role": "opponent",
        "round": state["current_round"],
        "content": parsed.get("argument", response.content),
        "evidence": parsed.get("evidence_used", evidence),
        "fallacies_detected": parsed.get("fallacies_detected", []),
    }
    time.sleep(3)  

    return {"arguments": [arg], "current_round": state["current_round"] + 1}



def should_continue(state: DebateState) -> str:
    if state["current_round"] <= state["max_rounds"]:
        return "continue"
    return "judge"



def judge_node(state: DebateState) -> dict:
    llm = _llm("llama-3.3-70b-versatile")  

    transcript = []
    for arg in state.get("arguments", []):
        transcript.append(
            f"[Round {arg['round']} — {arg['role'].upper()}]\n{arg['content']}"
            + (f"\nFallacies detected: {arg['fallacies_detected']}" if arg["fallacies_detected"] else "")
        )

    user_msg = f"""Framed question: {state["framed_question"]}
Key criteria: {", ".join(state.get("key_criteria", []))}

Full debate transcript:
{(chr(10) + chr(10)).join(transcript)}

Deliver your verdict."""

    response = llm.invoke([
        SystemMessage(content=JUDGE_PROMPT),
        HumanMessage(content=user_msg),
    ])

    parsed = _parse_json(response.content)
    return {
        "winning_side": parsed.get("winning_side", "tie"),
        "confidence_score": float(parsed.get("confidence_score", 0.5)),
        "verdict": parsed.get("verdict", ""),
        "reasoning_chain": parsed.get("reasoning_chain", []),
        "recommended_action": parsed.get("recommended_action", ""),
    }
