from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from hhh_judge.llm_judge import judge_all_categories_parallel, merge_category_results
from hhh_judge.models import EvalResult, PreEvalOutcome
from hhh_judge.pre_eval import PreEval
from hhh_judge.rubric import load_rubric
from hhh_judge.scoring import apply_kill_switch, harmlessness_kill_switch_triggered, weighted_average
from hhh_judge.settings import Settings, get_settings


async def evaluate_response(
    user_prompt: str,
    model_response: str,
    *,
    ground_truth: str | None = None,
    truthfulness_min_cosine: float | None = None,
    rubric_path: Path | str | None = None,
    settings: Settings | None = None,
) -> EvalResult:
    """Full hybrid waterfall: PreEval → (optional) parallel HHH judges → weighted score + kill switch."""
    cfg = settings or get_settings()
    path = Path(rubric_path or cfg.rubric_path)
    rubric = load_rubric(path)
    pre = PreEval(cfg)
    pre_out = pre.run(model_response, ground_truth=ground_truth, truthfulness_min_cosine=truthfulness_min_cosine)

    if pre_out.bypass_llm:
        logger.info("Pre-eval bypassed LLM: {}", "; ".join(pre_out.reasons))
        return EvalResult(
            scores={},
            reasoning="; ".join(pre_out.reasons) if pre_out.reasons else "Pre-eval failed.",
            final_weighted_score=0.0,
            pre_eval=pre_out,
            skipped_llm=True,
            harmlessness_kill_switch=False,
        )

    results = await judge_all_categories_parallel(rubric, user_prompt, model_response, cfg)
    scores, reasoning = merge_category_results(results)

    base = weighted_average(scores, rubric)
    kill = harmlessness_kill_switch_triggered(scores, rubric)
    final = apply_kill_switch(base, kill)
    if kill:
        logger.warning("Harmlessness kill switch engaged — final score forced to 0.")

    return EvalResult(
        scores=scores,
        reasoning=reasoning,
        final_weighted_score=final,
        pre_eval=pre_out,
        skipped_llm=False,
        harmlessness_kill_switch=kill,
    )


def evaluate_response_sync(
    user_prompt: str,
    model_response: str,
    **kwargs: Any,
) -> EvalResult:
    import asyncio

    return asyncio.run(evaluate_response(user_prompt, model_response, **kwargs))
