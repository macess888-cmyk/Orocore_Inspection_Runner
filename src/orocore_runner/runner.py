from __future__ import annotations

import hashlib
import json
import subprocess
import sys

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


FROZEN_PARTICIPANTS = {
    "DELTA-001": (
        "Authority_Composition_Inspector",
        "d83e1aaad685d5431052e459eea50a3ac144d3dd",
    ),
    "DELTA-002": (
        "Hybrid_Witness_Traceability_Model",
        "010740f418a01b8c8c415493b36988df8e43ad68",
    ),
    "DELTA-003": (
        "Orocore_Governed_Continuity_Architecture",
        "6b23f1d677d14b06f742a4d294bcc919d78d8a53",
    ),
    "DELTA-004": (
        "Model_Monitor_Transfer_Inspector",
        "58a1105c18014d2a290d24187cafe597bdc95ea2",
    ),
    "DELTA-005": (
        "Witness_Independence_Inspector",
        "be40c13f23f3e33dc549ecfffe5e81de24541fb8",
    ),
    "COMPOSITION": (
        "Orocore_Inspector_Composition_Contract",
        "d967ba66485c49034e6f9748fd12f59653e8a80f",
    ),
}


DELTA_002_REQUIRED_FIELDS = {
    "transition_id",
    "subject_id",
    "state_before",
    "proposed_transition",
    "evidence",
    "evidence_time",
    "evidence_validity",
    "authority_reference",
    "authority_scope",
    "authority_time",
    "dependency_state",
    "unresolved_obligations",
    "revalidation_trigger",
    "closure_state",
    "provenance",
}


class RunnerHold(RuntimeError):
    """Fail-closed runner HOLD."""


@dataclass(frozen=True)
class EmittedArtifacts:
    result: Path
    receipt: Path
    report: Path
    result_sha256: str


