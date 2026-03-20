Based on the current code, ds_settings is an extensible JSON-style Python dict that carries optimizer-control metadata, not cable/drum row data. It is assembled in optimizer_api/views.py (line 344), enriched for pre-order in optimizer_api/views.py (line 389), then copied and given a stage just before the external optimizer call in optimizer_api/views.py (line 450). The handler then normalizes that stage to the legacy lowercase values expected by the external optimizer in optimizer_api/api_handler.py (line 84).

The most important thing to tell the optimizer coding agent is this: ds_settings is not a rigid closed schema in this repo. It is a dict with a small set of known keys plus possible passthrough metadata. The guaranteed/currently meaningful keys are stage and, for pre-order only, preorder_stage_input.

Exact shape today

Minimal post-order shape actually sent out:

{
  "stage": "post_order"
}
Possible post-order shape if upstream code has already put extra metadata into setting_metadata:

{
  "share_mode": "free",
  "stage": "post_order"
}
Current pre-order shape sent out:
{
  "stage": "pre_order",
  "preorder_stage_input": {
    "drum_limits_by_cable_type": [
      {
        "cab_spec": "TYPE-A",
        "drum_length_min_m": 500,
        "drum_length_max_m": 1000
      }
    ],
    "cutting_allocation_rules": {
      "allocation_mode": "partial_wbs",
      "seq_start": 1,
      "reserve_margin_cable_m": 2,
      "reserve_margin_drum_m": 2,
      "cut_waste_per_cut_m": 2,
      "min_joint_seg_m": 2,
      "min_first_joint_seg_m": 50,
      "std_drum_len_mult": 1
    },
    "allocation_mode": "partial_wbs",
    "tag_pattern": "DR-{PROJECT}-{SEQ:3}"
  }
}

One subtle detail: OptimizerRun.settings_snapshot stores setting_metadata before stage is injected, so the snapshot and the outbound ds_settings are not identical. The snapshot is written in optimizer_api/views.py (line 419), while stage is appended only later in optimizer_api/views.py (line 450).

Top-level fields

stage
Type: str

Purpose: tells the external optimizer whether the run is pre-order or post-order. Internally the view normalizes incoming form values to canonical Django enum values like PRE_ORDER / POST_ORDER, then the API handler converts them to the legacy wire-format pre_order / post_order in optimizer_api/api_handler.py (line 64).

Accepted upstream variants:

PRE
PRE_ORDER
PRE-ORDER
PREORDER
POST
POST_ORDER
POST-ORDER
POSTORDER
Outbound values the optimizer should really expect:

pre_order
post_order
How to interpret it:

pre_order: use preorder_stage_input and ignore uploaded drum sheet semantics, because pre-order explicitly forces drums to []
post_order: normal optimizer flow with uploaded drums
preorder_stage_input
Type: dict
Present only for pre-order runs.

Purpose: this is the actual pre-order rule package. It replaces the need to rely on uploaded drum inventory. The view creates it in optimizer_api/views.py (line 389), and pre-order also forces raw_drum_data = "[]" in optimizer_api/views.py (line 404).

Other top-level keys
Type: arbitrary JSON-compatible values

Purpose: passthrough metadata from setting_metadata. The repo does not define a complete fixed list. Tests show share_mode can exist, for example in optimizer_api/tests.py (line 513). The current real upload parser does not populate setting_metadata at all in fileops/file_validator.py (line 625), so in today’s runtime these extra keys are usually absent unless another path injects them.

Inside preorder_stage_input

drum_limits_by_cable_type
Type: list[dict]

Purpose: per-cable-type allowed drum length range. This is the pre-order substitute for a physical drum stock sheet. Parsed and validated in optimizer_api/views.py (line 186).

Each item has:

cab_spec
Type: str
Purpose: cable type / cable catalogue type / spec that this limit row applies to.
Validation: required, non-empty.

drum_length_min_m
Type: int
Purpose: minimum allowed drum length in meters for that cable type.
Validation: must be > 0.

drum_length_max_m
Type: int
Purpose: maximum allowed drum length in meters for that cable type.
Validation: must be > 0 and >= drum_length_min_m.

cutting_allocation_rules
Type: dict

