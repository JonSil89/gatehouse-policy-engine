#!/usr/bin/env python3
"""
Gatehouse Policy Engine - Enterprise edition
ISO 27001-aligned infrastructure change validation.
No external dependencies beyond pyyaml.
"""

import re
import sys
import json
import yaml
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# ========================
# CONFIG LOAD
# ========================

CONFIG_FILE = "validation/config.yaml"

default_config = {
    "min_approvers": {1: 1, 2: 2, 3: 3},
    "required_sections": ["Perustiedot", "Kuvaus", "Vaikutusanalyysi"],
    "required_fields": [
        r"\*\*Muutoksen nimi:\*\*",
        r"\*\*Pyytäjä:\*\*",
        r"\*\*Päivämäärä:\*\*",
        r"\*\*Riskiluokka:\*\*",
        r"\*\*Kohdeympäristö:\*\*",
        r"\*\*Riskiperustelu:\*\*",
    ],
    "allowed_environments": ["dev", "test", "staging", "prod"],
    "sensitive_path_patterns": [
        r"/etc/",
        r"/var/",
        r"/root/",
        r"[A-Za-z]:\\"
    ],
    "iso_control_map": {
        "rollback": "A.12.1.2",
        "test_plan": "A.14.2.2",
        "logging": "A.12.4.1",
        "approval": "A.12.1.2",
        "risk_assessment": "A.6.1.2",
    }
}

if Path(CONFIG_FILE).exists():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        logging.info("Config loaded from YAML")
else:
    config = default_config
    logging.info("Using default config")

# ========================
# VALIDATION RESULT CLASS
# ========================

class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
        self.triggered_controls = set()
        self.original_risk_class = None
        self.final_risk_class = None
        self.risk_escalated = False

    def error(self, msg):
        self.errors.append(msg)
        print(f"Error:  {msg}", file=sys.stderr)

    def warning(self, msg):
        self.warnings.append(msg)
        print(f"Warning: {msg}", file=sys.stderr)

    def info_msg(self, msg):
        self.info.append(msg)

    def trigger_control(self, key):
        label = config.get("iso_control_map", {}).get(key, key)
        self.triggered_controls.add(label)

    @property
    def passed(self):
        return len(self.errors) == 0

# ========================
# VALIDATORS
# ========================

def extract_risk_class(content, result):
    m = re.search(r"\*\*Riskiluokka:\*\*\s+([123])", content)
    if not m:
        result.error("Riskiluokka puuttuu tai on virheellinen.")
        return 1
    return int(m.group(1))


def validate_sections(content, result):
    for section in config["required_sections"]:
        if not re.search(rf"##\s+{section}", content):
            result.error(f"Puuttuva osio: {section}")


def validate_fields(content, result):
    for pattern in config["required_fields"]:
        if not re.search(pattern, content):
            result.error(f"Puuttuva kenttä: {pattern}")


def validate_environment(content, result):
    m = re.search(r"\*\*Kohdeympäristö:\*\*\s+(\S+)", content)
    if not m:
        result.warning("Kohdeympäristö ei tunnistettu.")
        return None
    env = m.group(1).lower()
    if env not in config["allowed_environments"]:
        result.warning(f"Tuntematon ympäristö: {env}")
    return env


def escalate_risk_if_needed(env, rc, result):
    if env == "prod" and rc < 3:
        result.info_msg(f"Riskiluokka korotettu {rc} → 3 (tuotantoympäristö)")
        result.risk_escalated = True
        return 3
    result.risk_escalated = False
    return rc


def validate_approvers(content, rc, result):
    # Hakee Hyväksyjä 1, Hyväksyjä 2 jne — ei pelkkää Hyväksyjä
    approvers = re.findall(r"\*\*Hyväksyjä\s+\d+:\*\*", content)
    required = config["min_approvers"].get(rc, 1)
    if len(approvers) < required:
        result.error(f"Riskiluokka {rc} vaatii vähintään {required} hyväksyjää")
    result.trigger_control("approval")


def validate_rollback(content, rc, result):
    # Hyväksyy sekä "Palautussuunnitelma" että "Rollback"
    has_rollback = "Palautussuunnitelma" in content or "Rollback" in content
    if rc >= 2 and not has_rollback:
        result.error("Palautussuunnitelma puuttuu (lisää 'Palautussuunnitelma' tai 'Rollback')")
    result.trigger_control("rollback")