def _git(repo: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    if process.returncode != 0:
        raise RunnerHold(
            f"Git inspection failed for {repo.name}: "
            f"{process.stderr.strip()}"
        )

    return process.stdout.strip()


def verify_frozen_fabric(
    home: Path | None = None,
) -> dict[str, dict[str, str]]:
    root = home or Path.home()

    verified: dict[str, dict[str, str]] = {}

    for participant, (folder, expected_head) in (
        FROZEN_PARTICIPANTS.items()
    ):
        repo = root / folder

        if not repo.is_dir():
            raise RunnerHold(
                f"{participant} repository missing: {repo}"
            )

        actual_head = _git(repo, "rev-parse", "HEAD")

        if actual_head != expected_head:
            raise RunnerHold(
                f"{participant} HEAD changed: {actual_head}"
            )

        status = _git(repo, "status", "--porcelain")

        if status:
            raise RunnerHold(
                f"{participant} working tree is not clean"
            )

        verified[participant] = {
            "repository": folder,
            "head": actual_head,
        }

    return verified


def _install_frozen_import_paths(
    home: Path,
) -> None:
    folders = (
        "Authority_Composition_Inspector",
        "Orocore_Governed_Continuity_Architecture",
        "Model_Monitor_Transfer_Inspector",
        "Witness_Independence_Inspector",
        "Orocore_Inspector_Composition_Contract",
    )

    for folder in reversed(folders):
        src = str(home / folder / "src")

        if src not in sys.path:
            sys.path.insert(0, src)


def _finding_payload(finding: Any) -> dict[str, Any]:
    return {
        "state": finding.state.value,
        "diagnostics": [
            diagnostic.value
            for diagnostic in finding.diagnostics
        ],
    }


def _hold_payload(
    diagnostic: str,
) -> dict[str, Any]:
    return {
        "state": "HOLD",
        "diagnostics": [diagnostic],
    }


def _inspect_transition_evidence(
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    missing = sorted(
        DELTA_002_REQUIRED_FIELDS - set(evidence)
    )

    if missing:
        return {
            "state": "HOLD",
            "diagnostics": [
                "TRANSITION_EVIDENCE_FIELDS_MISSING"
            ],
            "missing_fields": missing,
        }

    if evidence.get("evidence_validity") != "CURRENT":
        return {
            "state": "HOLD",
            "diagnostics": [
                "TRANSITION_EVIDENCE_NOT_CURRENT"
            ],
        }

    return {
        "state": "EVIDENCE_PRESENT",
        "diagnostics": [],
    }


def validate_transition_package(
    package: Mapping[str, Any],
) -> None:
    if package.get("requested_action") != "INSPECT_ONLY":
        raise RunnerHold(
            "Only requested_action=INSPECT_ONLY is supported."
        )

    required = {
        "transition_id",
        "authority",
        "transition_evidence",
        "restriction_continuity",
        "assurance_transfer",
        "witness_independence",
    }

    missing = sorted(required - set(package))

    if missing:
        raise RunnerHold(
            "Transition package missing required surfaces: "
            + ", ".join(missing)
        )


def inspect_transition(
    package: Mapping[str, Any],
    *,
    home: Path | None = None,
) -> dict[str, Any]:
    validate_transition_package(package)

    root = home or Path.home()
    fabric = verify_frozen_fabric(root)

    _install_frozen_import_paths(root)

    from authority_composition_experiment.authority_mutation import (
        inspect_authority_mutation,
    )
    from orocore_review.restriction_continuity import (
        inspect_restriction_continuity,
    )
    from model_monitor_transfer.inspector import (
        inspect_model_monitor_transfer,
    )
    from witness_independence.inspector import (
        inspect_witness_independence,
    )
    from composition_contract.composer import (
        compose_inspector_outputs,
    )

    authority = package["authority"]

    r1 = inspect_authority_mutation(
        prior_authority_state=authority[
            "prior_authority_state"
        ],
        mutation=authority["mutation"],
        resulting_authority_state=authority[
            "resulting_authority_state"
        ],
    )

    r2 = _inspect_transition_evidence(
        package["transition_evidence"]
    )

    continuity = package["restriction_continuity"]

    r3 = inspect_restriction_continuity(
        restriction_before=continuity[
            "restriction_before"
        ],
        handoff=continuity["handoff"],
        restriction_after=continuity[
            "restriction_after"
        ],
        restart=continuity["restart"],
    )

    transfer = package["assurance_transfer"]

    r4 = inspect_model_monitor_transfer(
        validated_pair=transfer["validated_pair"],
        current_pair=transfer["current_pair"],
        transfer_test=transfer["transfer_test"],
    )

    witness = package["witness_independence"]

    r5 = inspect_witness_independence(
        receipts=witness["receipts"],
        source_independence_known=witness[
            "source_independence_known"
        ],
    )

    observations = {
        "DELTA-001": _finding_payload(r1),
        "DELTA-002": r2,
        "DELTA-003": _finding_payload(r3),
        "DELTA-004": _finding_payload(r4),
        "DELTA-005": _finding_payload(r5),
    }

    outputs = [
        {
            "source_inspector": name,
            "state": observations[name]["state"],
            "freshness": "CURRENT",
            "required": True,
        }
        for name in (
            "DELTA-001",
            "DELTA-002",
            "DELTA-003",
            "DELTA-004",
            "DELTA-005",
        )
    ]

    unresolved = [
        output["source_inspector"]
        for output in outputs
        if output["state"] == "HOLD"
    ]

    composition = compose_inspector_outputs(
        outputs=outputs,
        unresolved_dependencies=unresolved,
        conflicts=[],
    )

    return {
        "transition_id": package["transition_id"],
        "runner_state": "INSPECTION_COMPLETE",
        "requested_action": "INSPECT_ONLY",
        "fabric": fabric,
        "observations": observations,
        "composition_input": {
            "outputs": outputs,
            "unresolved_dependencies": unresolved,
            "conflicts": [],
        },
        "composition_result": _finding_payload(
            composition
        ),
        "transition_executed": False,
        "global_pass": False,
        "execution_authority_created": False,
        "claim_truth_created": False,
        "non_claims": [
            "Observation does not create authority",
            "EVIDENCE_PRESENT does not establish truth",
            "PRESERVED does not establish continuation permission",
            "TRANSFER_ESTABLISHED does not establish deployment authority",
            "INDEPENDENCE_ESTABLISHED does not establish claim truth",
            "COMPOSABLE_FOR_FURTHER_REVIEW does not create global PASS",
        ],
    }


def _canonical_json_bytes(
    value: Mapping[str, Any],
) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def render_report(
    result: Mapping[str, Any],
) -> str:
    lines = [
        "OROCORE INSPECTION REPORT",
        "",
        f"Transition: {result['transition_id']}",
        "",
        "OBSERVATIONS",
    ]

    for name in (
        "DELTA-001",
        "DELTA-002",
        "DELTA-003",
        "DELTA-004",
        "DELTA-005",
    ):
        finding = result["observations"][name]
        diagnostics = finding.get(
            "diagnostics",
            [],
        )

        diagnostic_text = (
            ", ".join(diagnostics)
            if diagnostics
            else "-"
        )

        lines.append(
            f"{name}: {finding['state']} "
            f"[{diagnostic_text}]"
        )

    composition = result["composition_result"]

    lines.extend(
        [
            "",
            "COMPOSITION",
            composition["state"],
            "",
            "BOUNDARIES",
            "Global PASS: FALSE",
            "Execution authority: FALSE",
            "Transition executed: FALSE",
            "Claim truth created: FALSE",
            "",
            "Observation != Authority",
            "PASS != Execution Permission",
        ]
    )

    return "\n".join(lines) + "\n"


def emit_artifacts(
    result: Mapping[str, Any],
    output_dir: Path,
) -> EmittedArtifacts:
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_path = output_dir / "inspection_result.json"
    receipt_path = output_dir / "inspection_receipt.json"
    report_path = output_dir / "inspection_report.txt"

    result_bytes = _canonical_json_bytes(result)
    result_hash = _sha256(result_bytes)

    result_path.write_bytes(result_bytes)

    receipt = {
        "artifact": "Orocore Inspection Receipt",
        "transition_id": result["transition_id"],
        "result_sha256": result_hash,
        "composition_state": result[
            "composition_result"
        ]["state"],
        "observed_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "global_pass_created": False,
        "execution_authority_created": False,
    }

    receipt_path.write_bytes(
        _canonical_json_bytes(receipt)
    )

    report_path.write_text(
        render_report(result),
        encoding="utf-8",
    )

    return EmittedArtifacts(
        result=result_path,
        receipt=receipt_path,
        report=report_path,
        result_sha256=result_hash,
    )


def inspect_file(
    source: Path,
    output_dir: Path,
    *,
    home: Path | None = None,
) -> EmittedArtifacts:
    try:
        package = json.loads(
            source.read_text(encoding="utf-8")
        )
    except FileNotFoundError as exc:
        raise RunnerHold(
            f"Transition package not found: {source}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RunnerHold(
            f"Transition package is not valid JSON: {exc}"
        ) from exc

    result = inspect_transition(
        package,
        home=home,
    )

    return emit_artifacts(
        result,
        output_dir,
    )