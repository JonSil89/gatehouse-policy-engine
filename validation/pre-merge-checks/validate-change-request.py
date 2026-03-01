#!/usr/bin/env python3

import re
import sys
import os
import json
from datetime import datetime, timezone
from pathlib import Path


MIN_APPROVERS = {1: 1, 2: 2, 3: 3}


class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

    def error(self, msg):
        self.errors.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)

    def info_msg(self, msg):
        self.info.append(msg)

    @property
    def passed(self):
        return len(self.errors) == 0


def extract_risk_class(content, result):
    m = re.search(r"\*\*Riskiluokka:\*\*\s+([123])", content)
    if not m:
        result.error("Riskiluokka puuttuu tai on virheellinen.")
        return 1
    return int(m.group(1))


def validate_sections(content, result):
    required = ["Perustiedot", "Kuvaus", "Vaikutusanalyysi"]
    for section in required:
        if not re.search(rf"##\s+{section}", content):
            result.error(f"Puuttuva osio: {section}")


def validate_fields(content, result):
    required_patterns = [
        r"\*\*Muutoksen nimi:\*\*",
        r"\*\*Pyytäjä:\*\*",
        r"\*\*Päivämäärä:\*\*",
        r"\*\*Riskiluokka:\*\*",
        r"\*\*Kohdeympäristö:\*\*",
    ]
    for pattern in required_patterns:
        if not re.search(pattern, content):
            result.error(f"Puuttuva kenttä: {pattern}")


def validate_approvers(content, rc, result):
    approvers = re.findall(r"\*\*Hyväksyjä\s+\d+:\*\*", content)
    if len(approvers) < MIN_APPROVERS.get(rc, 1):
        result.error(f"Hyväksyjiä liian vähän riskiluokalle {rc}")


def validate_rollback(content, rc, result):
    if rc >= 2:
        if "Palautussuunnitelma" not in content:
            result.error("Palautussuunnitelma pakollinen riskiluokalle 2-3")


def validate_test_plan(content, rc, result):
    if rc >= 2:
        if "Testaussuunnitelma" not in content:
            result.error("Testaussuunnitelma pakollinen riskiluokalle 2-3")


def validate_paths(content, result):
    if re.search(r"/[A-Za-z0-9_\-]+/", content):
        result.warning("Mahdollinen absoluuttinen polku havaittu.")


def generate_audit_report(result, rc, file_path, timestamp):

    Path("evidence/compliance-reports").mkdir(parents=True, exist_ok=True)

    base_name = Path("evidence/compliance-reports") / f"report-{int(datetime.now().timestamp())}"

    score = 100
    score -= min(len(result.errors) * 20, 80)
    score -= min(len(result.warnings) * 5, 20)
    score = max(score, 0)

    json_data = {
        "passed": result.passed,
        "risk_class": rc,
        "compliance_score": score,
        "errors": result.errors,
        "warnings": result.warnings,
        "timestamp": timestamp,
        "file": file_path,
        "iso_controls": ["A.12.1.2", "A.14.2.2", "A.12.4.1"],
    }

    with open(f"{base_name}.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    with open(f"{base_name}.md", "w", encoding="utf-8") as f:
        f.write("# Gatehouse Audit Report\n\n")
        f.write(f"**File:** {file_path}\n\n")
        f.write(f"**Risk class:** {rc}\n\n")
        f.write(f"**Compliance score:** {score}\n\n")
        f.write(f"**Passed:** {result.passed}\n\n")

    return str(base_name)


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
    validate_rollback(content, rc, result)
    validate_approvers(content, rc, result)
    validate_test_plan(content, rc, result)
    validate_paths(content, result)

    report_path = generate_audit_report(result, rc, file_path, timestamp)

    ci_output = {
        "passed": result.passed,
        "risk_class": rc,
        "compliance_score": 100 - (len(result.errors) * 20),
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