def validate_test_plan(content, rc, result):
    has_test = "Testaussuunnitelma" in content or "Testaus" in content
    if rc >= 2 and not has_test:
        result.warning("Testaussuunnitelma puuttuu")
    result.trigger_control("test_plan")


def validate_paths(content, result):
    for pattern in config["sensitive_path_patterns"]:
        if re.search(pattern, content):
            result.warning(f"Mahdollinen sensitiivinen polku havaittu: {pattern}")

# ========================
# SCORING & HASHING
# ========================

def calculate_score(result):
    score = 100 - (len(result.errors) * 20) - (len(result.warnings) * 5)
    return max(score, 0)


def calculate_file_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

# ========================
# REPORT GENERATION
# ========================

def generate_audit_report(result, file_path, timestamp):
    Path("evidence/compliance-reports").mkdir(parents=True, exist_ok=True)
    file_hash = calculate_file_hash(file_path)
    status_str = "PASSED" if result.passed else "FAILED"
    base_path = Path("evidence/compliance-reports") / f"report-{status_str}-{file_hash[:12]}"

    score = calculate_score(result)
    json_data = {
        "passed": result.passed,
        "original_risk_class": result.original_risk_class,
        "final_risk_class": result.final_risk_class,
        "risk_escalated": result.risk_escalated,
        "compliance_score": score,
        "errors": result.errors,
        "warnings": result.warnings,
        "timestamp": timestamp,
        "file": file_path,
        "file_hash": file_hash,
        "iso_controls_triggered": sorted(list(result.triggered_controls)),
    }

    with open(f"{base_path}.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    status_icon = "✅ PASSED" if result.passed else "❌ FAILED"
    with open(f"{base_path}.md", "w", encoding="utf-8") as f:
        f.write("# 🏛️ Gatehouse Audit Report\n\n")
        f.write(f"**Status:** {status_icon}  \n")
        f.write(f"**File:** `{file_path}`  \n")
        f.write(f"**Risk class:** {result.final_risk_class}  \n")
        f.write(f"**Compliance score:** {score}  \n")
        f.write(f"**Timestamp:** {timestamp}  \n")
        f.write(f"**File hash:** `{file_hash}`\n\n")
        f.write("| Check | Count |\n")
        f.write("| :--- | :--- |\n")
        f.write(f"| Errors | {len(result.errors)} |\n")
        f.write(f"| Warnings | {len(result.warnings)} |\n")
        f.write(f"| ISO controls triggered | {len(result.triggered_controls)} |\n")
        if result.errors:
            f.write("\n### ❌ Errors\n")
            for err in result.errors:
                f.write(f"- {err}\n")
        if result.warnings:
            f.write("\n### ⚠️ Warnings\n")
            for w in result.warnings:
                f.write(f"- {w}\n")

    return str(base_path)

# ========================
# MAIN
# ========================

def main():
    if len(sys.argv) < 2:
        print("Usage: validate-change-request.py <file.md>")
        sys.exit(2)

    file_path = sys.argv[1]
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = ValidationResult()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logging.error(f"File error: {e}")
        sys.exit(2)

    validate_sections(content, result)
    validate_fields(content, result)
    rc = extract_risk_class(content, result)
    result.original_risk_class = rc
    env = validate_environment(content, result)
    if env:
        rc = escalate_risk_if_needed(env, rc, result)
    result.final_risk_class = rc
    result.trigger_control("risk_assessment")

    validate_rollback(content, rc, result)
    validate_approvers(content, rc, result)
    validate_test_plan(content, rc, result)
    validate_paths(content, result)

    generate_audit_report(result, file_path, timestamp)

    ci_output = {
        "passed": result.passed,
        "original_risk_class": result.original_risk_class,
        "final_risk_class": result.final_risk_class,
        "risk_escalated": result.risk_escalated,
        "compliance_score": calculate_score(result),
        "errors": result.errors,
        "warnings": result.warnings,
        "timestamp": timestamp,
        "file": file_path,
    }
    print(json.dumps(ci_output, indent=2, ensure_ascii=False))
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
