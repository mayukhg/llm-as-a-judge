from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RubricItem(BaseModel):
    id: str
    question: str
    weight: float = 1.0


class RubricBundle(BaseModel):
    helpfulness: list[RubricItem]
    honesty: list[RubricItem]
    harmlessness: list[RubricItem]

    def all_items(self) -> list[RubricItem]:
        return [*self.helpfulness, *self.honesty, *self.harmlessness]

    def by_category(self) -> dict[str, list[RubricItem]]:
        return {
            "helpfulness": self.helpfulness,
            "honesty": self.honesty,
            "harmlessness": self.harmlessness,
        }


class PreEvalOutcome(BaseModel):
    passed: bool
    bypass_llm: bool
    reasons: list[str] = Field(default_factory=list)
    truthfulness_cosine: float | None = None


class CategoryJudgeResult(BaseModel):
    category: Literal["helpfulness", "honesty", "harmlessness"]
    scores: dict[str, float]
    chain_of_thought: str


class EvalResult(BaseModel):
    """Pydantic-validated final evaluation payload."""

    scores: dict[str, float] = Field(description="Per-question scores on a 1–5 scale.")
    reasoning: str = Field(description="Aggregated chain-of-thought from category judges.")
    final_weighted_score: float
    pre_eval: PreEvalOutcome
    skipped_llm: bool = False
    harmlessness_kill_switch: bool = False
