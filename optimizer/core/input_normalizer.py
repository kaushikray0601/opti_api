from dataclasses import dataclass

import numpy as np
import pandas as pd


CABLE_INPUT_COLUMNS = ("cabTag", "cabDesignLen", "cabSpec", "wBS")
DRUM_INPUT_COLUMNS = ("drumTag", "cabSpec", "manufLength")


class OptimizerInputError(ValueError):
    pass


@dataclass(slots=True)
class NormalizedOptimizerInput:
    cable_df: pd.DataFrame
    drum_df: pd.DataFrame
    cable_rows: np.ndarray
    drum_rows: np.ndarray
    cable_data: np.ndarray
    drum_data: np.ndarray
    unique_cable_types: list
    unique_drum_types: list
    unique_wbs: list
    cables_by_type: dict
    drums_by_type: dict


def _select_columns(df, required_columns, entity_name):
    if not isinstance(df, pd.DataFrame):
        raise OptimizerInputError(f"{entity_name} data must be a pandas DataFrame.")

    if df.empty:
        raise OptimizerInputError(f"{entity_name} data must not be empty.")

    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise OptimizerInputError(
            f"{entity_name} data is missing required columns: {missing}"
        )

    return df.loc[:, list(required_columns)].copy()


def _normalize_required_text(series, field_name):
    if series.isna().any():
        raise OptimizerInputError(f"{field_name} contains null values.")

    normalized = series.astype(str).str.strip()
    if (normalized == "").any():
        raise OptimizerInputError(f"{field_name} contains blank values.")

    return normalized


def _normalize_optional_text(series):
    return series.fillna("").astype(str).str.strip()


def _normalize_positive_ints(series, field_name):
    try:
        numeric = pd.to_numeric(series, errors="raise")
    except (TypeError, ValueError) as exc:
        raise OptimizerInputError(f"{field_name} must be numeric.") from exc

    if numeric.isna().any():
        raise OptimizerInputError(f"{field_name} contains null values.")

    integer_values = numeric.astype(np.int64)
    if (integer_values <= 0).any():
        raise OptimizerInputError(f"{field_name} must contain positive values only.")

    return integer_values


def _ordered_unique(values):
    return list(dict.fromkeys(values))


def normalize_cable_dataframe(cable_df):
    normalized = _select_columns(cable_df, CABLE_INPUT_COLUMNS, "Cable")
    normalized["cabTag"] = _normalize_required_text(normalized["cabTag"], "cabTag")
    normalized["cabDesignLen"] = _normalize_positive_ints(
        normalized["cabDesignLen"],
        "cabDesignLen",
    )
    normalized["cabSpec"] = _normalize_required_text(normalized["cabSpec"], "cabSpec")
    normalized["wBS"] = _normalize_optional_text(normalized["wBS"])
    return normalized


def normalize_drum_dataframe(drum_df):
    normalized = _select_columns(drum_df, DRUM_INPUT_COLUMNS, "Drum")
    normalized["drumTag"] = _normalize_required_text(normalized["drumTag"], "drumTag")
    normalized["cabSpec"] = _normalize_required_text(normalized["cabSpec"], "cabSpec")
    normalized["manufLength"] = _normalize_positive_ints(
        normalized["manufLength"],
        "manufLength",
    )
    return normalized


def _build_cable_data(cable_rows):
    cable_count = cable_rows.shape[0]
    cable_data = np.empty((cable_count, 4), dtype=object)
    cable_data[:, 0] = np.arange(cable_count, dtype=np.int32)
    cable_data[:, 1] = cable_rows[:, 1]
    cable_data[:, 2] = cable_rows[:, 2]
    cable_data[:, 3] = cable_rows[:, 3]
    return cable_data


def _build_drum_data(drum_rows):
    drum_count = drum_rows.shape[0]
    drum_data = np.empty((drum_count, 3), dtype=object)
    drum_data[:, 0] = np.arange(drum_count, dtype=np.int32)
    drum_data[:, 1] = drum_rows[:, 1]
    drum_data[:, 2] = drum_rows[:, 2]
    return drum_data


def _index_by_type(index_array, length_array, type_array):
    indexed = {}
    for cable_type in _ordered_unique(type_array.tolist()):
        type_mask = type_array == cable_type
        indexed[cable_type] = (
            index_array[type_mask].copy(),
            length_array[type_mask].copy(),
        )
    return indexed


def normalize_optimizer_inputs(cable_df, drum_df):
    normalized_cable_df = normalize_cable_dataframe(cable_df)
    normalized_drum_df = normalize_drum_dataframe(drum_df)

    cable_rows = normalized_cable_df.to_numpy(copy=True)
    drum_rows = normalized_drum_df.to_numpy(copy=True)

    cable_data = _build_cable_data(cable_rows)
    drum_data = _build_drum_data(drum_rows)

    cable_index = np.arange(cable_rows.shape[0], dtype=np.int32)
    cable_length = normalized_cable_df["cabDesignLen"].to_numpy(dtype=np.int64, copy=True)
    cable_type = normalized_cable_df["cabSpec"].to_numpy(copy=True)

    drum_index = np.arange(drum_rows.shape[0], dtype=np.int32)
    drum_length = normalized_drum_df["manufLength"].to_numpy(dtype=np.int64, copy=True)
    drum_type = normalized_drum_df["cabSpec"].to_numpy(copy=True)

    return NormalizedOptimizerInput(
        cable_df=normalized_cable_df,
        drum_df=normalized_drum_df,
        cable_rows=cable_rows,
        drum_rows=drum_rows,
        cable_data=cable_data,
        drum_data=drum_data,
        unique_cable_types=_ordered_unique(cable_type.tolist()),
        unique_drum_types=_ordered_unique(drum_type.tolist()),
        unique_wbs=_ordered_unique(normalized_cable_df["wBS"].tolist()),
        cables_by_type=_index_by_type(cable_index, cable_length, cable_type),
        drums_by_type=_index_by_type(drum_index, drum_length, drum_type),
    )
