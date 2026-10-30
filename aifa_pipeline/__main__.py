import argparse
import json
import os
from pathlib import Path
import sys

from .database import ROOT, connect, import_catalog
from .report import write_reports

DEFAULT_INPUT = ROOT / "data/sql_link_pdf - parisa - Sheet1.csv"
DEFAULT_OUTPUT = ROOT / "results/reproduced"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate the AIFA catalog and extract document sections into SQLite.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "extract"):
        command = commands.add_parser(name)
        command.add_argument("--input", type=Path, default=DEFAULT_INPUT)
        command.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
        if name == "extract":
            command.add_argument("--limit", type=int, default=3, help="Maximum distinct document URLs to process")
            command.add_argument("--refresh", action="store_true", help="Download again instead of reusing cached PDFs")
            command.add_argument("--delay", type=float, default=1.0, help="Seconds between documents")
    report = commands.add_parser("report")
    report.add_argument("--database", type=Path, default=DEFAULT_OUTPUT / "aifa.sqlite")
    report.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    sheets = commands.add_parser("sheets-export")
    sheets.add_argument("--database", type=Path, default=DEFAULT_OUTPUT / "aifa.sqlite")
    sheets.add_argument("--spreadsheet-id", required=True)
    sheets.add_argument("--worksheet", required=True)
    sheets.add_argument("--credentials", type=Path, default=Path(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "service_account.json")))
    sheets.add_argument("--plan", type=Path, default=ROOT / "results/sheets_plan.json")
    sheets.add_argument("--apply", action="store_true", help="Apply the proposed cell changes; default is preview only")
    args = parser.parse_args(argv)
    try:
        if args.command in ("build", "extract"):
            args.output.mkdir(parents=True, exist_ok=True)
            with connect(args.output / "aifa.sqlite") as connection:
                import_catalog(connection, args.input)
                results = []
                if args.command == "extract":
                    from .pipeline import process_documents
                    results = process_documents(connection, args.output / "pdf_cache", args.limit, args.refresh, delay=args.delay)
                    (args.output / "extraction_run.json").write_text(json.dumps(results, indent=2) + "\n")
                manifest = write_reports(connection, args.output)
            print(json.dumps(manifest["catalog"], indent=2))
            print(f"Finished. Results: {args.output.resolve()}")
            return 1 if any(r["status"] == "error" for r in results) else 0
        if not args.database.is_file():
            raise ValueError("Database not found; run 'python -m aifa_pipeline build' first")
        with connect(args.database) as connection:
            if args.command == "report":
                write_reports(connection, args.output)
                print(f"Finished. Reports: {args.output.resolve()}")
            else:
                from .sheets import export_sheet
                plan = export_sheet(connection, args.spreadsheet_id, args.worksheet, args.credentials, args.apply)
                args.plan.parent.mkdir(parents=True, exist_ok=True)
                args.plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
                print(f"{'Applied' if args.apply else 'Preview only'}: {plan['cell_count']} cells. Plan: {args.plan}")
        return 0
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
