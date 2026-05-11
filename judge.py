#!/usr/bin/env python3
"""CLI: evaluate a single prompt/response pair through the hybrid HHH pipeline."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from rich.console import Console
from rich.table import Table

from hhh_judge.pipeline import evaluate_response
from hhh_judge.settings import get_settings


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="HHH LLM-as-a-Judge (parallel categories + PreEval sieve).")
    p.add_argument("--prompt", required=True, help="Original user prompt.")
    p.add_argument("--response", required=True, help="Model response to grade.")
    p.add_argument("--ground-truth", default=None, help="Optional reference answer for TF–IDF truthfulness gate.")
    p.add_argument(
        "--truthfulness-threshold",
        type=float,
        default=None,
        help="Min cosine similarity vs ground truth (default: from env/settings).",
    )
    p.add_argument("--rubric", type=Path, default=None, help="Path to rubric.yaml (default: bundled).")
    p.add_argument("--model", default=None, help="Override JUDGE_MODEL / settings judge_model.")
    return p


async def _run(args: argparse.Namespace) -> None:
    console = Console()
    settings = get_settings()
    if args.model:
        settings.judge_model = args.model

    result = await evaluate_response(
        args.prompt,
        args.response,
        ground_truth=args.ground_truth,
        truthfulness_min_cosine=args.truthfulness_threshold,
        rubric_path=args.rubric,
        settings=settings,
    )

    table = Table(title="HHH Judge — Summary", show_lines=True)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    table.add_row("Pre-eval passed", str(result.pre_eval.passed))
    table.add_row("Bypassed LLM", str(result.skipped_llm))
    if result.pre_eval.truthfulness_cosine is not None:
        table.add_row("Truthfulness cosine", f"{result.pre_eval.truthfulness_cosine:.4f}")
    if result.pre_eval.reasons:
        table.add_row("Pre-eval notes", "\n".join(result.pre_eval.reasons))
    table.add_row("Harmlessness kill switch", str(result.harmlessness_kill_switch))
    table.add_row("Final weighted score", f"{result.final_weighted_score:.4f}")

    console.print(table)

    if result.scores:
        st = Table(title="Per-rubric scores", show_lines=False)
        st.add_column("Question ID", style="magenta")
        st.add_column("Score", justify="right")

        for qid in sorted(result.scores.keys()):
            score = result.scores[qid]
            style = "green" if score >= 4 else "yellow" if score >= 3 else "red"
            st.add_row(qid, f"[{style}]{score:.2f}[/]")
        console.print(st)

    console.print("\n[bold]Chain-of-thought (aggregated)[/bold]\n")
    console.print(result.reasoning)


def main() -> None:
    args = _build_parser().parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
