#!/usr/bin/env python3
"""Bootstrap and validate the LOS demo in a new customer environment."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Load the sibling BCL module whether run as a script or imported via importlib.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bcl  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
# Authored spec config is BCL (the single admin-facing import format). The
# config/runtime/* files are per-operator, gitignored, and round-tripped by the
# setup/operator tooling, so they stay JSON.
DEFAULT_CONFIG = ROOT / "config/runtime/demo-environment.json"
STATE_PATH = ROOT / "config/runtime/bootstrap-state.json"
CLI_COMMAND_NAME = "python3 scripts/demo_operator.py"
SCENARIOS = (
    "box-salesforce-los",
)
STATUS_ICONS = {
    "success": "✅",
    "running": "⚙️",
    "skip": "⏭️",
    "warn": "⚠️",
    "fail": "❌",
}
PHASE_WIDTH = 54
SALESFORCE_ADMIN_PERMISSION_SETS = (
    "box__Box_Admin_All_Licenses",
    "box__Docgen_Template_Manager",
    "box__Box_Sign_Admin",
    "LOS_Box_Automate_Integration",
    "LOS_Demo_Operator",
)
FOLDERS = [
    "01 - Application Intake",
    "02 - Borrower Documents",
    "03 - Underwriting",
    "04 - Credit Approval",
    "05 - Closing",
    "06 - Executed Loan Documents",
    "07 - Covenants and Servicing",
    "08 - DocGen Templates",
    "Credit Policies",
]
FOLDER_BINDINGS = {
    "workspace": "workspace",
    "intake": "01 - Application Intake",
    "borrowerDocs": "02 - Borrower Documents",
    "underwriting": "03 - Underwriting",
    "creditApproval": "04 - Credit Approval",
    "closing": "05 - Closing",
    "executed": "06 - Executed Loan Documents",
    "covenants": "07 - Covenants and Servicing",
    "docgen": "08 - DocGen Templates",
    "policies": "Credit Policies",
}
FILE_BINDINGS = {
    "loanApplication": "harborview-loan-application-2026.pdf",
    "termSheetMarkup": "harborview-term-sheet-2026-borrower-markup.pdf",
    "financialStatements": "harborview-financial-statements-fy2025.pdf",
    "taxReturns": "harborview-tax-return-summary-2025.pdf",
    "appraisal": "harborview-appraisal-2026.pdf",
    "insurance": "harborview-insurance-certificate.pdf",
    "docgenCommitmentLetter": "los-commitment-letter-template.docx",
    "docgenCommitmentLetterSalesforce": "los-commitment-letter-salesforce-template.docx",
}
PORTABLE_SPECS = [
    "config/box/automate-workflows.bcl",
    "config/box/https-connectors.bcl",
    "config/box/ai-agent-specs.bcl",
    "config/agentforce/los-react-agentforce-spec.bcl",
    "config/salesforce/los-loan-record.bcl",
    "config/los/expert-routing.bcl",
]
UPLOADS = {
    "02 - Borrower Documents": [
        "output/pdf/harborview-loan-application-2026.pdf",
        "output/pdf/harborview-term-sheet-2026-borrower-markup.pdf",
        "output/pdf/harborview-financial-statements-fy2025.pdf",
        "output/pdf/harborview-tax-return-summary-2025.pdf",
        "output/pdf/harborview-appraisal-2026.pdf",
        "output/pdf/harborview-insurance-certificate.pdf",
    ],
    "08 - DocGen Templates": [
        "output/docgen/los-commitment-letter-template.docx",
        "output/docgen/los-commitment-letter-salesforce-template.docx",
    ],
    "Credit Policies": [
        "sample-data/policies/README.md",
        "sample-data/policies/approved/LOS-LTV-001-standard.md",
        "sample-data/policies/approved/LOS-LTV-002-exception.md",
        "sample-data/policies/approved/LOS-DSCR-001-standard.md",
        "sample-data/policies/approved/LOS-DSCR-002-exception.md",
        "sample-data/policies/approved/LOS-RATE-001-standard.md",
        "sample-data/policies/approved/LOS-RATE-002-exception.md",
        "sample-data/policies/approved/LOS-GUAR-001-standard.md",
        "sample-data/policies/approved/LOS-GUAR-002-exception.md",
    ],
}


class OperatorError(RuntimeError):
    pass


def _shorten_command(command: list[str]) -> str:
    return " ".join(command)


def print_header(title: str) -> None:
    border = "=" * len(title)
    print(f"\n{title}\n{border}")


def ask_confirmation(message: str, *, default: bool = False) -> bool:
    if not sys.stdin.isatty():
        return False
    suffix = " [Y/n]" if default else " [y/N]"
    response = input(f"{message}{suffix}: ").strip().lower()
    if not response:
        return default
    return response in {"y", "yes"}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        try:
            display_path = path.relative_to(ROOT)
        except ValueError:
            display_path = path
        raise OperatorError(
            f"Missing {display_path}. Copy config/runtime/demo-environment.example.json "
            "to config/runtime/demo-environment.json and fill in your environment values."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(path: Path) -> dict[str, Any]:
    """Load a config artifact, dispatching by extension.

    Authored spec config is BCL; runtime files (and test fixtures) are JSON.
    Both yield the same payload shape.
    """
    if str(path).endswith(".bcl"):
        return bcl.load_bcl(path)
    return load_json(path)


def run(command: list[str], *, cwd: Path = ROOT, dry_run: bool = False) -> str:
    printable = _shorten_command(command)
    if dry_run:
        print(f"{STATUS_ICONS['running']} [DRY-RUN] {printable}")
        return ""
    result = subprocess.run(command, cwd=cwd, check=False, text=True, capture_output=True)
    if result.returncode:
        error_output = result.stderr.strip() if result.stderr.strip() else result.stdout.strip()
        raise OperatorError(f"Command failed ({result.returncode}): {printable}\n\n--- Full Output ---\n{error_output}\n--- End Output ---")
    return result.stdout.strip()


def deploy_uibundle(project: Path, *, alias: str, dry_run: bool) -> bool:
    # Deploy the bundle directory itself. `.forceignore` keeps node_modules and the
    # other build inputs out of the package; without it the UIBundle component packs
    # the whole folder (~357 MB) and the Metadata API rejects the 50 MB request.
    command = [
        "sf",
        "project",
        "deploy",
        "start",
        "--target-org",
        alias,
        "--wait",
        "20",
        "--source-dir",
        "force-app/main/default/uiBundles/losreactapp",
    ]
    try:
        run(command, cwd=project, dry_run=dry_run)
        return True
    except OperatorError as e:
        print(f"{STATUS_ICONS['warn']} UIBundle deployment failed (React Multi-Framework may not be enabled): {e}")
        return False


def run_json(command: list[str], *, cwd: Path = ROOT) -> Any:
    output = run(command, cwd=cwd)
    try:
        return json.loads(output)
    except json.JSONDecodeError as error:
        raise OperatorError(f"Command returned invalid JSON: {' '.join(command)}") from error


def run_json_allow_fail(command: list[str], *, cwd: Path = ROOT) -> tuple[int, Any]:
    result = subprocess.run(command, cwd=cwd, check=False, text=True, capture_output=True)
    payload: Any = None
    if result.stdout:
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = None
    return result.returncode, payload


def run_phase(name: str, index: int, total: int, fn, *args, **kwargs) -> None:
    label = f"{index:>2}/{total} {name}"
    print(f"{STATUS_ICONS['running']} {label:<{PHASE_WIDTH}}")
    fn(*args, **kwargs)
    print(f"{STATUS_ICONS['success']} {label}")


def try_run_json(command: list[str], *, cwd: Path = ROOT) -> Any | None:
    result = subprocess.run(command, cwd=cwd, check=False, text=True, capture_output=True)
    if result.returncode:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def find_box_item(parent_id: str, name: str, item_type: str) -> str | None:
    payload = run_json(["box", "folders:items", parent_id, "--fields", "id,type,name", "--max-items", "1000", "--json"])
    if isinstance(payload, dict):
        payload = payload.get("entries") or payload.get("items") or []
    for item in payload:
        if item.get("type") == item_type and item.get("name") == name:
            return str(item["id"])
    return None


def require_tools(names: list[str]) -> list[str]:
    return [name for name in names if shutil.which(name) is None]


def _status(icon: str, message: str) -> None:
    print(f"{icon} {message}")


def box_identity() -> dict[str, Any]:
    payload = run_json(["box", "users:get", "me", "--fields", "id,login,enterprise", "--json"])
    if isinstance(payload, list):
        payload = payload[0]
    return payload


def salesforce_identity(alias: str) -> dict[str, Any]:
    payload = run_json(["sf", "org", "display", "--target-org", alias, "--json"], cwd=ROOT / "los-salesforce-project")
    return payload.get("result", payload)


def assign_salesforce_admin_permission_sets(project: Path, *, alias: str, dry_run: bool) -> None:
    command = ["sf", "org", "assign", "permset"]
    for permission_set in SALESFORCE_ADMIN_PERMISSION_SETS:
        command.extend(["--name", permission_set])
    command.extend(["--target-org", alias, "--json"])
    if dry_run:
        run(command, cwd=project, dry_run=True)
        return

    return_code, payload = run_json_allow_fail(command, cwd=project)
    if not return_code:
        return
    failures = (payload.get("result") or {}).get("failures") if isinstance(payload, dict) else None
    failures = failures if isinstance(failures, list) else []
    non_duplicate_failures = [
        item
        for item in failures
        if not isinstance(item, dict)
        or "Duplicate PermissionSetAssignment" not in str(item.get("message", ""))
    ]
    if failures and not non_duplicate_failures:
        _status(STATUS_ICONS["warn"], "Required Salesforce permission-set assignments already exist; continuing.")
        return
    raise OperatorError(
        "Failed to assign required Salesforce permission sets to the authenticated admin. "
        f"return_code={return_code} result={payload}"
    )


def doctor(config_path: Path, *, offline: bool = False, platform: str = "all") -> None:
    print_header("Doctor")
    config = load_config(config_path)
    tools = ["python3"]
    if platform in ("all", "box"):
        tools.append("box")
    if platform in ("all", "salesforce"):
        tools.extend(["sf", "npm"])
    missing_tools = require_tools(tools)
    problems: list[str] = []
    if missing_tools:
        problems.append("missing commands: " + ", ".join(missing_tools))
    if platform in ("all", "salesforce"):
        if not config.get("salesforce", {}).get("orgAlias"):
            problems.append("salesforce.orgAlias is blank")
        if not config.get("salesforce", {}).get("orgId"):
            problems.append("salesforce.orgId is blank")
    if platform in ("all", "box"):
        if not config.get("box", {}).get("parentFolderId"):
            problems.append("box.parentFolderId is blank")
        if str(config.get("box", {}).get("parentFolderId")) == "0" and not config.get("box", {}).get("allowRootFolder"):
            problems.append("box.parentFolderId is 0 but box.allowRootFolder is not true")
        if not config.get("box", {}).get("enterpriseId"):
            problems.append("box.enterpriseId is blank")
        if not config.get("box", {}).get("operatorLogin"):
            problems.append("box.operatorLogin is blank")
    source_paths = []
    if platform in ("all", "box"):
        source_paths.append(ROOT / "config/box/metadata-templates.bcl")
    if platform in ("all", "salesforce"):
        source_paths.append(ROOT / "los-salesforce-project/sfdx-project.json")
    for path in source_paths:
        if not path.exists():
            problems.append(f"missing repository file: {path.relative_to(ROOT)}")
    if problems:
        raise OperatorError("Doctor found setup issues:\n- " + "\n- ".join(problems))
    if not offline and platform in ("all", "box"):
        box_user = box_identity()
        actual_enterprise = str(box_user.get("enterprise", {}).get("id") or "")
        if actual_enterprise != str(config["box"]["enterpriseId"]):
            raise OperatorError(f"Box enterprise mismatch: authenticated {actual_enterprise or 'unknown'}, configured {config['box']['enterpriseId']}.")
        expected_login = config["box"].get("operatorLogin")
        if expected_login and box_user.get("login") != expected_login:
            raise OperatorError(f"Box user mismatch: authenticated {box_user.get('login')}, configured {expected_login}.")
        run_json(["box", "folders:get", str(config["box"]["parentFolderId"]), "--json"])
    if not offline and platform in ("all", "salesforce"):
        sf_org = salesforce_identity(config["salesforce"]["orgAlias"])
        if str(sf_org.get("id") or "") != str(config["salesforce"]["orgId"]):
            raise OperatorError(f"Salesforce org mismatch: authenticated {sf_org.get('id') or 'unknown'}, configured {config['salesforce']['orgId']}.")
    scope = "local prerequisites" if offline else "authenticated identity, target scope, and local prerequisites"
    _status(STATUS_ICONS["success"], f"Doctor passed for {platform}: {scope} are valid.")


def generate_assets(dry_run: bool) -> None:
    print_header("Generate sample and helper artifacts")
    for script in ["generate_sample_loan_assets.py", "generate_docgen_templates.py"]:
        run([sys.executable, str(ROOT / "scripts" / script)], dry_run=dry_run)
    action = "Would generate" if dry_run else "Generated"
    _status(STATUS_ICONS["success"], f"{action} sample loan documents and Doc Gen templates.")


def box_template_command(template: dict[str, Any]) -> list[str]:
    command = [
        "box", "metadata-templates:create",
        "--display-name", template["displayName"],
        "--template-key", template["templateKey"],
        "--json", "--yes",
    ]
    for field in template["fields"]:
        flag = {"string": "--string", "enum": "--enum", "date": "--date", "float": "--number"}[field["type"]]
        command.extend([flag, field["key"], "--field-key", field["key"]])
        for option in field.get("options", []):
            command.extend(["--option", option])
    return command


def parse_id(output: str) -> str:
    if not output:
        return "DRY_RUN"
    payload = json.loads(output)
    if isinstance(payload, list):
        payload = payload[0]
    identifier = payload.get("id") or payload.get("templateKey")
    if not identifier:
        raise OperatorError("A create command returned JSON without an id or templateKey.")
    return str(identifier)


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def box_foundation(config_path: Path, *, dry_run: bool) -> None:
    config = load_config(config_path)
    doctor(config_path, offline=dry_run, platform="box")
    parent_id = str(config["box"].get("parentFolderId") or "0")
    state: dict[str, Any] = load_json(STATE_PATH) if STATE_PATH.exists() and not dry_run else {}
    box_state = state.setdefault("box", {})
    folders = box_state.setdefault("folders", {})
    templates_state = box_state.setdefault("metadataTemplates", {})
    files_state = box_state.setdefault("files", {})

    root_id = folders.get("workspace")
    if not root_id:
        existing_root = None if dry_run else find_box_item(parent_id, "LOS-2026-Harborview", "folder")
        if existing_root:
            root_id = existing_root
            print(f"REUSE    existing Box workspace: {root_id}")
        else:
            root_output = run(
                ["box", "folders:create", parent_id, "LOS-2026-Harborview", "--json", "--yes"],
                dry_run=dry_run,
            )
            root_id = parse_id(root_output)
        folders["workspace"] = root_id
        if not dry_run:
            save_state(state)
    for name in FOLDERS:
        if name in folders:
            print(f"SKIP     folder already recorded: {name}")
            continue
        existing_folder = None if dry_run else find_box_item(root_id, name, "folder")
        if existing_folder:
            folders[name] = existing_folder
            print(f"REUSE    existing folder: {name}")
        else:
            output = run(["box", "folders:create", root_id, name, "--json", "--yes"], dry_run=dry_run)
            folders[name] = parse_id(output)
        if not dry_run:
            save_state(state)

    templates = bcl.load_bcl(ROOT / "config/box/metadata-templates.bcl")["templates"]
    for template in templates:
        if template["templateKey"] in templates_state:
            print(f"SKIP     metadata template already recorded: {template['templateKey']}")
            continue
        existing_template = None if dry_run else try_run_json([
            "box", "metadata-templates:get", template["templateKey"], "--scope", "enterprise", "--json"
        ])
        if existing_template:
            if isinstance(existing_template, list):
                existing_template = existing_template[0]
            templates_state[template["templateKey"]] = str(existing_template.get("id") or existing_template.get("templateKey"))
            print(f"REUSE    existing metadata template: {template['templateKey']}")
        else:
            output = run(box_template_command(template), dry_run=dry_run)
            templates_state[template["templateKey"]] = parse_id(output)
        if not dry_run:
            save_state(state)

    for folder_name, relative_paths in UPLOADS.items():
        folder_id = folders[folder_name]
        for relative_path in relative_paths:
            source = ROOT / relative_path
            if source.name in files_state:
                print(f"SKIP     file already recorded: {source.name}")
                continue
            if not dry_run and not source.exists():
                raise OperatorError(f"Missing generated asset: {relative_path}. Run generate-assets first.")
            existing_file = None if dry_run else find_box_item(folder_id, source.name, "file")
            if existing_file:
                files_state[source.name] = existing_file
                print(f"REUSE    existing file: {source.name}")
            else:
                output = run(
                    ["box", "files:upload", str(source), "--parent-id", folder_id, "--json", "--yes"],
                    dry_run=dry_run,
                )
                files_state[source.name] = parse_id(output)
            if not dry_run:
                save_state(state)

    if not dry_run:
        try:
            display_state_path = STATE_PATH.relative_to(ROOT)
        except ValueError:
            display_state_path = STATE_PATH
        print(f"Wrote local IDs to {display_state_path} (gitignored).")
    action = "Box foundation plan validated" if dry_run else "Box foundation complete"
    print(f"{action}. Apps, Forms, Automate, Hub, metadata values, and publishing remain browser tasks.")


def metadata_data(values: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for key, value in values.items():
        if isinstance(value, (int, float)):
            rendered = f"#{value}"
        else:
            rendered = str(value)
        result.extend(["--data", f"{key}={rendered}"])
    return result


def seed_metadata(config_path: Path, *, dry_run: bool) -> None:
    doctor(config_path, offline=dry_run, platform="box")
    if not STATE_PATH.exists() and not dry_run:
        raise OperatorError("Box bootstrap state is missing. Run box-foundation first.")
    state = load_json(STATE_PATH) if STATE_PATH.exists() else {"box": {"folders": {}, "files": {}}}
    box_state = state.setdefault("box", {})
    folders = box_state.setdefault("folders", {})
    files = box_state.setdefault("files", {})
    seeded = box_state.setdefault("metadataSeeds", {})
    if dry_run and not STATE_PATH.exists():
        folders.update({"workspace": "DRY_RUN", **{name: "DRY_RUN" for name in FOLDERS}})
        files.update({Path(path).name: "DRY_RUN" for paths in UPLOADS.values() for path in paths})

    seeds: list[tuple[str, str, str, dict[str, Any]]] = [
        ("folder", "workspace", "losLoan", {
            "loanId": "LN-2026-0042", "borrower": "Harborview Logistics",
            "loanType": "Commercial Real Estate", "status": "Underwriting", "loanAmount": 4800000,
            "termMonths": 120, "interestRate": 6.85, "ltv": 85, "dscr": 1.12,
            "region": "Northeast", "collateralType": "Real Estate", "owner": "Alex Bennett",
            "underwriter": "Credit Risk", "riskRating": "High",
            "targetClosingDate": "2026-11-30T00:00:00Z", "maturityDate": "2036-11-30T00:00:00Z",
            "covenantReviewDate": "2027-03-31T00:00:00Z",
        }),
        ("folder", "07 - Covenants and Servicing", "losCovenant", {
            "covenantType": "DSCR Test", "owner": "Portfolio Management",
            "dueDate": "2027-03-31T00:00:00Z", "sourceSection": "Loan Agreement Section 9.3",
            "status": "Open", "reminderWindowDays": 45,
        }),
    ]
    # documentType, versionStatus, policyRisk, aiSummaryStatus, approvalStatus. The term
    # sheet markup is Internal: the bank's analysis of the borrower's paper never reaches
    # the borrower portal, which filters on that value.
    document_values = {
        "harborview-loan-application-2026.pdf": ("Application", "Draft", "Medium", "Complete", "Pending"),
        "harborview-term-sheet-2026-borrower-markup.pdf": ("Term Sheet", "Internal", "Critical", "Needs Review", "Pending"),
        "harborview-financial-statements-fy2025.pdf": ("Financial Statement", "Draft", "High", "Complete", "Pending"),
        "harborview-tax-return-summary-2025.pdf": ("Tax Return", "Draft", "Low", "Complete", "Pending"),
        "harborview-appraisal-2026.pdf": ("Appraisal", "Approved", "High", "Complete", "Approved"),
        "harborview-insurance-certificate.pdf": ("Insurance", "Approved", "Low", "Complete", "Approved"),
    }
    for filename, values in document_values.items():
        seeds.append(("file", filename, "losDocument", {
            "documentType": values[0], "versionStatus": values[1], "policyRisk": values[2],
            "aiSummaryStatus": values[3], "approvalStatus": values[4], "signatureStatus": "Not Required",
        }))
    policy_families = {"LTV": "Loan-to-Value", "DSCR": "Debt Service Coverage", "RATE": "Pricing", "GUAR": "Guaranty"}
    policy_owners = {"LTV": "Credit Risk", "DSCR": "Credit Risk", "RATE": "Pricing Committee", "GUAR": "Loan Documentation"}
    policy_files = sorted(name for name in files if name.startswith("LOS-") and name.endswith(".md"))
    for index, filename in enumerate(policy_files):
        parts = filename.removesuffix(".md").split("-")
        policy_id = "-".join(parts[:3])
        seeds.append(("file", filename, "losPolicy", {
            "policyId": policy_id, "policyFamily": policy_families[parts[1]],
            "position": "Standard" if filename.endswith("standard.md") else "Approved Exception",
            "approvalStatus": "Approved", "owner": policy_owners[parts[1]], "marketScope": "National",
            "lastReviewed": "2026-07-01T00:00:00Z", "nextReview": "2027-01-15T00:00:00Z",
            "usageCount": 12 + index * 7,
        }))

    for item_type, key, template_key, values in seeds:
        seed_key = f"{item_type}:{key}:{template_key}"
        if seed_key in seeded:
            print(f"SKIP     metadata already recorded: {seed_key}")
            continue
        item_id = folders.get(key) if item_type == "folder" else files.get(key)
        if not item_id:
            if dry_run:
                item_id = "DRY_RUN"
            else:
                raise OperatorError(f"Missing Box {item_type} binding for metadata seed: {key}")
        existing_metadata = None if dry_run else try_run_json([
            "box", f"{item_type}s:metadata:get", str(item_id), "--template-key", template_key, "--scope", "enterprise", "--json"
        ])
        if existing_metadata:
            seeded[seed_key] = "existing"
            save_state(state)
            print(f"REUSE    existing metadata: {seed_key}")
            continue
        command = ["box", f"{item_type}s:metadata:create", str(item_id), "--template-key", template_key, "--json", "--yes"]
        command.extend(metadata_data(values))
        run(command, dry_run=dry_run)
        seeded[seed_key] = "DRY_RUN" if dry_run else "applied"
        if not dry_run:
            save_state(state)
    action = "Metadata seed plan validated" if dry_run else "Representative Box metadata applied"
    print(f"{action}.")


def flatten_config(value: Any, prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            flattened.update(flatten_config(child, child_prefix))
    elif not isinstance(value, list):
        flattened[prefix] = value
    return flattened


def runtime_bindings(config: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    bindings = flatten_config(config)
    box_state = state.get("box", {})
    folders = box_state.get("folders", {})
    files = box_state.get("files", {})
    templates = box_state.get("metadataTemplates", {})
    for logical, stored_key in FOLDER_BINDINGS.items():
        bindings[f"box.folders.{logical}"] = folders.get(stored_key, "")
    for logical, filename in FILE_BINDINGS.items():
        bindings[f"box.files.{logical}"] = files.get(filename, "")
    for key, value in templates.items():
        bindings[f"box.metadataTemplates.{key}"] = value
    reviewers = config.get("box", {}).get("reviewerLogins", [])
    bindings["box.reviewers.primary"] = reviewers[0] if reviewers else ""
    return bindings


TOKEN_PATTERN = re.compile(r"\$\{([A-Za-z0-9_.]+)\}")


def resolve_value(value: Any, bindings: dict[str, Any], unresolved: set[str]) -> Any:
    if isinstance(value, dict):
        return {key: resolve_value(child, bindings, unresolved) for key, child in value.items()}
    if isinstance(value, list):
        return [resolve_value(child, bindings, unresolved) for child in value]
    if not isinstance(value, str):
        return value
    full = TOKEN_PATTERN.fullmatch(value)
    if full:
        key = full.group(1)
        replacement = bindings.get(key)
        if replacement in (None, ""):
            unresolved.add(key)
            return value
        return replacement
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        replacement = bindings.get(key)
        if replacement in (None, ""):
            unresolved.add(key)
            return match.group(0)
        return str(replacement)
    return TOKEN_PATTERN.sub(replace, value)


def generated_spec_path(relative: str) -> Path:
    """Path of an environment-resolved spec under config/runtime/generated/.

    Authored specs are BCL, but the resolved output is machine-generated
    runtime JSON (gitignored), so the generated copy carries a ``.json`` suffix.
    """
    return (ROOT / "config/runtime/generated" / Path(relative).relative_to("config")).with_suffix(".json")


def resolve_config(config_path: Path, *, allow_unresolved: bool) -> None:
    config = load_config(config_path)
    state = load_json(STATE_PATH)
    bindings = runtime_bindings(config, state)
    unresolved: set[str] = set()
    output_root = ROOT / "config/runtime/generated"
    for relative in PORTABLE_SPECS:
        source = ROOT / relative
        resolved = resolve_value(load_config(source), bindings, unresolved)
        destination = generated_spec_path(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(resolved, indent=2) + "\n", encoding="utf-8")
    if unresolved and not allow_unresolved:
        raise OperatorError("Unresolved runtime bindings: " + ", ".join(sorted(unresolved)))
    print(f"Generated {len(PORTABLE_SPECS)} resolved specs under {output_root.relative_to(ROOT)}.")
    if unresolved:
        print("Unresolved until browser/admin setup: " + ", ".join(sorted(unresolved)))


def unresolved_bindings_in_generated_specs() -> set[str]:
    unresolved: set[str] = set()
    for relative in PORTABLE_SPECS:
        path = generated_spec_path(relative)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        unresolved.update(TOKEN_PATTERN.findall(text))
    return unresolved


def provision_status(config_path: Path, scenario: str) -> None:
    print_header("Provision status")
    config = load_config(config_path)
    doctor(config_path, offline=True, platform="all")

    state_exists = STATE_PATH.exists()
    state: dict[str, Any] = load_json(STATE_PATH) if state_exists else {"box": {"folders": {}, "files": {}, "metadataTemplates": {}, "metadataSeeds": {}}}
    box_state = state.get("box", {})
    folders = box_state.get("folders", {})
    files = box_state.get("files", {})
    templates = box_state.get("metadataTemplates", {})
    seeds = box_state.get("metadataSeeds", {})

    required_folders = ["workspace", *FOLDERS]
    required_files = [Path(path).name for paths in UPLOADS.values() for path in paths]
    required_templates = [item["templateKey"] for item in bcl.load_bcl(ROOT / "config/box/metadata-templates.bcl")["templates"]]

    missing_folders = [name for name in required_folders if not folders.get(name)]
    missing_files = [filename for filename in required_files if not files.get(filename)]
    missing_templates = [item for item in required_templates if not templates.get(item)]

    missing_specs = [str(generated_spec_path(relative).relative_to(ROOT)) for relative in PORTABLE_SPECS if not generated_spec_path(relative).exists()]
    unresolved = unresolved_bindings_in_generated_specs()

    print(f"{STATUS_ICONS['success'] if state_exists else STATUS_ICONS['warn']} Bootstrap state file: {'present' if state_exists else 'missing'}")
    folder_ok = not missing_folders
    file_ok = not missing_files
    template_ok = not missing_templates
    seeds_ok = len(seeds) >= 16
    specs_ok = not missing_specs
    unresolved_ok = not unresolved
    print(f"{STATUS_ICONS['success'] if folder_ok else STATUS_ICONS['warn']} Box folders complete: {len(folders)}/{len(required_folders)}")
    print(f"{STATUS_ICONS['success'] if file_ok else STATUS_ICONS['warn']} Box files complete: {len(files)}/{len(required_files)}")
    print(f"{STATUS_ICONS['success'] if template_ok else STATUS_ICONS['warn']} Metadata templates complete: {len(templates)}/{len(required_templates)}")
    print(f"{STATUS_ICONS['success'] if seeds_ok else STATUS_ICONS['warn']} Metadata seeds complete: {len(seeds)} / 16")
    print(f"{STATUS_ICONS['success'] if specs_ok else STATUS_ICONS['warn']} Resolved runtime specs present: {len(PORTABLE_SPECS)}/{len(PORTABLE_SPECS)}")
    print(f"{STATUS_ICONS['success'] if unresolved_ok else STATUS_ICONS['warn']} Runtime unresolved tokens: {'none' if unresolved_ok else ', '.join(sorted(unresolved))}")

    if missing_folders or missing_files or missing_templates or missing_specs:
        print("Missing automation scope:")
        if missing_folders:
            print("  folders: " + ", ".join(missing_folders))
        if missing_files:
            print("  files: " + ", ".join(missing_files))
        if missing_templates:
            print("  metadata templates: " + ", ".join(missing_templates))
        if missing_specs:
            print("  generated specs: " + ", ".join(missing_specs))

    required_manual = ["box.appUrl", "box.formUrl", "box.hubUrl", "box.workflowUrl"]
    missing_manual = [
        key for key in required_manual
        if not config.get("box", {}).get(key.split(".")[1])
    ]
    if unresolved:
        print("Browser-only and environment-integration bindings still unresolved; complete operator browser/admin steps:")
        for token in sorted(unresolved):
            print(f"  - {token}")
    if missing_manual:
        print("Manual integration fields still missing in runtime config:")
        for key in missing_manual:
            print(f"  - {key}")

    if not missing_manual and not unresolved:
        try:
            validate(config_path, scenario=scenario, offline=True)
            _status(STATUS_ICONS["success"], "Automated/manual config appears aligned with scenario requirements.")
        except OperatorError as error:
            print(f"{STATUS_ICONS['warn']} Validate status: {error}")
    else:
        print(f"{STATUS_ICONS['warn']} Run finalize steps (resolve-config allow-unresolved and manual setup) before running validate.")


def provision(
    config_path: Path,
    *,
    scenario: str,
    dry_run: bool,
    allow_unresolved: bool,
    skip_validate: bool,
    confirm: bool,
    interactive: bool = False,
) -> None:
    print_header("Bootstrap")
    doctor(config_path, offline=dry_run, platform="all")
    if dry_run:
        _status(STATUS_ICONS["running"], "Dry-run mode enabled; no external writes will execute.")
        print("Use --yes/--confirm to run the same workflow for real.")
    elif not confirm:
        raise OperatorError("Provisioning performs external writes. Add --yes (or --confirm) to run mutations, or --dry-run to inspect the plan.")

    phases = (
        ("Generate local artifacts", lambda: generate_assets(dry_run)),
        ("Create Box foundation", lambda: box_foundation(config_path, dry_run=dry_run)),
        ("Seed representative metadata", lambda: seed_metadata(config_path, dry_run=dry_run)),
        ("Deploy Salesforce components", lambda: salesforce_deploy(config_path, dry_run=dry_run)),
        ("Resolve generated specs", lambda: resolve_config(config_path, allow_unresolved=True)),
    )
    for index, (name, action) in enumerate(phases, start=1):
        if interactive and not dry_run and not confirm:
            if not ask_confirmation(f"Run phase {index}/{len(phases)}: {name}"):
                _status(STATUS_ICONS["skip"], f"{index}/{len(phases)} {name}: skipped by operator")
                continue
        run_phase(name, index, len(phases), action)

    unresolved = unresolved_bindings_in_generated_specs()
    if unresolved and not allow_unresolved:
        message = ", ".join(sorted(unresolved))
        if dry_run:
            print(f"{STATUS_ICONS['warn']} Resolution preview still has unresolved tokens: {message}")
        else:
            print(f"{STATUS_ICONS['warn']} Resolution requires manual steps (unresolved tokens): {message}")

    if not dry_run and not skip_validate:
        try:
            validate(config_path, scenario=scenario, offline=False)
            _status(STATUS_ICONS["success"], "Validation passed for automated and configured assets.")
        except OperatorError as error:
            print(f"{STATUS_ICONS['warn']} Automated provision complete; finalize check not fully passed because: {error}")

    _status(STATUS_ICONS["success"], "Provision attempt finished.")
    if not dry_run:
        print("Run: python3 scripts/demo_operator.py status --scenario <scenario> for a full readiness summary.")
    else:
        print("Run again with --yes (or --confirm) to apply the remaining items.")


def salesforce_deploy(config_path: Path, *, dry_run: bool) -> None:
    config = load_config(config_path)
    doctor(config_path, offline=dry_run, platform="salesforce")
    alias = config["salesforce"].get("orgAlias")
    if not alias:
        raise OperatorError("salesforce.orgAlias is required.")
    expected_org_id = config["salesforce"].get("orgId")
    if not expected_org_id:
        raise OperatorError("salesforce.orgId is required as an explicit deployment guard.")
    project = ROOT / "los-salesforce-project"
    if dry_run:
        run(["sf", "org", "display", "--target-org", alias, "--json"], cwd=project, dry_run=True)
    else:
        actual_org = salesforce_identity(alias)
        if str(actual_org.get("id") or "") != str(expected_org_id):
            raise OperatorError(f"Refusing deployment: authenticated Salesforce org {actual_org.get('id') or 'unknown'} does not match configured {expected_org_id}.")
    experience_settings_sources = [
        "force-app/main/default/settings/Communities.settings-meta.xml",
        "force-app/main/default/settings/ExperienceBundle.settings-meta.xml",
    ]
    core_sources = [
        "force-app/main/default/classes",
        "force-app/main/default/staticresources",
        "force-app/main/default/objects/LOS_Loan__c",
        "force-app/main/default/objects/LOS_Box_Config__c",
        "force-app/main/default/namedCredentials",
        "force-app/main/default/externalCredentials",
        "force-app/main/default/cspTrustedSites",
        "force-app/main/default/customPermissions",
        "force-app/main/default/layouts/LOS_Loan__c-LOS Loan Layout.layout-meta.xml",
        "force-app/main/default/flexipages/LOS_Loan_Record_Page.flexipage-meta.xml",
        "force-app/main/default/applications/LOS_Demo.app-meta.xml",
        "force-app/main/default/permissionsets/LOS_Box_Automate_Integration.permissionset-meta.xml",
        "force-app/main/default/permissionsets/LOS_Demo_Operator.permissionset-meta.xml",
        "force-app/main/default/tabs/LOS_Loan__c.tab-meta.xml",
    ]
    experience_site_sources = [
        "force-app/main/default/sites/LOS_Experience.site-meta.xml",
        "force-app/main/default/networks/LOS Experience.network-meta.xml",
        "force-app/main/default/digitalExperienceConfigs/LOS_Experience1.digitalExperienceConfig-meta.xml",
        "force-app/main/default/digitalExperiences/site/LOS_Experience1",
    ]
    for name, sources in [
        ("Digital Experiences settings", experience_settings_sources),
        ("Salesforce core metadata", core_sources),
    ]:
        command = ["sf", "project", "deploy", "start", "--target-org", alias, "--wait", "20"]
        for source in sources:
            command.extend(["--source-dir", source])
        run(command, cwd=project, dry_run=dry_run)
    uibundle_deployed = deploy_uibundle(project, alias=alias, dry_run=dry_run)
    experience_command = ["sf", "project", "deploy", "start", "--target-org", alias, "--wait", "20"]
    for source in experience_site_sources:
        experience_command.extend(["--source-dir", source])
    run(experience_command, cwd=project, dry_run=dry_run)
    assign_salesforce_admin_permission_sets(project, alias=alias, dry_run=dry_run)
    if dry_run:
        action = "Salesforce deployment plan validated"
    else:
        uibundle_status = "UI Bundle, and " if uibundle_deployed else ""
        action = f"Salesforce data model, permissions, app, record page, Box tab, {uibundle_status}authenticated Experience Cloud site deployed"
    print(f"{action}.")


def validate_urls(config: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    hostname = config.get("box", {}).get("hostname", "")
    for key in ["appUrl", "formUrl", "hubUrl", "workflowUrl"]:
        value = config.get("box", {}).get(key)
        if value and urlparse(value).hostname != hostname:
            problems.append(f"box.{key} hostname does not match box.hostname")
    salesforce_url = config.get("salesforce", {}).get("myDomainUrl")
    if salesforce_url and urlparse(salesforce_url).scheme != "https":
        problems.append("salesforce.myDomainUrl must be an https URL")
    return problems


def validate(config_path: Path, *, scenario: str, offline: bool = False) -> None:
    config = load_config(config_path)
    required = {
        "box.hostname": config.get("box", {}).get("hostname"),
        "box.appUrl": config.get("box", {}).get("appUrl"),
        "box.formUrl": config.get("box", {}).get("formUrl"),
        "box.hubUrl": config.get("box", {}).get("hubUrl"),
        "box.workflowUrl": config.get("box", {}).get("workflowUrl"),
        "box.enterpriseId": config.get("box", {}).get("enterpriseId"),
        "box.operatorLogin": config.get("box", {}).get("operatorLogin"),
        "box.reviewerLogins": config.get("box", {}).get("reviewerLogins"),
        "salesforce.orgAlias": config.get("salesforce", {}).get("orgAlias"),
        "salesforce.orgId": config.get("salesforce", {}).get("orgId"),
        "salesforce.myDomainUrl": config.get("salesforce", {}).get("myDomainUrl"),
        "salesforce.integrationUsername": config.get("salesforce", {}).get("integrationUsername"),
        "salesforce.integrationEmail": config.get("salesforce", {}).get("integrationEmail"),
    }
    if scenario == "box-salesforce-los":
        required.update({
            "agentforce.agentId": config.get("agentforce", {}).get("agentId"),
            "agentforce.applicationId": config.get("agentforce", {}).get("applicationId"),
        })
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise OperatorError("Environment is not presentation-ready; missing: " + ", ".join(missing))
    url_problems = validate_urls(config)
    if url_problems:
        raise OperatorError("Environment URL validation failed:\n- " + "\n- ".join(url_problems))
    if not STATE_PATH.exists():
        raise OperatorError("Box bootstrap state is missing. Run box-foundation first.")
    state = load_json(STATE_PATH)
    box_state = state.get("box", {})
    required_folders = ["workspace", *FOLDERS]
    missing_folders = [key for key in required_folders if not box_state.get("folders", {}).get(key)]
    missing_files = [filename for paths in UPLOADS.values() for filename in [Path(path).name for path in paths] if not box_state.get("files", {}).get(filename)]
    missing_templates = [item["templateKey"] for item in bcl.load_bcl(ROOT / "config/box/metadata-templates.bcl")["templates"] if not box_state.get("metadataTemplates", {}).get(item["templateKey"])]
    if missing_folders or missing_files or missing_templates:
        raise OperatorError(f"Bootstrap state is incomplete: folders={missing_folders}, files={missing_files}, templates={missing_templates}")
    if len(box_state.get("metadataSeeds", {})) < 16:
        raise OperatorError("Deterministic metadata seed is incomplete. Run seed-metadata.")
    missing_generated = []
    unresolved_generated: set[str] = set()
    for relative in PORTABLE_SPECS:
        path = generated_spec_path(relative)
        if not path.exists():
            missing_generated.append(str(path.relative_to(ROOT)))
            continue
        unresolved_generated.update(TOKEN_PATTERN.findall(path.read_text(encoding="utf-8")))
    if missing_generated:
        raise OperatorError("Resolved runtime specs are missing: " + ", ".join(missing_generated))
    if unresolved_generated:
        raise OperatorError("Resolved runtime specs still contain bindings: " + ", ".join(sorted(unresolved_generated)))
    if not offline:
        doctor(config_path, offline=False, platform="all")
        for folder_id in box_state["folders"].values():
            run_json(["box", "folders:get", str(folder_id), "--json"])
        for file_id in box_state["files"].values():
            run_json(["box", "files:get", str(file_id), "--json"])
        for template_key in box_state["metadataTemplates"]:
            run_json(["box", "metadata-templates:get", template_key, "--scope", "enterprise", "--json"])
        sf_result = run_json([
            "sf", "data", "query", "--target-org", config["salesforce"]["orgAlias"], "--json",
            "--query", "SELECT QualifiedApiName FROM EntityDefinition WHERE QualifiedApiName='LOS_Loan__c'",
        ], cwd=ROOT / "los-salesforce-project")
        records = sf_result.get("result", {}).get("records", [])
        if not records:
            raise OperatorError("Salesforce LOS_Loan__c is not present in the configured org.")
    scope = "local bindings" if offline else "live Box resources, Salesforce data model, and local bindings"
    print(f"{scenario.title()} readiness validation passed for {scope}. Run the storyboard preflight before presenting.")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Examples:\n"
            f"  {CLI_COMMAND_NAME} bootstrap --scenario box-salesforce-los --dry-run\n"
            f"  {CLI_COMMAND_NAME} bootstrap --scenario box-salesforce-los --yes\n"
            f"  {CLI_COMMAND_NAME} status --scenario box-salesforce-los\n"
            f"  {CLI_COMMAND_NAME} validate --scenario box-salesforce-los --offline"
        ),
    )
    result.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = result.add_subparsers(dest="command", required=True)

    doctor_parser = sub.add_parser("doctor", help="Check CLI/tooling prerequisites before changing anything.")
    doctor_parser.add_argument("--offline", action="store_true", help="Skip Box/Salesforce API checks.")
    doctor_parser.add_argument("--platform", choices=["all", "box", "salesforce"], default="all")

    for name in ["generate-assets", "box-foundation", "seed-metadata", "salesforce-deploy"]:
        command = sub.add_parser(name, help=f"Run the {name} task only.")
        command.add_argument("--dry-run", action="store_true")

    resolve_parser = sub.add_parser("resolve-config", help="Render portable specs from template + runtime state.")
    resolve_parser.add_argument("--allow-unresolved", action="store_true", help="Allow unresolved runtime placeholders.")

    status_parser = sub.add_parser("status", help="Show completeness and what remains.")
    status_parser.add_argument("--scenario", choices=SCENARIOS, default=SCENARIOS[0])

    bootstrap_parser = sub.add_parser("bootstrap", help="Run the full non-destructive workflow end-to-end.")
    bootstrap_parser.add_argument("--scenario", choices=SCENARIOS, default=SCENARIOS[0])
    bootstrap_parser.add_argument("--dry-run", action="store_true", help="Plan without creating anything.")
    bootstrap_parser.add_argument("--allow-unresolved", action="store_true", help="Allow unresolved placeholders during spec rendering.")
    bootstrap_parser.add_argument("--skip-validate", action="store_true", help="Skip full post-bootstrap validation.")
    bootstrap_parser.add_argument("--yes", "--confirm", dest="confirm", action="store_true", help="Apply and confirm writes.")
    bootstrap_parser.add_argument("--interactive", action="store_true", help="Prompt before each phase.")

    provision_parser = sub.add_parser("provision", help="Legacy alias for bootstrap.")
    provision_parser.add_argument("--scenario", choices=SCENARIOS, default=SCENARIOS[0])
    provision_parser.add_argument("--dry-run", action="store_true")
    provision_parser.add_argument("--allow-unresolved", action="store_true")
    provision_parser.add_argument("--skip-validate", action="store_true")
    provision_parser.add_argument("--yes", "--confirm", dest="confirm", action="store_true", help="Apply writes to Box and Salesforce.")
    provision_parser.add_argument("--interactive", action="store_true", help="Prompt before each phase.")

    validate_parser = sub.add_parser("validate", help="Validate readiness and readiness gates.")
    validate_parser.add_argument("--scenario", choices=SCENARIOS, default=SCENARIOS[0])
    validate_parser.add_argument("--offline", action="store_true", help="Validate local bindings without live calls.")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "doctor":
            doctor(args.config, offline=args.offline, platform=args.platform)
        elif args.command == "generate-assets":
            generate_assets(args.dry_run)
        elif args.command == "box-foundation":
            box_foundation(args.config, dry_run=args.dry_run)
        elif args.command == "seed-metadata":
            seed_metadata(args.config, dry_run=args.dry_run)
        elif args.command == "salesforce-deploy":
            salesforce_deploy(args.config, dry_run=args.dry_run)
        elif args.command == "resolve-config":
            resolve_config(args.config, allow_unresolved=args.allow_unresolved)
        elif args.command == "status":
            if not args.config.exists():
                raise OperatorError("Demo configuration missing. Run setup_los_dev.py first.")
            provision_status(args.config, scenario=args.scenario)
        elif args.command == "provision":
            if not args.config.exists():
                raise OperatorError("Demo configuration missing. Run setup_los_dev.py first.")
            provision(
                args.config,
                scenario=args.scenario,
                dry_run=args.dry_run,
                allow_unresolved=args.allow_unresolved,
                skip_validate=args.skip_validate,
                confirm=args.confirm,
                interactive=args.interactive,
            )
        elif args.command == "bootstrap":
            if not args.config.exists():
                raise OperatorError("Demo configuration missing. Run setup_los_dev.py first.")
            provision(
                args.config,
                scenario=args.scenario,
                dry_run=args.dry_run,
                allow_unresolved=args.allow_unresolved,
                skip_validate=args.skip_validate,
                confirm=args.confirm,
                interactive=args.interactive,
            )
        elif args.command == "validate":
            validate(args.config, scenario=args.scenario, offline=args.offline)
    except (OperatorError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
