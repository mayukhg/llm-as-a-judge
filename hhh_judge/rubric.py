from __future__ import annotations

from pathlib import Path

import yaml
from loguru import logger

from hhh_judge.models import RubricBundle, RubricItem


def load_rubric(path: Path | str) -> RubricBundle:
    p = Path(path)
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    bundle = RubricBundle.model_validate(raw)
    n = len(bundle.all_items())
    if n != 22:
        logger.warning("Expected 22 rubric questions, found {}", n)
    return bundle
