

import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

load_dotenv()

from tools.retriever import EvidenceRetriever
from graph import build_debate_graph
from state import DebateState

console = Console()


SAMPLE_CONTEXT_DOCS = [
    "Our engineering team has 12 engineers. Hiring takes 3-4 months and costs ~$40k per hire.",
    "The vendor SaaS tool costs $120k/year with a 2-year lock-in. It covers 80% of our requirements out of the box.",
    "Building in-house would require ~8 months and 3 senior engineers full-time, delaying Q3 product roadmap.",
    "Our data is highly sensitive; the vendor is SOC2 Type II compliant but stores data on US servers only.",
    "Two competitors have adopted the same vendor tool and report 30% faster deployment cycles.",
    "Our CTO prefers owning core infrastructure. The team has strong Python and infra skills.",
    "The vendor offers a $20k/year startup discount for the first 2 years.",
    "Our current manual process costs ~60 hours/month in engineering time at $150/hr = $108k/year.",
]


def print_argument(arg: dict):
    role = arg["role"]
    color = "green" if role == "proponent" else "red"
    label = "Proponent" if role == "proponent" else "Opponent"
    console.print(Panel(
        arg["content"],
        title=f"[bold {color}]Round {arg['round']} — {label}[/]",
        border_style=color,
        padding=(1, 2),
    ))
    if arg.get("fallacies_detected"):
        console.print(f"  [yellow]⚠ Fallacies flagged: {', '.join(arg['fallacies_detected'])}[/]")
    console.print()


def print_verdict(state: DebateState):
    side = state["winning_side"]
    color = {"proponent": "green", "opponent": "red", "tie": "yellow"}.get(side, "white")

    console.print(Rule("[bold]Judge's Verdict[/]"))
    console.print()
    console.print(Panel(
        state["verdict"],
        title=f"[bold {color}]Winner: {side.upper()}  (confidence: {state['confidence_score']:.0%})[/]",
        border_style=color,
        padding=(1, 2),
    ))

    if state.get("reasoning_chain"):
        console.print("\n[bold]Reasoning chain:[/]")
        for i, step in enumerate(state["reasoning_chain"], 1):
            console.print(f"  {i}. {step}")

    if state.get("recommended_action"):
        console.print(Panel(
            state["recommended_action"],
            title="[bold cyan]Recommended action[/]",
            border_style="cyan",
            padding=(1, 2),
        ))


def run_debate(question: str, context_docs: list[str], max_rounds: int = 2):
    console.print(Rule("[bold blue]Multi-Agent Debate System[/]"))
    console.print(f"\n[bold]Question:[/] {question}\n")
    console.print(f"[dim]Running {max_rounds} debate rounds...[/]\n")

    retriever = EvidenceRetriever(docs=context_docs)
    graph = build_debate_graph(retriever)

    initial_state: DebateState = {
        "decision_question": question,
        "context_docs": context_docs,
        "max_rounds": max_rounds,
        "current_round": 1,
        "framed_question": "",
        "debate_rules": "",
        "key_criteria": [],
        "arguments": [],
        "verdict": "",
        "winning_side": "",
        "confidence_score": 0.0,
        "reasoning_chain": [],
        "recommended_action": "",
    }

    final_state = None
    for step in graph.stream(initial_state):
        node_name = list(step.keys())[0]
        state_update = step[node_name]

        if node_name == "moderator":
            console.print(Rule("[dim]Moderator[/]"))
            console.print(f"[bold]Framed:[/] {state_update.get('framed_question', '')}")
            criteria = state_update.get("key_criteria", [])
            if criteria:
                console.print(f"[bold]Criteria:[/] {' · '.join(criteria)}")
            console.print()

        elif node_name in ("proponent", "opponent"):
            for arg in state_update.get("arguments", []):
                print_argument(arg)

        elif node_name == "judge":
            final_state = {**initial_state, **state_update}

    if final_state:
        print_verdict(final_state)

    return final_state


if __name__ == "__main__":
    console.print(Rule("[bold blue]Multi-Agent Debate System[/]"))
    console.print()

    question = console.input("[bold cyan]Enter your decision question:[/] ").strip()
    if not question:
        question = "Should we build our own internal data pipeline orchestration tool or purchase and integrate the vendor SaaS solution?"
        console.print(f"[dim]No input — using sample question.[/]\n")

    rounds_input = console.input("[bold cyan]Number of debate rounds (default 2):[/] ").strip()
    max_rounds = int(rounds_input) if rounds_input.isdigit() and int(rounds_input) > 0 else 2

    use_sample = console.input("[bold cyan]Use sample business context docs? (y/n):[/] ").strip().lower()
    context_docs = SAMPLE_CONTEXT_DOCS if use_sample != "n" else []

    if use_sample == "n":
        console.print("[dim]Enter context docs one per line. Empty line to finish:[/]")
        while True:
            doc = input("> ").strip()
            if not doc:
                break
            context_docs.append(doc)

    run_debate(question=question, context_docs=context_docs, max_rounds=max_rounds)
