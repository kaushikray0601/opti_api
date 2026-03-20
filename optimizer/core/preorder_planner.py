"""Synthetic drum planning for the pre-order workflow."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math

import numpy as np

from optimizer.core.dp_engine import modified_search_algo
from optimizer.core.ds_settings_parser import (
    DEFAULT_FALLBACK_TAG_PATTERN,
    DEFAULT_PROJECT_NAME,
    ParsedDSSettings,
)
from optimizer.core.input_normalizer import normalize_cable_inputs
from optimizer.core.tag_builder import TagPatternError, pattern_uses_cable_type, render_tag_pattern


class PreOrderPlanningError(ValueError):
    """Raised when pre-order planning cannot produce a valid drum schedule."""


@dataclass(slots=True)
class PlanInputs:
    cable_rows: np.ndarray
    drum_rows: np.ndarray
    drum_data: np.ndarray
    drum_schedule: list


def build_preorder_plan(cable_df, parsed_settings: ParsedDSSettings) -> PlanInputs:
    normalized_cable_input = normalize_cable_inputs(cable_df)
    _validate_preorder_inputs(normalized_cable_input, parsed_settings)

    generated_drum_rows = []
    drum_schedule = []
    existing_tags = set()

    per_type_sequence = defaultdict(lambda: parsed_settings.seq_start)
    global_sequence = parsed_settings.seq_start
    reset_sequence_by_type = pattern_uses_cable_type(parsed_settings.tag_pattern)

    for current_cable_type in normalized_cable_input.unique_cable_types:
        limit_rule = parsed_settings.drum_limits_by_cable_type[current_cable_type]
        remaining_cable_index, remaining_cable_length = _copy_cable_group(
            normalized_cable_input.cables_by_type[current_cable_type]
        )
        drum_schedule_for_type = []

        while remaining_cable_index:
            wastage, allocated_cables = modified_search_algo(
                limit_rule.max_length_m,
                remaining_cable_index,
                remaining_cable_length,
                current_cable_type,
            )

            if not allocated_cables:
                raise PreOrderPlanningError(
                    f"Unable to plan a pre-order drum for cable type {current_cable_type} within the configured maximum length."
                )

            used_length = limit_rule.max_length_m - int(wastage)
            ordered_length = _calculate_ordered_length(
                used_length=used_length,
                min_length=limit_rule.min_length_m,
                max_length=limit_rule.max_length_m,
                std_length_multiple=parsed_settings.std_drum_len_mult,
            )
            ordered_leftover = ordered_length - used_length

            if reset_sequence_by_type:
                sequence_number = per_type_sequence[current_cable_type]
                per_type_sequence[current_cable_type] += 1
            else:
                sequence_number = global_sequence
                global_sequence += 1

            drum_tag = _build_unique_drum_tag(
                tag_pattern=parsed_settings.tag_pattern,
                project_name=parsed_settings.project_name or DEFAULT_PROJECT_NAME,
                cable_type=current_cable_type,
                sequence_number=sequence_number,
                existing_tags=existing_tags,
            )
            existing_tags.add(drum_tag)

            drum_index = len(generated_drum_rows)
            generated_drum_rows.append([drum_tag, current_cable_type, ordered_length])
            drum_schedule_for_type.append([drum_index, [ordered_leftover, allocated_cables]])

            remaining_cable_index, remaining_cable_length = _remove_allocated_cables(
                remaining_cable_index,
                remaining_cable_length,
                allocated_cables,
            )

        drum_schedule.append(drum_schedule_for_type)

    drum_rows = np.array(generated_drum_rows, dtype=object)
    return PlanInputs(
        cable_rows=normalized_cable_input.cable_rows,
        drum_rows=drum_rows,
        drum_data=_build_drum_data(drum_rows),
        drum_schedule=drum_schedule,
    )


def _validate_preorder_inputs(normalized_cable_input, parsed_settings):
    missing_limit_types = [
        cable_type
        for cable_type in normalized_cable_input.unique_cable_types
        if cable_type not in parsed_settings.drum_limits_by_cable_type
    ]
    if missing_limit_types:
        missing = ", ".join(sorted(missing_limit_types))
        raise PreOrderPlanningError(
            f"Missing pre-order drum limits for cable types: {missing}"
        )

    for cable_type in normalized_cable_input.unique_cable_types:
        limit_rule = parsed_settings.drum_limits_by_cable_type[cable_type]
        cable_group = normalized_cable_input.cables_by_type[cable_type]
        max_cable_length = max(int(length) for length in cable_group[1])
        if max_cable_length > limit_rule.max_length_m:
            raise PreOrderPlanningError(
                f"Cable type {cable_type} contains a cable longer than the configured maximum drum length."
            )


def _copy_cable_group(cable_group):
    cable_index, cable_length = cable_group
    return list(cable_index.tolist()), [int(length) for length in cable_length.tolist()]


def _calculate_ordered_length(used_length, min_length, max_length, std_length_multiple):
    required_length = max(int(used_length), int(min_length))
    rounded_length = _round_up_to_multiple(required_length, std_length_multiple)
    ordered_length = min(int(max_length), rounded_length)
    return max(ordered_length, int(min_length))


def _round_up_to_multiple(value, multiple):
    if multiple <= 1:
        return int(value)
    return int(math.ceil(value / multiple) * multiple)


def _remove_allocated_cables(remaining_index, remaining_length, allocated_cables):
    allocated_set = set(int(cable_index) for cable_index in allocated_cables)
    next_index = []
    next_length = []
    for cable_index, cable_length in zip(remaining_index, remaining_length):
        if cable_index not in allocated_set:
            next_index.append(cable_index)
            next_length.append(int(cable_length))
    return next_index, next_length


def _build_unique_drum_tag(
    tag_pattern,
    project_name,
    cable_type,
    sequence_number,
    existing_tags,
):
    variables = {
        "PROJECT": project_name or DEFAULT_PROJECT_NAME,
        "CABLE_TYPE": cable_type,
    }

    try:
        candidate_tag = render_tag_pattern(tag_pattern, variables, sequence_number)
    except TagPatternError:
        candidate_tag = _fallback_drum_tag(
            project_name=variables["PROJECT"],
            cable_type=cable_type,
            sequence_number=sequence_number,
        )

    if not candidate_tag or candidate_tag in existing_tags:
        candidate_tag = _fallback_drum_tag(
            project_name=variables["PROJECT"],
            cable_type=cable_type,
            sequence_number=sequence_number,
        )

    if candidate_tag in existing_tags:
        fallback_index = 1
        unique_prefix = candidate_tag
        while candidate_tag in existing_tags:
            candidate_tag = f"{unique_prefix}-{fallback_index:02d}"
            fallback_index += 1

    return candidate_tag


def _fallback_drum_tag(project_name, cable_type, sequence_number):
    try:
        return render_tag_pattern(
            DEFAULT_FALLBACK_TAG_PATTERN,
            {
                "PROJECT": project_name or DEFAULT_PROJECT_NAME,
                "CABLE_TYPE": cable_type,
            },
            sequence_number,
        )
    except TagPatternError:
        return f"DR-{cable_type}-{sequence_number:03d}"


def _build_drum_data(drum_rows):
    drum_count = drum_rows.shape[0]
    drum_data = np.empty((drum_count, 3), dtype=object)
    drum_data[:, 0] = np.arange(drum_count, dtype=np.int32)
    drum_data[:, 1] = drum_rows[:, 1]
    drum_data[:, 2] = drum_rows[:, 2]
    return drum_data
