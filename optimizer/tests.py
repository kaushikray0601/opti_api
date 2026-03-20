import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from optimizer.core.cable_optimizer import control_panel
from optimizer.core.dp_engine import create_dp_table, fill_drums_sequentially, modified_search_algo
from optimizer.core.ds_settings_parser import unpack_ds_settings
from optimizer.core.input_normalizer import (
    OptimizerInputError,
    normalize_cable_dataframe,
    normalize_cable_inputs,
    normalize_drum_dataframe,
    normalize_optimizer_inputs,
)
from optimizer.core.report_builder import build_report, build_schedule_output


class DpEngineTests(SimpleTestCase):
    def test_create_dp_table_skips_lengths_bigger_than_target(self):
        search_table, aux_table = create_dp_table(10, [0, 1], [11, 4], "Cabletype01")
        self.assertEqual(search_table[4], 2)
        self.assertEqual(aux_table, [4])

    def test_modified_search_algo_returns_best_fit_with_wastage(self):
        wastage, chosen = modified_search_algo(10, [100, 101, 102], [6, 4, 3], "Cabletype01")
        self.assertEqual(wastage, 0)
        self.assertEqual(chosen, [101, 100])

    def test_modified_search_algo_returns_full_wastage_when_nothing_fits(self):
        wastage, chosen = modified_search_algo(5, [100, 101], [6, 7], "Cabletype01")
        self.assertEqual(wastage, 5)
        self.assertEqual(chosen, [])

    def test_fill_drums_sequentially_removes_allocated_cables(self):
        schedule = fill_drums_sequentially(
            filt_drum_index=[10, 11],
            filt_drum_len=[10, 6],
            cab_index=[100, 101, 102],
            cab_len=[6, 4, 3],
            cable_type="Cabletype01",
        )
        self.assertEqual(schedule[0][0], 10)
        self.assertEqual(schedule[0][1], [0, [101, 100]])
        self.assertEqual(schedule[1][0], 11)
        self.assertEqual(schedule[1][1], [3, [102]])


class WorkbookLoaderTests(SimpleTestCase):
    def test_normalize_cable_dataframe_keeps_expected_columns(self):
        cable_df = pd.DataFrame(
            {
                "seqNo": [1],
                "cabTag": ["Cabletag001"],
                "cabDesignLen": [233],
                "cabSpec": ["Cabletype01"],
                "wBS": ["SS03"],
                "extra": ["ignored"],
            }
        )
        normalized = normalize_cable_dataframe(cable_df)
        self.assertEqual(list(normalized.columns), ["cabTag", "cabDesignLen", "cabSpec", "wBS"])

    def test_normalize_drum_dataframe_keeps_expected_columns(self):
        drum_df = pd.DataFrame(
            {
                "seqNo": [1],
                "drumTag": ["Drum001"],
                "cabSpec": ["Cabletype01"],
                "manufLength": [1190],
                "extra": ["ignored"],
            }
        )
        normalized = normalize_drum_dataframe(drum_df)
        self.assertEqual(list(normalized.columns), ["drumTag", "cabSpec", "manufLength"])


