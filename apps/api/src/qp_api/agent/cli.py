"""Ask QueryPilot questions from the terminal.

Single question:  qp-ask "How many orders were delivered in 2017?"
Chat with memory: qp-ask --chat
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from qp_api.agent.graph import build_graph, new_turn


def ask(graph: Any, question: str, config: dict[str, Any]) -> None:
    started = time.perf_counter()
    final: dict[str, Any] = {}
    for mode, chunk in graph.stream(
        new_turn(question), config, stream_mode=["updates", "values"]
    ):
        if mode == "updates":
            for node, update in chunk.items():
                extra = f"  error: {update['error']}" if update.get("error") else ""
                print(f"  ✓ {node}{extra}")
        else:
            final = chunk
    answer = final.get("answer", {})
    print("\n" + "=" * 70)
    if final.get("standalone_question") and final["standalone_question"] != question:
        print(f"Understood as: {final['standalone_question']}")
    print(f"Intent: {final.get('intent')}   Complexity: {final.get('complexity')}")
    if final.get("sql_executed"):
        print(f"\nSQL:\n{final['sql_executed']}")
        print(f"\nRows returned: {len(final.get('rows', []))}")
    print(f"\nAnswer:\n{answer.get('summary')}")
    for fact in answer.get("key_numbers", []):
        print(f"  • {fact}")
    for caveat in answer.get("caveats", []):
        print(f"  ⚠ {caveat}")
    if answer.get("chart") and final.get("sql_executed"):
        print(f"\nChart: {json.dumps(answer['chart'])}")
    for f in answer.get("followups", []):
        print(f"  Follow up: {f}")
    usage = final.get("usage", [])
    print(
        f"\nLLM calls: {len(usage)}   tokens in/out: "
        f"{sum(u['input_tokens'] for u in usage)}/{sum(u['output_tokens'] for u in usage)}"
    )
    for u in usage:
        tag = " (cached)" if u.get("cached") else ""
        print(
            f"  {u['call']:<11} {u['role']:<10} {u['model']:<28} "
            f"in={u['input_tokens']} out={u['output_tokens']}{tag}"
        )
    print(f"Steps: {[(s['node'], s['ms']) for s in final.get('steps', [])]}")
    print(f"Total time: {time.perf_counter() - started:.1f}s")


def main() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(prog="qp-ask")
    parser.add_argument("question", nargs="?", help="Ask one question and exit")
    parser.add_argument(
        "--chat", action="store_true", help="Interactive chat with memory"
    )
    args = parser.parse_args()
    graph = build_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "cli"}}
    if args.chat:
        print("QueryPilot chat. Type 'exit' to quit.\n")
        while True:
            question = input("You: ").strip()
            if question.lower() in {"exit", "quit"}:
                break
            if question:
                ask(graph, question, config)
                print()
    elif args.question:
        ask(graph, args.question, config)
    else:
        parser.error("give a question, or use --chat")


if __name__ == "__main__":
    main()
