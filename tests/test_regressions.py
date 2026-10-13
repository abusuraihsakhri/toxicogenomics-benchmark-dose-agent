"""Regressions for batch parsing, audit integrity, and API/browser scope."""
import csv
import json
from pathlib import Path

import pytest

from agents.base import AuditTrail
from agents.llm_factory import LLMFactory
from cli import main as primary_cli, parse_csv_bool as primary_bool
from tox_benchmark.cli import main as secondary_cli, parse_csv_bool as secondary_bool
from tox_benchmark.models import FrontierPayload


@pytest.mark.parametrize("parser", [primary_bool, secondary_bool])
@pytest.mark.parametrize("raw, expected", [
    ("False", False), ("0", False), ("NO", False), ("", False),
    ("True", True), ("1", True), ("yes", True),
])
def test_csv_boolean_parsing(parser, raw, expected):
    assert parser(raw) is expected


@pytest.mark.parametrize("parser", [primary_bool, secondary_bool])
def test_invalid_boolean_rejected(parser):
    with pytest.raises(ValueError):
        parser("sometimes")


@pytest.mark.parametrize("cli", [primary_cli, secondary_cli])
def test_batch_false_does_not_escalate(tmp_path, cli):
    src = tmp_path / "input.csv"
    dest = tmp_path / "output.csv"
    src.write_text(
        "task_id,target_identifier,primary_metric,secondary_metric,is_critical_flag,status_descriptor\n"
        "T1,S1,10,2,False,NOMINAL\n"
        "T2,S2,10,2,True,NOMINAL\n", encoding="utf-8"
    )
    assert cli(["batch", "-i", str(src), "-o", str(dest)]) == 0
    with dest.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    status_key = "overall_urgency" if cli is primary_cli else "overall_status"
    assert rows[0][status_key] in ("ROUTINE", "NOMINAL_OPTIMAL")
    assert "CRITICAL" in rows[1][status_key]


@pytest.mark.parametrize("cli", [primary_cli, secondary_cli])
def test_invalid_batch_row_does_not_write_output(tmp_path, cli):
    src, dest = tmp_path / "bad.csv", tmp_path / "output.csv"
    src.write_text("task_id,target_identifier,primary_metric,is_critical_flag\nT1,S1,nan,False\n", encoding="utf-8")
    assert cli(["batch", "-i", str(src), "-o", str(dest)]) != 0
    assert not dest.exists()


@pytest.mark.parametrize("cli", [primary_cli, secondary_cli])
def test_batch_never_overwrites_input(tmp_path, cli):
    src = tmp_path / "input.csv"
    original = "task_id,target_identifier,primary_metric\nT1,S1,5\n"
    src.write_text(original, encoding="utf-8")
    assert cli(["batch", "-i", str(src), "-o", str(src)]) != 0
    assert src.read_text(encoding="utf-8") == original


def test_audit_hmac_integrity_and_snapshot():
    trail = AuditTrail(secret_key="test-only-secret")
    trail.log("test", "supervisor", "EVALUATE", {"ok": True})
    trail.log("test", "supervisor", "COMPLETE", {"ok": True})
    assert trail.verify_integrity()
    snapshot = trail.get_trail()
    snapshot[0]["current_hash"] = "0" * 64
    assert trail.verify_integrity()  # no mutable reference to internal records
    trail.logs[0]["payload_hash"] = "0" * 64
    assert not trail.verify_integrity()  # cryptographic verification, not link checks alone


def test_frontier_payload_rejects_nonfinite():
    with pytest.raises(ValueError):
        FrontierPayload("T1", "S1", float("inf"), 1.0, "NOMINAL")


def test_unimplemented_model_providers_fail_closed():
    with pytest.raises(ValueError, match="not implemented"):
        LLMFactory.create("openai")


def test_fastapi_serves_browser_and_real_audit():
    from fastapi.testclient import TestClient
    from agents.api import app
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    page = client.get("/")
    assert page.status_code == 200
    assert "does not fit dose" in page.text
    result = client.post("/api/audit", json={
        "task_id":"API-1", "target_identifier":"S1",
        "primary_metric":10, "secondary_metric":2,
        "status_descriptor":"NOMINAL", "is_critical_flag":False
    })
    assert result.status_code == 200
    assert result.json()["overall_urgency"] == "ROUTINE"
