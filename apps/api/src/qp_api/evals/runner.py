"""Run the golden set through the agent and report execution accuracy, latency and cost.

Usage (from apps/api):
  uv run qp-eval --limit 5            # quick smoke run
  uv run qp-eval                      # full golden set
  uv run qp-eval --ids h01,h02        # specific questions
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from qp_mcp import server as mcp_tools

from qp_api.agent.graph import build_graph, new_turn
from qp_api.config import REPO_ROOT, settings
from qp_api.evals.compare import results_match

EVALS_DIR = REPO_ROOT / "evals"
DIFFICULTIES = ["easy", "medium", "hard"]

def load_golden(path: Path) -> list[dict[str, Any]]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["questions"]

def evaluate_one(graph: Any, item: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        final = graph.invoke(new_turn(item["question"]))
        crash = None
    except Exception as e:  # noqa: BLE001  (a crash is a failed case, not a crashed run)
        final, crash = {}, f"{type(e).__name__}: {e}"
    latency = time.perf_counter() - started
    usage = final.get("usage", [])
    smart_id = settings.qp_model_smart.partition(":")[2]
    result: dict[str, Any] = {
        "id": item["id"],
        "difficulty": item["difficulty"],
        "question": item["question"],
        "latency_s": round(latency, 2),
        "sql": final.get("sql_executed"),
        "attempts": final.get("attempts", 0),
        "llm_calls": len(usage),
        "input_tokens": sum(u["input_tokens"] for u in usage),
        "output_tokens": sum(u["output_tokens"] for u in usage),
        "smart_requested": sum(1 for u in usage if u["role"].startswith("smart")),
        "smart_answered": sum(1 for u in usage if smart_id in u["model"]),
    }
    if crash or not final.get("sql_executed"):
        reason = crash or final.get("error") or f"no SQL produced (intent={final.get('intent')})"
        return {**result, "valid_sql": False, "correct": False, "reason": reason}
    reference = mcp_tools.run_sql(item["sql"])
    ok, reason = results_match(
        reference["columns"], reference["rows"], final["columns"], final["rows"]
    )
    detail = {}
    if not ok:  # keep both results so failures can be diagnosed later
        detail = {
            "expected": {"columns": reference["columns"], "rows": reference["rows"][:10]},
            "got": {"columns": final["columns"], "rows": final["rows"][:10]},
        }
    return {**result, "valid_sql": True, "correct": ok, "reason": reason, **detail}

def _percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(pct * (len(ordered) - 1)))]

def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(results)
    latencies = [r["latency_s"] for r in results]
    by_difficulty = {}
    for d in DIFFICULTIES:
        subset = [r for r in results if r["difficulty"] == d]
        if subset:
            correct = sum(r["correct"] for r in subset)
            by_difficulty[d] = {
                "n": len(subset),
                "correct": correct,
                "accuracy": round(correct / len(subset), 3),
            }
    return {
        "n": n,
        "execution_accuracy": round(sum(r["correct"] for r in results) / n, 3),
        "valid_sql_rate": round(sum(r["valid_sql"] for r in results) / n, 3),
        "by_difficulty": by_difficulty,
        "latency_p50_s": round(statistics.median(latencies), 2),
        "latency_p95_s": round(_percentile(latencies, 0.95), 2),
        "avg_llm_calls": round(sum(r["llm_calls"] for r in results) / n, 2),
        "avg_input_tokens": round(sum(r["input_tokens"] for r in results) / n),
        "avg_output_tokens": round(sum(r["output_tokens"] for r in results) / n),
        "questions_with_repairs": sum(1 for r in results if r["attempts"] > 1),
        "smart_calls_requested": sum(r["smart_requested"] for r in results),
        "smart_calls_answered": sum(r["smart_answered"] for r in results),
    }

def main() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(prog="qp-eval")
    parser.add_argument("--golden", type=Path, default=EVALS_DIR / "golden.yaml")
    parser.add_argument("--limit", type=int, help="Only the first N questions")
    parser.add_argument("--ids", help="Comma separated question ids, e.g. e01,h02")
    parser.add_argument(
        "--delay", type=float, default=13.0,
        help="Seconds between questions (stay under free tier requests per minute)",
    )
    parser.add_argument("--use-cache", action="store_true", help="Allow LLM cache hits")
    parser.add_argument("--label", default="run", help="Name for this run in the report file")
    args = parser.parse_args()
    # Honest measurement: by default every call goes to the model, no cache hits.
    settings.llm_cache_enabled = args.use_cache
    items = load_golden(args.golden)
    if args.ids:
        wanted = set(args.ids.split(","))
        items = [q for q in items if q["id"] in wanted]
    if args.limit:
        items = items[: args.limit]
    graph = build_graph()
    results = []
    for i, item in enumerate(items, start=1):
        result = evaluate_one(graph, item)
        results.append(result)
        status = "PASS" if result["correct"] else "FAIL"
        print(f"[{i:>2}/{len(items)}] {item['id']} {status}  {result['latency_s']:5.1f}s  {result['reason']}")
        if not result["correct"] and "got" in result:
            print(f"      SQL:      {result['sql']}")
            print(f"      expected: {result['expected']['columns']} {result['expected']['rows'][:3]}")
            print(f"      got:      {result['got']['columns']} {result['got']['rows'][:3]}")
        if i < len(items):
            time.sleep(args.delay)
    summary = summarize(results)
    report = {
        "label": args.label,
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "models": {"fast": settings.qp_model_fast, "smart": settings.qp_model_smart},
        "cache_enabled": args.use_cache,
        "summary": summary,
        "results": results,
    }
    out_dir = EVALS_DIR / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"{stamp}-{args.label}.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print("\n" + json.dumps(summary, indent=2))
    print(f"\nReport saved to {out_path}")

if __name__ == "__main__":
    main()