class InputNormalizerTests(SimpleTestCase):
    def test_normalize_optimizer_inputs_rejects_blank_cable_data(self):
        with self.assertRaisesMessage(OptimizerInputError, "Cable data must not be empty."):
            normalize_optimizer_inputs(
                pd.DataFrame(columns=["cabTag", "cabDesignLen", "cabSpec", "wBS"]),
                pd.DataFrame([{"drumTag": "D1", "cabSpec": "T1", "manufLength": 10}]),
            )

    def test_normalize_optimizer_inputs_rejects_missing_columns(self):
        with self.assertRaisesMessage(OptimizerInputError, "missing required columns"):
            normalize_optimizer_inputs(
                pd.DataFrame([{"cabTag": "C1", "cabDesignLen": 10, "cabSpec": "T1"}]),
                pd.DataFrame([{"drumTag": "D1", "cabSpec": "T1", "manufLength": 10}]),
            )

    def test_normalize_optimizer_inputs_normalizes_nan_wbs(self):
        normalized = normalize_optimizer_inputs(
            pd.DataFrame(
                [
                    {"cabTag": "C1", "cabDesignLen": 10, "cabSpec": "T1", "wBS": None},
                    {"cabTag": "C2", "cabDesignLen": 20, "cabSpec": "T1", "wBS": "W2"},
                ]
            ),
            pd.DataFrame([{"drumTag": "D1", "cabSpec": "T1", "manufLength": 40}]),
        )
        self.assertEqual(normalized.cable_rows[0, 3], "")
        self.assertEqual(normalized.unique_wbs, ["", "W2"])

    def test_normalize_optimizer_inputs_preserves_duplicate_tags_with_stable_indexes(self):
        normalized = normalize_optimizer_inputs(
            pd.DataFrame(
                [
                    {"cabTag": "C1", "cabDesignLen": 10, "cabSpec": "T1", "wBS": "W1"},
                    {"cabTag": "C1", "cabDesignLen": 20, "cabSpec": "T1", "wBS": "W2"},
                ]
            ),
            pd.DataFrame([{"drumTag": "D1", "cabSpec": "T1", "manufLength": 40}]),
        )
        self.assertEqual(normalized.cable_rows[:, 0].tolist(), ["C1", "C1"])
        self.assertEqual(normalized.cable_data[:, 0].tolist(), [0, 1])

    def test_normalize_optimizer_inputs_rejects_non_numeric_lengths(self):
        with self.assertRaisesMessage(OptimizerInputError, "cabDesignLen must be numeric."):
            normalize_optimizer_inputs(
                pd.DataFrame([{"cabTag": "C1", "cabDesignLen": "bad", "cabSpec": "T1", "wBS": "W1"}]),
                pd.DataFrame([{"drumTag": "D1", "cabSpec": "T1", "manufLength": 40}]),
            )

    def test_normalize_cable_inputs_supports_preorder_without_drums(self):
        normalized = normalize_cable_inputs(
            pd.DataFrame(
                [
                    {"cabTag": "C1", "cabDesignLen": 10, "cabSpec": "T1", "wBS": "W1"},
                    {"cabTag": "C2", "cabDesignLen": 8, "cabSpec": "T2", "wBS": "W2"},
                ]
            )
        )
        self.assertEqual(normalized.unique_cable_types, ["T1", "T2"])
        self.assertEqual(normalized.cable_data[:, 0].tolist(), [0, 1])


class DSSettingsParserTests(SimpleTestCase):
    def test_unpack_ds_settings_normalizes_preorder_payload(self):
        parsed = unpack_ds_settings(
            {
                "stage": "PRE-ORDER",
                "preorder_stage_input": {
                    "tag_pattern": "DR-{PROJECT}-{CABLE_TYPE}-{SEQ:3}",
                    "drum_limits_by_cable_type": [
                        {
                            "cab_spec": "T1",
                            "drum_length_min_m": 8,
                            "drum_length_max_m": 12,
                        }
                    ],
                    "cutting_allocation_rules": {
                        "allocation_mode": "free",
                        "seq_start": 5,
                        "std_drum_len_mult": 5,
                    },
                },
            }
        )
        self.assertTrue(parsed.is_pre_order)
        self.assertEqual(parsed.stage, "pre_order")
        self.assertEqual(parsed.project_name, "Project-XYZ")
        self.assertEqual(parsed.seq_start, 5)
        self.assertEqual(parsed.std_drum_len_mult, 5)
        self.assertEqual(parsed.drum_limits_by_cable_type["T1"].max_length_m, 12)


