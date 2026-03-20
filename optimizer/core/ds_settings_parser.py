"""Defensive parsing for optimizer stage settings.

This module keeps the API/task boundary tolerant of partially filled or future
`ds_settings` payloads while exposing the small subset of fields the optimizer
actually needs in the current pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json


DEFAULT_PROJECT_NAME = "Project-XYZ"
DEFAULT_FALLBACK_TAG_PATTERN = "DR-{PROJECT}-{CABLE_TYPE}-{SEQ:3}"


class DSSettingsError(ValueError):
    """Raised when stage settings are structurally invalid for planning."""


@dataclass(slots=True)
class DrumLengthLimit:
    cab_spec: str
    min_length_m: int
    max_length_m: int


@dataclass(slots=True)
class ParsedDSSettings:
    stage: str = "post_order"
    is_pre_order: bool = False
    allocation_mode: str = "free"
    project_name: str = DEFAULT_PROJECT_NAME
    tag_pattern: str = DEFAULT_FALLBACK_TAG_PATTERN
    seq_start: int = 1
    std_drum_len_mult: int = 1
    drum_limits_by_cable_type: dict[str, DrumLengthLimit] = field(default_factory=dict)
    preorder_stage_input: dict = field(default_factory=dict)
    extra_top_level_keys: dict = field(default_factory=dict)


def unpack_ds_settings(ds_settings) -> ParsedDSSettings:
    payload = _coerce_mapping(ds_settings)
    stage = _normalize_stage(payload.get("stage"))
    preorder_stage_input = _coerce_mapping(payload.get("preorder_stage_input"))
    cutting_rules = _coerce_mapping(preorder_stage_input.get("cutting_allocation_rules"))

    allocation_mode = _normalize_text(
        preorder_stage_input.get("allocation_mode")
        or cutting_rules.get("allocation_mode")
        or "free"
    )

    project_name = _first_present_text(
        preorder_stage_input.get("project"),
        preorder_stage_input.get("project_name"),
        payload.get("project"),
        payload.get("project_name"),
        payload.get("PROJECT"),
        default=DEFAULT_PROJECT_NAME,
    )

    seq_start = _coerce_positive_int(cutting_rules.get("seq_start"), default=1)
    std_drum_len_mult = _coerce_positive_int(
        cutting_rules.get("std_drum_len_mult"),
        default=1,
        field_name="std_drum_len_mult",
    )

    tag_pattern = _first_present_text(
        preorder_stage_input.get("tag_pattern"),
        default=DEFAULT_FALLBACK_TAG_PATTERN,
    )

    return ParsedDSSettings(
        stage=stage,
        is_pre_order=stage == "pre_order",
        allocation_mode=allocation_mode or "free",
        project_name=project_name,
        tag_pattern=tag_pattern,
        seq_start=seq_start,
        std_drum_len_mult=std_drum_len_mult,
        drum_limits_by_cable_type=_parse_drum_limits(
            preorder_stage_input.get("drum_limits_by_cable_type")
        ),
        preorder_stage_input=preorder_stage_input,
        extra_top_level_keys={
            key: value
            for key, value in payload.items()
            if key not in {"stage", "preorder_stage_input"}
        },
    )


def _coerce_mapping(value):
    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        text = value.strip()
        if text in {"", "[]", "{}"}:
            return {}

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}

        return parsed if isinstance(parsed, dict) else {}

    return {}


def _normalize_stage(raw_stage) -> str:
    value = _normalize_text(raw_stage).lower()
    if value in {"pre", "pre_order", "pre-order", "preorder"}:
        return "pre_order"
    if value in {"post", "post_order", "post-order", "postorder"}:
        return "post_order"
    return "post_order"


def _normalize_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _first_present_text(*values, default="") -> str:
    for value in values:
        text = _normalize_text(value)
        if text:
            return text
    return default


def _coerce_positive_int(value, default, field_name=""):
    if value in (None, ""):
        return default

    try:
        parsed_value = int(value)
    except (TypeError, ValueError) as exc:
        if field_name:
            raise DSSettingsError(f"{field_name} must be a positive integer.") from exc
        return default

    if parsed_value < 1:
        if field_name:
            raise DSSettingsError(f"{field_name} must be at least 1.")
        return default

    return parsed_value


def _parse_drum_limits(raw_limits) -> dict[str, DrumLengthLimit]:
    if raw_limits in (None, ""):
        return {}

    if not isinstance(raw_limits, list):
        raise DSSettingsError("drum_limits_by_cable_type must be a list.")

    parsed_limits = {}
    for row in raw_limits:
        if not isinstance(row, dict):
            raise DSSettingsError("Each drum limit row must be a mapping.")

        cab_spec = _normalize_text(row.get("cab_spec"))
        if not cab_spec:
            raise DSSettingsError("Each drum limit row requires a non-empty cab_spec.")

        min_length = _coerce_required_positive_int(
            row.get("drum_length_min_m"),
            "drum_length_min_m",
        )
        max_length = _coerce_required_positive_int(
            row.get("drum_length_max_m"),
            "drum_length_max_m",
        )

        if max_length < min_length:
            raise DSSettingsError(
                f"drum_length_max_m must be greater than or equal to drum_length_min_m for {cab_spec}."
            )

        parsed_limits[cab_spec] = DrumLengthLimit(
            cab_spec=cab_spec,
            min_length_m=min_length,
            max_length_m=max_length,
        )

    return parsed_limits


def _coerce_required_positive_int(value, field_name):
    try:
        parsed_value = int(value)
    except (TypeError, ValueError) as exc:
        raise DSSettingsError(f"{field_name} must be a positive integer.") from exc

    if parsed_value < 1:
        raise DSSettingsError(f"{field_name} must be a positive integer.")

    return parsed_value
