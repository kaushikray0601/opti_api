from pathlib import Path

import pandas as pd
from optimizer.core.input_normalizer import (
    CABLE_INPUT_COLUMNS,
    DRUM_INPUT_COLUMNS,
)


def _select_columns(df, required_columns, sheet_name):
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Sheet '{sheet_name}' is missing required columns: {missing}")

    return df.loc[:, list(required_columns)].copy()


def normalize_cable_dataframe(cable_df):
    return _select_columns(cable_df, CABLE_INPUT_COLUMNS, "Cable")


def normalize_drum_dataframe(drum_df):
    return _select_columns(drum_df, DRUM_INPUT_COLUMNS, "Drum")


def load_workbook_inputs(workbook_path, cable_sheet="Cable", drum_sheet="Drum"):
    workbook_path = Path(workbook_path)

    cable_df = pd.read_excel(workbook_path, sheet_name=cable_sheet)
    drum_df = pd.read_excel(workbook_path, sheet_name=drum_sheet)

    return normalize_cable_dataframe(cable_df), normalize_drum_dataframe(drum_df)
