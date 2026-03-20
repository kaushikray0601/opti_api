import json
from hashlib import sha256
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from optimizer.core.cable_optimizer import control_panel
from optimizer.core.workbook_loader import load_workbook_inputs


def build_baseline_snapshot(workbook_path, cable_sheet, drum_sheet, ds_report):
    stable_payload = {
        "workbook": str(workbook_path),
        "cable_sheet": cable_sheet,
        "drum_sheet": drum_sheet,
        "statistics": ds_report.get("statistics", {}),
        "allot_cab_summary": ds_report.get("allot_cab_summary", []),
        "allot_dr_summary": ds_report.get("allot_dr_summary", []),
        "unallot_cab_summary": ds_report.get("unallot_cab_summary", []),
        "unallt_dr_summary": ds_report.get("unallt_dr_summary", []),
        "allot_cab_rows": len(ds_report.get("allot_cab_list", [])),
        "unallot_cab_rows": len(ds_report.get("unallot_cab_list", [])),
        "allot_dr_rows": len(ds_report.get("allot_dr_list", [])),
        "unallot_dr_rows": len(ds_report.get("unallot_dr_list", [])),
        "schedule_rows": len(ds_report.get("ds", [])),
    }
    snapshot_json = json.dumps(stable_payload, sort_keys=True, ensure_ascii=True)
    stable_payload["sha256"] = sha256(snapshot_json.encode("utf-8")).hexdigest()
    stable_payload["computeTime"] = ds_report.get("computeTime")
    return stable_payload


class Command(BaseCommand):
    help = "Run the current optimizer against a workbook and emit a stable baseline snapshot."

    def add_arguments(self, parser):
        parser.add_argument(
            "workbook",
            nargs="?",
            default="sample_input.xlsx",
            help="Path to the workbook to baseline.",
        )
        parser.add_argument(
            "--cable-sheet",
            default="Cable",
            help="Sheet name for cable data.",
        )
        parser.add_argument(
            "--drum-sheet",
            default="Drum",
            help="Sheet name for drum data.",
        )
        parser.add_argument(
            "--output",
            default="",
            help="Optional JSON output path for the baseline snapshot.",
        )

    def handle(self, *args, **options):
        workbook_path = Path(options["workbook"]).expanduser().resolve()
        if not workbook_path.exists():
            raise CommandError(f"Workbook not found: {workbook_path}")

        try:
            cable_df, drum_df = load_workbook_inputs(
                workbook_path,
                cable_sheet=options["cable_sheet"],
                drum_sheet=options["drum_sheet"],
            )
        except ImportError as exc:
            raise CommandError(
                "Workbook loading requires openpyxl. Install updated requirements first."
            ) from exc
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        ds_report = control_panel(cable_df, drum_df, ds_settings={})
        if "error" in ds_report:
            raise CommandError(ds_report["error"])

        snapshot = build_baseline_snapshot(
            workbook_path=workbook_path,
            cable_sheet=options["cable_sheet"],
            drum_sheet=options["drum_sheet"],
            ds_report=ds_report,
        )

        output_path = options["output"]
        if output_path:
            output_file = Path(output_path).expanduser().resolve()
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Baseline snapshot written to {output_file}"))

        self.stdout.write(json.dumps(snapshot, indent=2))
