from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class QuestionValueConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    minimum_value_score: int = Field(ge=0)
    field_relevance: dict[str, int]
    field_answerability: dict[str, int]
    interaction_cost: int = Field(ge=0)


def load_question_value_config(path: Path | None = None) -> QuestionValueConfig:
    source = path or Path(__file__).with_name("question_value_v1.yaml")
    return QuestionValueConfig.model_validate(yaml.safe_load(source.read_text(encoding="utf-8")))
