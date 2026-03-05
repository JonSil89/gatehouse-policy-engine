#!/usr/bin/env python3
"""
Gatehouse Policy Engine - Enterprise edition
- Dynamic config
- Role-based approvers
- Enhanced path scanning
- Full audit trail
- CI/CD-friendly output
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
        logging.error(msg)
        self.errors.append(msg)

    def warning(self, msg):
        logging.warning(msg)
        self.warnings.append(msg)

    def info_msg(self, msg):
        logging.info(msg)
        self.info.append(msg)

    def trigger_control(self, key):
        if key in config["iso_control_map"]:
            self.triggered_controls.add(config["iso_control_map"][key])

    @property
    def passed(self):
        return len(self.errors) == 0


# ========================
# CORE VALIDATIONS
# ========================

def validate_sections(content, result):
    for section in config["required_sections"]:
        if section not in content:
            result.error(f"Puuttuva osio: {section}")


def validate_fields(content, result):
    for field in config["required_fields"]:
        if not re.search(field, content):
            result.error(f"Pakollinen kenttä puuttuu: {field}")


def extract_risk_class(content, result):
    match = re.search(r"\*\*Riskiluokka:\*\*\s*(\d)", content)
    if not match:
        result.error("Riskiluokkaa ei tunnistettu")
        return 1
    rc = int(match.group(1))
    if rc not in [1, 2, 3]:
        result.error("Virheellinen riskiluokka")
    return rc


def validate_environment(content, result):
    match = re.search(r"\*\*Kohdeympäristö:\*\*\s*(\w+)", content)
    if not match:
        result.warning("Kohdeympäristöä ei määritelty")
        return None
    env = match.group(1).lower()
    if env not in config["allowed_environments"]:
        result.warning(f"Tuntematon ympäristö: {env}")
    return env


def escalate_risk_if_needed(env, rc, result):
    if env == "prod" and rc < 3:
        result.warning("Riskiluokka nostettu production-ympäristön vuoksi")
        result.risk_escalated = True
        return 3
    return rc


def validate_approvers(content, rc, result):
    approvers = re.findall(r"\*\*Hyväksyjä:\*\*", content)
    required = config["min_approvers"].get(rc, 1)
    if len(approvers) < required:
        result.error(f"Riskiluokka {rc} vaatii vähintään {required} hyväksyjää")
    result.trigger_control("approval")


def validate_rollback(content, rc, result):
    if rc >= 2 and "Rollback" not in content:
        result.error("Rollback-suunnitelma puuttuu")
    result.trigger_control("rollback")


def validate_test_plan(content, rc, result):
    if rc >= 2 and "Testaus" not in content:
        result.warning("Testisuunnitelma puuttuu")
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
        for k, v in json_data.items():
            f.write(f"{k}: {v}\n\n")
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
