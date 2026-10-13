"""
Command-Line Interface for ToxBenchmark: Benchmark Dose (BMD/BMDL) & Transcriptomic Hazard Agent.
"""
import argparse
import csv
import json
import sys
from .models import FrontierPayload
from .agents import ToxBenchmarkCoordinator

coordinator = ToxBenchmarkCoordinator()


def parse_csv_bool(value):
    """Interpret explicit CSV boolean values, never Python string truthiness."""
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in ("true", "1", "yes", "y"):
        return True
    if normalized in ("false", "0", "no", "n", ""):
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")



def main(argv=None):
    parser = argparse.ArgumentParser(prog="toxicogenomics-benchmark-dose-agent", description="ToxBenchmark: Benchmark Dose (BMD/BMDL) & Transcriptomic Hazard Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Audit
    p_audit = subparsers.add_parser("audit", help="Run single task evaluation")
    p_audit.add_argument("--task-id", default="TASK-2026-001")
    p_audit.add_argument("--target", default="TARGET-GEN-01")
    p_audit.add_argument("--primary", type=float, default=29.4)
    p_audit.add_argument("--secondary", type=float, default=15.1)
    p_audit.add_argument("--critical", action="store_true")
    p_audit.add_argument("--status", default="DISCORDANT")

    # Chat
    p_chat = subparsers.add_parser("chat", help="System configuration query")
    p_chat.add_argument("query", nargs="+")

    # Batch
    p_batch = subparsers.add_parser("batch", help="Batch process CSV records")
    p_batch.add_argument("-i", "--input", required=True)
    p_batch.add_argument("-o", "--output", default="results.csv")

    # Serve
    p_serve = subparsers.add_parser("serve", help="Launch FastAPI REST server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "audit":
        payload = FrontierPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.status,
            is_critical_flag=args.critical,
        )
        dossier = coordinator.process(payload)
        print("=" * 80)
        print(f"  TOXBENCHMARK: BENCHMARK DOSE (BMD/BMDL) & TRANSCRIPTOMIC HAZARD AGENT")
        print(f"  Domain: Biomedical Scientific Discovery & Multi-Omics | Standard: EPA / EFSA Benchmark Dose (BMD) Technical Guidance")
        print(f"  Task: {dossier['task_id']} | Status: [{dossier['overall_status']}] | Total Alerts: {dossier['total_alerts']}")
        print("=" * 80)
        for a in dossier["alerts"]:
            print(f"\n  [{a['status']}] from {a['origin_agent']}:")
            print(f"  Summary: {a['summary']}")
            print(f"  Details: {a['technical_details']}")
            print(f"  Action:  {a['actionable_remediation']}")
        print("\n" + "=" * 80)
        return 0

    if args.command == "chat":
        ans = coordinator.query_supervisory_chat(" ".join(args.query))
        print(f"\n[ToxBenchmarkCoordinator]:\n{ans}\n")
        return 0

    if args.command == "batch":
        from pathlib import Path
        if Path(args.input).resolve() == Path(args.output).resolve():
            print("Error: Input and output CSV files must differ.", file=sys.stderr)
            return 2
        try:
            with open(args.input, mode="r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames or [])
                required = {"task_id", "target_identifier", "primary_metric"}
                missing = required.difference(fieldnames)
                if missing:
                    raise ValueError(f"Missing required CSV columns: {', '.join(sorted(missing))}")
                rows = list(reader)
            out_fields = list(dict.fromkeys(
                fieldnames + ["overall_status", "total_alerts", "critical_count", "consensus_summary"]
            ))
            out_rows = []
            for line_no, row in enumerate(rows, start=2):
                try:
                    if None in row:
                        raise ValueError("Unexpected extra columns")
                    payload = FrontierPayload(
                        task_id=row.get("task_id") or "",
                        target_identifier=row.get("target_identifier") or "",
                        primary_metric=float(row.get("primary_metric") or "nan"),
                        secondary_metric=float(row.get("secondary_metric") or 0.0),
                        status_descriptor=row.get("status_descriptor") or "NOMINAL",
                        is_critical_flag=parse_csv_bool(row.get("is_critical_flag")),
                    )
                    dossier = coordinator.process(payload)
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"CSV row {line_no}: {exc}") from exc
                out_rows.append({
                    **row,
                    "overall_status": dossier["overall_status"],
                    "total_alerts": dossier["total_alerts"],
                    "critical_count": dossier["critical_count"],
                    "consensus_summary": dossier["consensus_summary"],
                })
            with open(args.output, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=out_fields)
                writer.writeheader()
                writer.writerows(out_rows)
        except (OSError, UnicodeError, csv.Error, ValueError) as exc:
            print(f"Batch processing error: {exc}", file=sys.stderr)
            return 2
        print(f"Processed {len(out_rows)} records -> {args.output}")
        return 0

    if args.command == "serve":
        try:
            import uvicorn
            from .server import create_app
            app = create_app()
            if app:
                print(f"Starting ToxBenchmark: Benchmark Dose (BMD/BMDL) & Transcriptomic Hazard Agent on http://{args.host}:{args.port}")
                uvicorn.run(app, host=args.host, port=args.port)
        except ImportError:
            print("FastAPI / uvicorn not installed. Run 'pip install fastapi uvicorn'")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
