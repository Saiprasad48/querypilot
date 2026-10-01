"""Ask QueryPilot a question from the terminal and watch each step run."""

from __future__ import annotations

import argparse
import json
import logging
import time

from qp_api.agent.graph import build_graph


def main() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(prog="qp-ask")
    parser.add_argument("question")
    args = parser.parse_args()
    graph = build_graph()
    started = time.perf_counter()
    final: dict = {}
    for mode, chunk in graph.stream(
        {"question": args.question}, stream_mode=["updates", "values"]
    ):
        if mode == "updates":
            for node, update in chunk.items():
                extra = f"  error: {update['error']}" if update.get("error") else ""
                print(f"  ✓ {node}{extra}")
        else:
            final = chunk
    answer = final.get("answer", {})
    print("\n" + "=" * 70)
    print(f"Intent: {final.get('intent')}   Complexity: {final.get('complexity')}")
    if final.get("sql_executed"):
        print(f"\nPlan:\n{final.get('plan')}")
        print(f"\nSQL:\n{final['sql_executed']}")
        print(f"\nRows returned: {len(final.get('rows', []))}")
    print(f"\nAnswer:\n{answer.get('summary')}")
    for fact in answer.get("key_numbers", []):
        print(f"  • {fact}")
    if answer.get("chart"):
        print(f"\nChart: {json.dumps(answer['chart'])}")
    for f in answer.get("followups", []):
        print(f"  Follow up: {f}")
    usage = final.get("usage", [])
    tokens_in = sum(u["input_tokens"] for u in usage)
    tokens_out = sum(u["output_tokens"] for u in usage)
    print(f"\nLLM calls: {len(usage)}   tokens in/out: {tokens_in}/{tokens_out}")
    for u in usage:
        print(
            f"  {u['call']:<11} {u['role']:<6} {u['model']:<28} in={u['input_tokens']} out={u['output_tokens']}"
        )
    print(f"Steps: {[(s['node'], s['ms']) for s in final.get('steps', [])]}")
    print(f"Total time: {time.perf_counter() - started:.1f}s")


if __name__ == "__main__":
    main()
