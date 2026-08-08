from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from guancha_api.schemas.contracts import ActionBucket


RuleStatus = Literal["approved", "rejected", "deferred"]


class DecisionRule(BaseModel):
    """A deliberately small, reviewed rule record; conditions are not Python."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(pattern=r"^RULE-[A-Z-]+-[0-9]{3}$")
    rule_version: Literal["v1"]
    status: RuleStatus
    prd_section: str = Field(min_length=1)
    input_fields: tuple[str, ...] = Field(min_length=1)
    condition: Literal[
        "budget_mismatch_without_sample",
        "roast_unknown",
        "style_conflict",
        "marketing_with_missing_core",
        "core_information_insufficient",
    ]
    action_bucket: ActionBucket
    reason: str = Field(min_length=1)
    risk: str = Field(min_length=1)


class RuleDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_version: Literal["v1"]
    rules: tuple[DecisionRule, ...] = Field(min_length=1)


def load_rules(path: Path | None = None) -> tuple[DecisionRule, ...]:
    """Safely parse and validate the only supported finite rule vocabulary."""

    rules_path = path or Path(__file__).with_name("rules_v1.yaml")
    try:
        document = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        parsed = RuleDocument.model_validate(document)
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise ValueError(f"invalid decision rule file: {error}") from error
    rule_ids = [rule.rule_id for rule in parsed.rules]
    if len(rule_ids) != len(set(rule_ids)):
        raise ValueError("decision rule ids must be unique")
    if any(rule.rule_version != parsed.rule_version for rule in parsed.rules):
        raise ValueError("all rules must match the document rule_version")
    return parsed.rules


def load_approved_rules(path: Path | None = None) -> tuple[DecisionRule, ...]:
    return tuple(rule for rule in load_rules(path) if rule.status == "approved")
