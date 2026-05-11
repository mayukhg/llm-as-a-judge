#!/usr/bin/env python3
"""Batch-evaluate rows from CSV or JSONL; write JSON/JSONL results."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from hhh_judge.pipeline import evaluate_response
from hhh_judge.settings import get_settings


async def _eval_row(
    idx: int,
    row: dict[str, Any],
    *,
    rubric_path: Path | None,
    settings,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    prompt = str(row.get("prompt", ""))
    response = str(row.get("response", ""))
    gt = row.get("ground_truth")
    if gt is None or pd.isna(gt):
        ground_truth = None
    else:
        s = str(gt).strip()
        ground_truth = s or None

    async with semaphore:
        try:
            ev = await evaluate_response(
                prompt,
                response,
                ground_truth=ground_truth,
                rubric_path=rubric_path,
                settings=settings,
            )
            payload = ev.model_dump()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Row {} failed: {}", idx, exc)
            payload = {"error": str(exc), "row_index": idx}
    return {"row_index": idx, "prompt": prompt, "evaluation": payload}


async def _run_batch(rows: list[dict[str, Any]], rubric_path: Path | None, settings, concurrency: int) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)
    tasks = [_eval_row(i, r, rubric_path=rubric_path, settings=settings, semaphore=sem) for i, r in enumerate(rows)]
    return await asyncio.gather(*tasks)


def _load_rows(path: Path) -> list[dict[str, Any]]:
    suf = path.suffix.lower()
    if suf == ".csv":
        df = pd.read_csv(path)
        return df.to_dict(orient="records")
    if suf in {".jsonl", ".ndjson"}:
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
        return out
    if suf == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return list(data)
        raise ValueError("JSON input must be a list of objects.")
    raise ValueError(f"Unsupported input format: {suf}")


def main() -> None:
    p = argparse.ArgumentParser(description="Batch HHH evaluation.")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--rubric", type=Path, default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--concurrency", type=int, default=4)
    args = p.parse_args()

    settings = get_settings()
    if args.model:
        settings.judge_model = args.model

    rows = _load_rows(args.input)
    results = asyncio.run(_run_batch(rows, args.rubric, settings, max(1, args.concurrency)))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.suffix.lower() == ".json":
        args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    else:
        with args.output.open("w", encoding="utf-8") as fh:
            for item in results:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    logger.info("Wrote {} row evaluations to {}", len(results), args.output)


if __name__ == "__main__":
    main()
