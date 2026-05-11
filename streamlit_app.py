"""
Streamlit dashboard: paste CSV of responses, run HHH pipeline, heatmap of criterion failures.

Run: streamlit run streamlit_app.py
"""

from __future__ import annotations

import asyncio
import io
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from loguru import logger

from hhh_judge.pipeline import evaluate_response
from hhh_judge.rubric import load_rubric
from hhh_judge.settings import get_settings


def _parse_csv(text: str) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(text))


async def _eval_all(
    df: pd.DataFrame,
    *,
    rubric_path: Path | None,
    settings,
    truth_threshold: float | None,
    concurrency: int,
) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(concurrency)

    async def one(row_index: int | str, row: pd.Series) -> dict[str, Any]:
        prompt = str(row.get("prompt", ""))
        response = str(row.get("response", ""))
        gt = row.get("ground_truth")
        if gt is None or pd.isna(gt):
            ground_truth = None
        else:
            ground_truth = str(gt).strip() or None

        async with sem:
            try:
                ev = await evaluate_response(
                    prompt,
                    response,
                    ground_truth=ground_truth,
                    truthfulness_min_cosine=truth_threshold,
                    rubric_path=rubric_path,
                    settings=settings,
                )
                return {"row": row_index, "ok": True, "evaluation": ev.model_dump()}
            except Exception as exc:  # noqa: BLE001
                logger.exception("eval failed row {}", row_index)
                return {"row": row_index, "ok": False, "error": str(exc)}

    tasks = [one(idx, row) for idx, row in df.iterrows()]
    return await asyncio.gather(*tasks)


def main() -> None:
    st.set_page_config(page_title="HHH Judge Dashboard", layout="wide")
    st.title("HHH Judge — failure heatmap")
    st.caption("Paste a CSV with columns: `prompt`, `response`, optional `ground_truth`.")

    settings = get_settings()
    rubric_disk_path: Path | None = None

    with st.sidebar:
        st.header("Settings")
        model = st.text_input("Judge model", value=settings.judge_model)
        truth_threshold = st.number_input(
            "Truthfulness min cosine",
            value=float(settings.truthfulness_min_cosine),
            step=0.01,
            format="%.3f",
        )
        concurrency = st.slider("API concurrency", 1, 8, 4)
        rubric_upload = st.file_uploader("Optional custom rubric.yaml", type=["yaml", "yml"])

    csv_text = st.text_area("CSV content", height=220, placeholder="prompt,response\n\"Hi\",\"Hello\"")
    run = st.button("Run evaluation", type="primary")

    if not run:
        return

    if not csv_text.strip():
        st.warning("Provide CSV text.")
        return

    df = _parse_csv(csv_text)
    for col in ("prompt", "response"):
        if col not in df.columns:
            st.error(f"Missing required column: {col}")
            return

    settings.judge_model = model
    if rubric_upload is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".yaml")
        tmp.write(rubric_upload.getvalue())
        tmp.close()
        rubric_disk_path = Path(tmp.name)

    rubric = load_rubric(rubric_disk_path or settings.rubric_path)
    qids = [item.id for item in rubric.all_items()]

    with st.spinner("Running parallel HHH judges…"):
        results = asyncio.run(
            _eval_all(
                df,
                rubric_path=rubric_disk_path,
                settings=settings,
                truth_threshold=float(truth_threshold),
                concurrency=concurrency,
            )
        )

    ok_rows = [r for r in results if r.get("ok")]
    if not ok_rows:
        st.error("No successful evaluations.")
        return

    scored_rows = [r for r in ok_rows if (r["evaluation"].get("scores") or {})]
    if not scored_rows:
        st.info("All rows bypassed the LLM judge (PreEval / truthfulness gate). No rubric heatmap to show.")
        st.json(results)
        return

    score_matrix: list[list[float | None]] = []
    row_labels: list[str] = []
    for r in scored_rows:
        ev = r["evaluation"]
        scores = ev.get("scores") or {}
        row_labels.append(f"row {r['row']}")
        score_matrix.append([float(scores[q]) if q in scores else None for q in qids])

    score_df = pd.DataFrame(score_matrix, columns=qids, index=row_labels)
    fail_df = score_df.map(lambda v: (v is not None and v < 3))
    fail_rate = fail_df.mean(axis=0).sort_values(ascending=False)

    st.subheader("Failure rate heatmap (score < 3)")
    z = fail_rate.values.reshape(1, -1)
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=list(fail_rate.index),
            y=["failure rate"],
            colorscale="Reds",
            zmin=0,
            zmax=1,
            colorbar=dict(title="Rate"),
        )
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=120), xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Mean score per criterion")
    mean_scores = score_df.mean(axis=0, skipna=True).sort_values()
    st.bar_chart(mean_scores)

    st.subheader("Raw evaluations (JSON)")
    st.json(results)


if __name__ == "__main__":
    main()