class ReportBuilderTests(SimpleTestCase):
    def test_build_schedule_output_and_report_preserve_contract(self):
        cable_rows = np.array(
            [
                ["C1", 6, "T1", "W1"],
                ["C2", 4, "T1", "W2"],
                ["C3", 3, "T2", "W1"],
            ],
            dtype=object,
        )
        drum_rows = np.array(
            [
                ["D1", "T1", 10],
                ["D2", "T2", 6],
            ],
            dtype=object,
        )
        drum_data = np.array(
            [
                [0, "T1", 10],
                [1, "T2", 6],
            ],
            dtype=object,
        )
        drum_schedule = [
            [[0, [0, [1, 0]]]],
            [[1, [3, [2]]]],
        ]

        json_output = build_schedule_output(cable_rows, drum_rows, drum_data, drum_schedule, 10)
        report = build_report(cable_rows, drum_rows, json_output)

        self.assertEqual(report["statistics"]["no_of_allotted_cables"], 3)
        self.assertEqual(report["statistics"]["no_of_partial_spare_drums"], 1)
        self.assertEqual(report["allot_dr_summary"], [[0, "T1", 10, 0], [1, "T2", 6, 3]])
        self.assertEqual(report["allot_cab_summary"], [[0, "T1", 10], [1, "T2", 3]])
        self.assertEqual(report["allot_cab_list"][0][-2:], ["D1", 0])

    def test_build_report_handles_empty_schedule_output(self):
        cable_rows = np.array(
            [
                ["C1", 6, "T1", "W1"],
                ["C2", 4, "T1", "W2"],
            ],
            dtype=object,
        )
        drum_rows = np.array(
            [
                ["D1", "T2", 10],
                ["D2", "T2", 8],
            ],
            dtype=object,
        )

        report = build_report(cable_rows, drum_rows, [])

        self.assertEqual(report["statistics"]["no_of_drums_used"], 0)
        self.assertEqual(report["statistics"]["no_of_allotted_cables"], 0)
        self.assertEqual(report["statistics"]["no_of_full_spare_drums"], 2)
        self.assertEqual(report["statistics"]["no_of_unAllotted_cables"], 2)
        self.assertEqual(report["unallot_dr_list"], [[0, "D1", "T2", 10], [1, "D2", "T2", 8]])
        self.assertEqual(report["allot_dr_summary"], [])

    def test_build_report_preserves_scheduled_but_empty_drum_behavior(self):
        cable_rows = np.array(
            [
                ["C1", 12, "T1", "W1"],
            ],
            dtype=object,
        )
        drum_rows = np.array(
            [
                ["D1", "T1", 10],
            ],
            dtype=object,
        )
        drum_data = np.array(
            [
                [0, "T1", 10],
            ],
            dtype=object,
        )
        drum_schedule = [
            [[0, [10, []]]],
        ]

        json_output = build_schedule_output(cable_rows, drum_rows, drum_data, drum_schedule, 10)
        report = build_report(cable_rows, drum_rows, json_output)

        self.assertEqual(report["statistics"]["no_of_drums_used"], 1)
        self.assertEqual(report["statistics"]["no_of_allotted_cables"], 0)
        self.assertEqual(report["statistics"]["no_of_partial_spare_drums"], 1)
        self.assertEqual(report["statistics"]["partial_spare_drum_length"], 10)
        self.assertEqual(report["unallot_cab_list"], [[0, "C1", 12, "T1", "W1"]])


