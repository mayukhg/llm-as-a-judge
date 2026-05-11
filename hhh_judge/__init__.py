"""HHH Judge: hybrid rule-based + parallel LLM rubric evaluation."""

from hhh_judge.models import EvalResult
from hhh_judge.pipeline import evaluate_response

__all__ = ["EvalResult", "evaluate_response"]
