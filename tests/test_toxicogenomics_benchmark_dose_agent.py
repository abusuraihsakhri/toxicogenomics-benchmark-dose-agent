"""
Automated Pytest Test Suite for Toxicogenomics Benchmark Dose Agent.
Domain: Clinical & Biomedical AI
Standard: CAP / CLSI / ISO Standards
"""
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import PHIGuard, AuditLogger, SecurityException, AuditTrail
from agents.models import SystemTaskPayload, UrgencyLevel, SystemIntegrityStatus
from agents.workers import InvariantQCWorker, SafetyEscalationWorker, ProtocolConformanceWorker
from agents.supervisor import SystemSupervisor
from cli import main


def test_phi_guard_enforcement():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive for Staphylococcus")

    # Clean text passes
    PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")


def test_specialized_workers():
    # Worker 1: QC Invariant
    p1 = SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=35.0)
    alerts1 = InvariantQCWorker.evaluate(p1)
    assert len(alerts1) == 1
    assert alerts1[0].urgency == UrgencyLevel.ELEVATED

    # Worker 2: Safety
    p2 = SystemTaskPayload(task_id="T2", target_identifier="KEY-02", primary_metric=10.0, is_critical_flag=True)
    alerts2 = SafetyEscalationWorker.evaluate(p2)
    assert len(alerts2) == 1
    assert alerts2[0].urgency == UrgencyLevel.CRITICAL_STAT

    # Worker 3: Protocol Conformance
    p3 = SystemTaskPayload(task_id="T3", target_identifier="KEY-03", primary_metric=10.0, status_descriptor="DISCORDANT_ANOMALY")
    alerts3 = ProtocolConformanceWorker.evaluate(p3)
    assert len(alerts3) == 1


def test_supervisor_consensus_and_audit():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-PROD-01",
        target_identifier="KEY-PROD-01",
        primary_metric=12.0,
        secondary_metric=4.0,
        status_descriptor="NOMINAL"
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.ROUTINE
    assert dossier.integrity_status == SystemIntegrityStatus.VALIDATED
    assert dossier.audit_hash != ""

    # Verify cryptographic audit trail
    assert AuditLogger.verify_integrity() is True

    # CLI tests
    assert main(["audit", "--task-id", "CLI-TEST-01"]) == 0
    assert main(["chat", "Explain", "specifications"]) == 0
    assert main(["verify-audit"]) == 0


def test_input_validation_rejects_nan():
    """Ensure NaN values are rejected by input validation."""
    with pytest.raises(ValueError, match="finite"):
        SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=float("nan"))


def test_input_validation_rejects_infinity():
    """Ensure infinity values are rejected by input validation."""
    with pytest.raises(ValueError, match="finite"):
        SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=float("inf"))


def test_input_validation_rejects_empty_strings():
    """Ensure empty/whitespace-only strings are rejected."""
    with pytest.raises(ValueError, match="empty"):
        SystemTaskPayload(task_id="   ", target_identifier="KEY-01", primary_metric=10.0)


def test_input_validation_strips_whitespace():
    """Ensure string fields are stripped of leading/trailing whitespace."""
    payload = SystemTaskPayload(task_id="  T1  ", target_identifier="  KEY-01  ", primary_metric=10.0)
    assert payload.task_id == "T1"
    assert payload.target_identifier == "KEY-01"


def test_audit_trail_uses_provided_key():
    """Ensure AuditTrail uses the provided secret key."""
    trail = AuditTrail(secret_key="test-key-123")
    assert trail.secret_key == b"test-key-123"


def test_audit_trail_generates_random_key_without_warning_suppression():
    """Ensure AuditTrail generates a random key when none is provided."""
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        trail = AuditTrail()
        # Should have generated a warning about missing AUDIT_SECRET_KEY
        assert len(w) == 1
        assert "AUDIT_SECRET_KEY" in str(w[0].message)
    # Key should be 32 bytes (256 bits)
    assert len(trail.secret_key) == 32


def test_batch_file_not_found_returns_error():
    """Ensure batch command returns error code when input file is missing."""
    result = main(["batch", "-i", "nonexistent_file.csv"])
    assert result == 1