class ControlPanelTests(SimpleTestCase):
    def test_control_panel_handles_no_matching_drum_type(self):
        cable_df = pd.DataFrame(
            [
                {"cabTag": "C1", "cabDesignLen": 12, "cabSpec": "T1", "wBS": "W1"},
                {"cabTag": "C2", "cabDesignLen": 8, "cabSpec": "T1", "wBS": "W2"},
            ]
        )
        drum_df = pd.DataFrame(
            [
                {"drumTag": "D1", "cabSpec": "T2", "manufLength": 15},
            ]
        )

        report = control_panel(cable_df, drum_df, ds_settings={})

        self.assertEqual(report["statistics"]["no_of_drums_used"], 0)
        self.assertEqual(report["statistics"]["no_of_allotted_cables"], 0)
        self.assertEqual(report["statistics"]["no_of_full_spare_drums"], 1)
        self.assertEqual(report["statistics"]["no_of_unAllotted_cables"], 2)
        self.assertEqual(report["allot_cab_list"], [])

    def test_control_panel_preorder_generates_synthetic_drums_and_ignores_input_drums(self):
        cable_df = pd.DataFrame(
            [
                {"cabTag": "C1", "cabDesignLen": 11, "cabSpec": "T1", "wBS": "W1"},
                {"cabTag": "C2", "cabDesignLen": 4, "cabSpec": "T1", "wBS": "W2"},
            ]
        )
        drum_df = pd.DataFrame(
            [
                {"drumTag": "IGNORED-1", "cabSpec": "X1", "manufLength": 99},
            ]
        )
        ds_settings = {
            "stage": "pre_order",
            "preorder_stage_input": {
                "tag_pattern": "DR-{PROJECT}-{CABLE_TYPE}-{SEQ:3}",
                "drum_limits_by_cable_type": [
                    {
                        "cab_spec": "T1",
                        "drum_length_min_m": 8,
                        "drum_length_max_m": 12,
                    }
                ],
                "cutting_allocation_rules": {
                    "allocation_mode": "free",
                    "seq_start": 1,
                    "std_drum_len_mult": 5,
                },
            },
        }

        report = control_panel(cable_df, drum_df, ds_settings=ds_settings)

        self.assertEqual(report["statistics"]["no_of_drums"], 2)
        self.assertEqual(report["statistics"]["no_of_drums_used"], 2)
        self.assertEqual(report["statistics"]["no_of_full_spare_drums"], 0)
        self.assertEqual(report["statistics"]["partial_spare_drum_length"], 7)
        self.assertEqual(report["allot_dr_list"][0][2], "DR-Project-XYZ-T1-001")
        self.assertEqual(report["allot_dr_list"][1][2], "DR-Project-XYZ-T1-002")
        self.assertNotIn("IGNORED-1", str(report["ds"]))

    def test_control_panel_preorder_resets_sequence_per_cable_type_when_pattern_uses_cable_type(self):
        cable_df = pd.DataFrame(
            [
                {"cabTag": "C1", "cabDesignLen": 5, "cabSpec": "T1", "wBS": "W1"},
                {"cabTag": "C2", "cabDesignLen": 6, "cabSpec": "T2", "wBS": "W2"},
            ]
        )
        ds_settings = {
            "stage": "pre_order",
            "preorder_stage_input": {
                "tag_pattern": "DR-{PROJECT}-{CABLE_TYPE}-{SEQ:3}",
                "drum_limits_by_cable_type": [
                    {"cab_spec": "T1", "drum_length_min_m": 5, "drum_length_max_m": 10},
                    {"cab_spec": "T2", "drum_length_min_m": 5, "drum_length_max_m": 10},
                ],
                "cutting_allocation_rules": {
                    "allocation_mode": "free",
                    "seq_start": 1,
                    "std_drum_len_mult": 1,
                },
            },
        }

        report = control_panel(cable_df, pd.DataFrame(), ds_settings=ds_settings)
        generated_tags = [row[2] for row in report["allot_dr_list"]]

        self.assertIn("DR-Project-XYZ-T1-001", generated_tags)
        self.assertIn("DR-Project-XYZ-T2-001", generated_tags)

    def test_control_panel_preorder_uses_global_sequence_when_pattern_has_no_cable_type(self):
        cable_df = pd.DataFrame(
            [
                {"cabTag": "C1", "cabDesignLen": 5, "cabSpec": "T1", "wBS": "W1"},
                {"cabTag": "C2", "cabDesignLen": 6, "cabSpec": "T2", "wBS": "W2"},
            ]
        )
        ds_settings = {
            "stage": "pre_order",
            "preorder_stage_input": {
                "tag_pattern": "DR-{PROJECT}-{SEQ:3}",
                "drum_limits_by_cable_type": [
                    {"cab_spec": "T1", "drum_length_min_m": 5, "drum_length_max_m": 10},
                    {"cab_spec": "T2", "drum_length_min_m": 5, "drum_length_max_m": 10},
                ],
                "cutting_allocation_rules": {
                    "allocation_mode": "free",
                    "seq_start": 1,
                    "std_drum_len_mult": 1,
                },
            },
        }

        report = control_panel(cable_df, pd.DataFrame(), ds_settings=ds_settings)
        generated_tags = [row[2] for row in report["allot_dr_list"]]

        self.assertEqual(generated_tags, ["DR-Project-XYZ-001", "DR-Project-XYZ-002"])

    def test_control_panel_preorder_falls_back_to_unique_tags_on_invalid_pattern(self):
        cable_df = pd.DataFrame(
            [
                {"cabTag": "C1", "cabDesignLen": 11, "cabSpec": "T1", "wBS": "W1"},
                {"cabTag": "C2", "cabDesignLen": 4, "cabSpec": "T1", "wBS": "W2"},
            ]
        )
        ds_settings = {
            "stage": "pre_order",
            "preorder_stage_input": {
                "tag_pattern": "DR-{PROJECT}-{UNKNOWN}-{SEQ:3}",
                "drum_limits_by_cable_type": [
                    {
                        "cab_spec": "T1",
                        "drum_length_min_m": 8,
                        "drum_length_max_m": 12,
                    }
                ],
                "cutting_allocation_rules": {
                    "allocation_mode": "free",
                    "seq_start": 1,
                    "std_drum_len_mult": 5,
                },
            },
        }

        report = control_panel(cable_df, pd.DataFrame(), ds_settings=ds_settings)
        generated_tags = [row[2] for row in report["allot_dr_list"]]

        self.assertEqual(generated_tags, ["DR-Project-XYZ-T1-001", "DR-Project-XYZ-T1-002"])