Purpose: detailed operational rules for how the optimizer should cut and allocate drums in pre-order mode.

Fields inside it:

allocation_mode
Type: str
Allowed values:

free
wbs
partial_wbs
Purpose:

free: optimizer can allocate freely
wbs: keep allocation constrained by WBS
partial_wbs: allow controlled sharing across WBS boundaries
This enum is validated in optimizer_api/views.py (line 99).

seq_start
Type: int
Purpose: first sequence number to use when generating drum tags from the pattern.
Validation: >= 1

reserve_margin_cable_m
Type: int
Purpose: extra reserve length to keep per cable.
Validation: >= 0

reserve_margin_drum_m
Type: int
Purpose: extra reserve length to keep per drum.
Validation: >= 0

cut_waste_per_cut_m
Type: int
Purpose: expected waste introduced by each cut.
Validation: >= 0

min_joint_seg_m
Type: int
Purpose: minimum segment length allowed when a joint is involved.
Validation: >= 0

min_first_joint_seg_m
Type: int
Purpose: stricter minimum for the first jointed segment.
Validation: >= 0

std_drum_len_mult
Type: int
Purpose: multiplier for standard drum length sizing logic.
Validation: >= 1

allocation_mode
Type: str
Purpose: duplicated again at the root of preorder_stage_input. This is redundant with cutting_allocation_rules["allocation_mode"]. I read this as a convenience/compatibility duplicate rather than a separate meaning.

tag_pattern
Type: str
Purpose: template used to generate pre-order drum tags, for example DR-{PROJECT}-{SEQ:3}.
Validation: required, non-empty.

How the optimizer agent should unpack it

Use defensive unpacking, because:

ds_settings may be {} on fallback retry
preorder_stage_input only exists for pre-order
extra top-level keys may appear in the future
unknown keys should not break parsing

def unpack_ds_settings(ds_settings: dict | None) -> dict:
    ds_settings = ds_settings or {}

    stage = str(ds_settings.get("stage") or "").strip().lower()
    preorder = ds_settings.get("preorder_stage_input") or {}

    limits = preorder.get("drum_limits_by_cable_type") or []
    rules = preorder.get("cutting_allocation_rules") or {}

    return {
        "stage": stage,  # expected: pre_order / post_order
        "is_pre_order": stage == "pre_order",

        "preorder_stage_input": preorder,

        "allocation_mode": (
            preorder.get("allocation_mode")
            or rules.get("allocation_mode")
        ),
        "tag_pattern": preorder.get("tag_pattern"),

        "seq_start": rules.get("seq_start"),
        "reserve_margin_cable_m": rules.get("reserve_margin_cable_m"),
        "reserve_margin_drum_m": rules.get("reserve_margin_drum_m"),
        "cut_waste_per_cut_m": rules.get("cut_waste_per_cut_m"),
        "min_joint_seg_m": rules.get("min_joint_seg_m"),
        "min_first_joint_seg_m": rules.get("min_first_joint_seg_m"),
        "std_drum_len_mult": rules.get("std_drum_len_mult"),

        "drum_limits_by_cable_type": limits,

        # preserve extensibility
        "extra_top_level_keys": {
            k: v for k, v in ds_settings.items()
            if k not in {"stage", "preorder_stage_input"}
        },
    }

for row in limits:
    cab_spec = row.get("cab_spec")
    min_len = row.get("drum_length_min_m")
    max_len = row.get("drum_length_max_m")

Important caveats for the optimizer agent

ds_settings can be completely empty. The submitter intentionally retries with ds_settings = {} if the first submit attempt fails and fallback is enabled. That behavior is tested in optimizer_api/tests.py (line 137).
The only field normalized by the Django side is stage. Everything else is passed through as-is.
In the current codebase, pre-order rules are the real source of truth, not the older contract example in Pre_order_work_flow (line 208). That doc still mentions joint_margin_m and drum_share_min_length_m, but the live code now sends the richer cutting_allocation_rules object instead.
In real runtime today, setting_metadata is usually empty unless another pipeline step injects data, because the upload parser only fills cable/drum payloads and file type in fileops/file_validator.py (line 625).
If you want, I can also turn this into a copy-paste handoff note for the optimizer agent in a “contract spec” format.