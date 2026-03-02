#!/usr/bin/env python3

import re
import sys
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path


# ========================
# POLICY CONFIGURATION
# ========================

MIN_APPROVERS = {1: 1, 2: 2, 3: 3}

REQUIRED_SECTIONS = [
    "Perustiedot",
    "Kuvaus",
    "Vaikutusanalyysi"
]

REQUIRED_FIELDS = [
    r"\*\*Muutoksen nimi:\*\*",
    r"\*\*Pyytäjä:\*\*",
    r"\*\*Päivämäärä:\*\*",
    r"\*\*Riskiluokka:\*\*",
    r"\*\*Kohdeympäristö:\*\*",
    r"\*\*Riskiperustelu:\*\*",
]

ALLOWED_ENVIRONMENTS = ["dev", "test", "staging", "prod"]

SENSITIVE_PATH_PATTERNS = [
    r"/etc/",
    r"/var/",
    r"/root/",
    r"[A-Za-z]:\\",  # Windows drive letter
]

ISO_CONTROL_MAP = {
    "rollback": "A.12.1.2",
    "test_plan": "A.14.2.2",
    "logging": "A.12.4.1",
    "approval": "A.12.1.2",
    "risk_assessment": "A.6.1.2",
}


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

    def warning(self, msg):
        self.warnings.append(msg)

    def info_msg(self, msg):
        self.info.append(msg)

    def trigger_control(self, key):
        if key in ISO_CONTROL_MAP:
            self.triggered_controls.add(ISO_CONTROL_MAP[key])

    @property
    def passed(self):
        return len(self.errors) == 0


# ========================
# CORE VALIDATION
# ========================

def extract_risk_class(content, result):
    m = re.search(r"\*\*Riskiluokka:\*\*\s+([123])", content)
    if not m:
        result.error("Riskiluokka puuttuu tai on virheellinen.")
        return 3
    return int(m.group(1))


def validate_environment(content, result):
    m = re.search(r"\*\*Kohdeympäristö:\*\*\s+(.*)", content)
    if not m:
        result.error("Kohdeympäristö puuttuu.")
        return None

    env = m.group(1).strip().lower()

    if env not in ALLOWED_ENVIRONMENTS:
        result.error(f"Virheellinen ympäristö: {env}")
        return None

    return env


def escalate_risk_if_needed(env, rc, result):
    if env == "prod" and rc < 2:
        result.warning("Production-ympäristö → riskiluokka nostettu min 2")
        result.risk_escalated = True
        return 2
    return rc


def validate_sections(content, result):
    for section in REQUIRED_SECTIONS:
        if not re.search(rf"##\s+{section}", content):
            result.error(f"Puuttuva osio: {section}")


def validate_fields(content, result):
    for pattern in REQUIRED_FIELDS:
        if not re.search(pattern, content):
            result.error(f"Puuttuva kenttä: {pattern}")


def validate_approvers(content, rc, result):
    approvers = re.findall(r"\*\*Hyväksyjä\s+\d+:\*\*", content)
    if len(approvers) < MIN_APPROVERS.get(rc, 1):
        result.error(f"Hyväksyjiä liian vähän riskiluokalle {rc}")
    else:
        result.trigger_control("approval")


def validate_rollback(content, rc, result):
    if rc >= 2:
        if "Palautussuunnitelma" not in content:
            result.error("Palautussuunnitelma pakollinen riskiluokalle 2-3")
        else:
            result.trigger_control("rollback")


def validate_test_plan(content, rc, result):
    if rc >= 2:
        if "Testaussuunnitelma" not in content:
            result.error("Testaussuunnitelma pakollinen riskiluokalle 2-3")
        else:
            result.trigger_control("test_plan")


def validate_paths(content, result):
    for pattern in SENSITIVE_PATH_PATTERNS:
        if re.search(pattern, content):
            result.warning(f"Mahdollinen sensitiivinen polku havaittu: {pattern}")


# ========================
# SCORING
# ========================

def calculate_score(result):
    score = 100 - (len(result.errors) * 20) - (len(result.warnings) * 5)
    return max(score, 0)


# ========================
# HASHING
# ========================

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
    report_name = f"report-{file_hash[:16]}"
    base_path = Path("evidence/compliance-reports") / report_name

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
        "iso_controls_triggered": list(result.triggered_controls),
    }

    with open(f"{base_path}.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    with open(f"{base_path}.md", "w", encoding="utf-8") as f:
        f.write("# Gatehouse Audit Report\n\n")
        f.write(f"File: {file_path}\n\n")
        f.write(f"File hash (SHA256): {file_hash}\n\n")
        f.write(f"Original risk class: {result.original_risk_class}\n\n")
        f.write(f"Final risk class: {result.final_risk_class}\n\n")
        f.write(f"Risk escalated: {result.risk_escalated}\n\n")
        f.write(f"Compliance score: {score}\n\n")
        f.write(f"Passed: {result.passed}\n\n")

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
        print(f"File error: {e}")
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
