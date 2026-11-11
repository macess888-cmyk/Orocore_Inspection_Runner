import hashlib
import json

from pathlib import Path

import pytest

from orocore_runner.runner import (
    RunnerHold,
    emit_artifacts,
    inspect_transition,
    verify_frozen_fabric,
)


ROOT = Path(__file__).parent.parent
EXAMPLE = ROOT / "examples" / "transition.operational.json"


def load_example() -> dict:
    return json.loads(
        EXAMPLE.read_text(encoding="utf-8")
    )


def test_frozen_fabric_verifies() -> None:
    fabric = verify_frozen_fabric()

    assert set(fabric) == {
        "DELTA-001",
        "DELTA-002",
        "DELTA-003",
        "DELTA-004",
        "DELTA-005",
        "COMPOSITION",
    }


def test_operational_example_runs_all_surfaces() -> None:
    result = inspect_transition(load_example())

    assert result["observations"]["DELTA-001"]["state"] == "TRACEABLE"
    assert result["observations"]["DELTA-002"]["state"] == "EVIDENCE_PRESENT"
    assert result["observations"]["DELTA-003"]["state"] == "PRESERVED"
    assert (
        result["observations"]["DELTA-004"]["state"]
        == "TRANSFER_ESTABLISHED"
    )
    assert (
        result["observations"]["DELTA-005"]["state"]
        == "INDEPENDENCE_ESTABLISHED"
    )


def test_operational_example_composes_for_review() -> None:
    result = inspect_transition(load_example())

    assert (
        result["composition_result"]["state"]
        == "COMPOSABLE_FOR_FURTHER_REVIEW"
    )
    assert result["composition_result"]["diagnostics"] == []


def test_runner_preserves_non_authority_boundaries() -> None:
    result = inspect_transition(load_example())

    assert result["transition_executed"] is False
    assert result["global_pass"] is False
    assert result["execution_authority_created"] is False
    assert result["claim_truth_created"] is False


def test_artifact_emission_round_trip(
    tmp_path: Path,
) -> None:
    result = inspect_transition(load_example())

    artifacts = emit_artifacts(
        result,
        tmp_path,
    )

    assert artifacts.result.exists()
    assert artifacts.receipt.exists()
    assert artifacts.report.exists()

    digest = hashlib.sha256(
        artifacts.result.read_bytes()
    ).hexdigest().upper()

    assert digest == artifacts.result_sha256

    receipt = json.loads(
        artifacts.receipt.read_text(encoding="utf-8")
    )

    assert receipt["result_sha256"] == digest
    assert receipt["global_pass_created"] is False
    assert receipt["execution_authority_created"] is False


def test_non_inspection_action_holds() -> None:
    package = load_example()
    package["requested_action"] = "EXECUTE"

    with pytest.raises(RunnerHold):
        inspect_transition(package)


def test_missing_surface_holds() -> None:
    package = load_example()
    del package["assurance_transfer"]

    with pytest.raises(RunnerHold):
        inspect_transition(package)