import json
from pathlib import Path


ROOT = Path(__file__).parent.parent

CONTRACT = (
    ROOT
    / "docs"
    / "RUNNER_FOUNDATION_CONTRACT.json"
)

EXAMPLE = (
    ROOT
    / "examples"
    / "transition.example.json"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_foundation_contract_exists() -> None:
    assert CONTRACT.exists()


def test_example_transition_exists() -> None:
    assert EXAMPLE.exists()


def test_runner_is_observer_only() -> None:
    contract = load(CONTRACT)

    assert contract["observer_only"] is True
    assert contract["transition_execution_enabled"] is False
    assert contract["remediation_enabled"] is False
    assert contract["deployment_enabled"] is False


def test_runner_creates_no_authority() -> None:
    contract = load(CONTRACT)

    assert contract["execution_authority_created"] is False
    assert contract["global_pass_created"] is False
    assert contract["claim_truth_created"] is False


def test_unknown_policy_is_hold() -> None:
    contract = load(CONTRACT)

    assert contract["unknown_policy"] == "HOLD"


def test_runner_targets_five_inspectors() -> None:
    contract = load(CONTRACT)

    assert contract["inspector_count"] == 5
    assert contract["composition_enabled"] is True


def test_example_requests_inspection_only() -> None:
    example = load(EXAMPLE)

    assert example["requested_action"] == "INSPECT_ONLY"


def test_example_has_all_five_input_surfaces() -> None:
    example = load(EXAMPLE)

    required = {
        "authority",
        "transition_evidence",
        "restriction_continuity",
        "assurance_transfer",
        "witness_independence",
    }

    assert required.issubset(example)


def test_no_result_exists_before_runner_implementation() -> None:
    results = ROOT / "results"

    artifacts = [
        path
        for path in results.iterdir()
        if path.name != ".gitkeep"
    ]

    assert artifacts == []


def test_no_receipt_exists_before_runner_implementation() -> None:
    receipts = ROOT / "receipts"

    artifacts = [
        path
        for path in receipts.iterdir()
        if path.name != ".gitkeep"
    ]

    assert artifacts == []