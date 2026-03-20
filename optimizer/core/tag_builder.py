"""Utilities for rendering configurable drum tags."""

from __future__ import annotations

import re


TOKEN_PATTERN = re.compile(r"\{([^{}]+)\}")


class TagPatternError(ValueError):
    """Raised when a configurable tag pattern cannot be rendered safely."""


def pattern_uses_cable_type(tag_pattern: str) -> bool:
    return "{CABLE_TYPE}" in str(tag_pattern or "")


def render_tag_pattern(tag_pattern: str, variables: dict[str, str], sequence_number: int) -> str:
    pattern = str(tag_pattern or "").strip()
    if not pattern:
        raise TagPatternError("Tag pattern is empty.")

    def replace(match):
        token = match.group(1).strip()
        if token == "SEQ":
            return str(sequence_number)
        if token.startswith("SEQ:"):
            width_text = token.split(":", 1)[1]
            try:
                width = int(width_text)
            except ValueError as exc:
                raise TagPatternError(f"Invalid sequence width in token {{{token}}}.") from exc
            if width < 1:
                raise TagPatternError("Sequence width must be at least 1.")
            return f"{sequence_number:0{width}d}"

        value = variables.get(token)
        if value is None:
            raise TagPatternError(f"Unknown tag variable {{{token}}}.")

        normalized_value = str(value).strip()
        if not normalized_value:
            raise TagPatternError(f"Tag variable {{{token}}} resolved to an empty value.")

        return normalized_value

    try:
        rendered = TOKEN_PATTERN.sub(replace, pattern)
    except re.error as exc:
        raise TagPatternError("Invalid tag pattern.") from exc

    if "{" in rendered or "}" in rendered:
        raise TagPatternError("Tag pattern contains unresolved braces.")

    rendered = rendered.strip()
    if not rendered:
        raise TagPatternError("Rendered drum tag is empty.")

    return rendered
