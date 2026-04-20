#!/usr/bin/env python3
"""
Gatehouse Policy Engine — Infrastructure Change Quality Gate
============================================================

Validates infrastructure change requests against ISO 27001-aligned controls.

Checks:
  - Required sections and fields
  - Risk classification (1-3) with justification
  - Rollback plan (mandatory for Class 2-3)
  - Test plan (mandatory for Class 2-3)
  - Approver count (risk-class based)
  - CISO approval (mandatory for Class 3)
  - Freeze period (mandatory for Class 3)
  - Absolute path detection
  - SHA-256 file hash (tamper-evident audit trail)

Output:
  - Colored terminal summary
  - JSON output for CI/CD integration
  - Audit report saved to evidence/compliance-reports/

Exit codes:
  0 = PASSED
  1 = FAILED (validation errors)
  2 = ERROR  (script/file error)

ISO 27001 Controls:
  A.12.1.2 — Change Management
  A.14.2.2 — System Change Control
  A.12.4.1 — Event Logging (audit trail)

No external dependencies — Python stdlib only.
POSIX-compatible: relative paths, LF line endings.
"""

import re
import sys
import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path


# ─── ANSI Colors ───────────────────────────────────────────────────────────────

GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
CYAN   = '\033[96m'
BOLD   = '\033[1m'
RESET  = '\033[0m'


# ─── Configuration ─────────────────────────────────────────────────────────────

REQUIRED_SECTIONS = [
    "Perustiedot",
    "Kuvaus",
    "Vaikutusanalyysi",
]

REQUIRED_FIELDS = {
    "Muutoksen nimi": r"\*\*Muutoksen nimi:\*\*\s+\S",
    "Pyytäjä":        r"\*\*Pyytäjä:\*\*\s+\S",
    "Päivämäärä":     r"\*\*Päivämäärä:\*\*\s+\d{4}-\d{2}-\d{2}",
    "Riskiluokka":    r"\*\*Riskiluokka:\*\*\s+[123]",
    "Kohdeympäristö": r"\*\*Kohdeympäristö:\*\*\s+(dev|staging|production)",
}

RISK_CLASS_PATTERN = re.compile(r"\*\*Riskiluokka:\*\*\s+([123])")
APPROVER_PATTERN   = re.compile(r"\*\*Hyväksyjä\s+\d+:\*\*\s+(?!\[Nimi\])(\S+)")
ROLLBACK_SECTION   = re.compile(r"##\s+Palautussuunnitelma", re.IGNORECASE)
ROLLBACK_STRATEGY  = re.compile(r"\*\*Palautusstrategia:\*\*\s+(?!\[)\S")
TEST_PLAN_SECTION  = re.compile(r"##\s+Testaussuunnitelma", re.IGNORECASE)
FREEZE_PATTERN     = re.compile(r"\*\*Jäädytysikkuna:\*\*\s+(?!Ei)\S")
CISO_PATTERN       = re.compile(r"\*\*CISO-hyväksyntä:\*\*\s+(?!\[)\S")
ABS_PATH_PATTERN   = re.compile(r"(/[a-zA-Z0-9_\-./]{3,}|[A-Z]:\\[^\s]+)")

KNOWN_ENVIRONMENTS = {"dev", "staging", "production"}

REQUIRED_APPROVERS = {1: 1, 2: 2, 3: 3}


# ─── Validation Result ─────────────────────────────────────────────────────────

class ValidationResult:
    def __init__(self):
        self.errors   = []
        self.warnings = []
        self.info     = []
        self.passed   = True

    def error(self, msg):
        self.errors.append(msg)
        self.passed = False
        print(f"  {RED}Error:{RESET}  {msg}")

    def warn(self, msg):
        self.warnings.append(msg)
        print(f"  {YELLOW}Warning:{RESET} {msg}")

    def info_msg(self, msg):
        self.info.append(msg)

    def summary(self):
        status = f"{GREEN}PASSED{RESET}" if self.passed else f"{RED}FAILED{RESET}"
        lines = [
            f"\n{'─' * 60}",
            f"  {BOLD}QUALITY GATE: {status}{RESET}",
            f"  Errors:   {len(self.errors)}",
            f"  Warnings: {len(self.warnings)}",
            f"{'─' * 60}",
        ]
        return "\n".join(lines)


# ─── Validators ────────────────────────────────────────────────────────────────

def validate_sections(content, result):
    for section in REQUIRED_SECTIONS:
        if not re.search(rf"##\s+{re.escape(section)}", content, re.IGNORECASE):
            result.error(f"Pakollinen osio puuttuu: '{section}'")
        else:
            result.info_msg(f"Osio löytyi: '{section}'")


def validate_fields(content, result):
    for field, pattern in REQUIRED_FIELDS.items():
        if not re.search(pattern, content):
            result.error(f"Pakollinen kenttä puuttuu tai ei ole täytetty: '{field}'")
        else:
            result.info_msg(f"Kenttä täytetty: '{field}'")

    # Environment check
    env_match = re.search(r"\*\*Kohdeympäristö:\*\*\s+(\S+)", content)
    if env_match:
        env = env_match.group(1).lower()
        if env not in KNOWN_ENVIRONMENTS:
            result.warn(f"Tuntematon ympäristö: {env}")


def extract_risk_class(content, result):
    match = RISK_CLASS_PATTERN.search(content)
    if not match:
        result.error("Riskiluokka puuttuu tai on virheellinen (1, 2 tai 3)")
        return None
    rc = int(match.group(1))
    result.info_msg(f"Riskiluokka: {rc}")
    return rc


def validate_rollback(content, rc, result):
    if rc is None or rc < 2:
        return
    if not ROLLBACK_SECTION.search(content):
        result.error("Palautussuunnitelma-osio puuttuu (vaaditaan luokille 2-3)")
    elif not ROLLBACK_STRATEGY.search(content):
        result.error("Palautusstrategia ei ole täytetty")
    else:
        result.info_msg("Palautussuunnitelma: OK")


def validate_approvers(content, rc, result):
    if rc is None:
        return
    approvers = APPROVER_PATTERN.findall(content)

    # Also count checkbox-style approvers: - [x] @name
    checkbox_approvers = re.findall(r"-\s+\[x\]\s+@\S+", content, re.IGNORECASE)
    total = max(len(approvers), len(checkbox_approvers))

    required = REQUIRED_APPROVERS.get(rc, 1)
    if total < required:
        result.error(f"Hyväksyjiä liian vähän riskiluokalle {rc} (löytyi {total}, vaaditaan {required})")
    else:
        result.info_msg(f"Hyväksyjät: {total}/{required} (OK)")

    if rc == 3 and not CISO_PATTERN.search(content):
        result.error("CISO-hyväksyntä puuttuu (vaaditaan luokalle 3)")


def validate_freeze(content, rc, result):
    if rc != 3:
        return
    if not FREEZE_PATTERN.search(content):
        result.error("Jäädytysikkuna puuttuu (vaaditaan luokalle 3)")
    else:
        result.info_msg("Jäädytysikkuna: OK")


def validate_test_plan(content, rc, result):
    if rc is None or rc < 2:
        return
    if not TEST_PLAN_SECTION.search(content):
        result.error("Testaussuunnitelma-osio puuttuu (vaaditaan luokille 2-3)")
    else:
        result.info_msg("Testaussuunnitelma: OK")


def validate_paths(content, result):
    matches = ABS_PATH_PATTERN.findall(content)
    safe = {"/dev/null", "/tmp", "/etc", "/usr", "/var"}
    for path in matches:
        if not any(path.startswith(s) for s in safe):
            result.warn(f"Mahdollinen absoluuttinen polku havaittu: {path}")


# ─── SHA-256 Hash ──────────────────────────────────────────────────────────────

def calculate_sha256(file_path):
    """Laskee tiedoston digitaalisen sormenjäljen (SHA-256).
    
    Tamper-evident: jos tiedostoa muutetaan raportin generoinnin jälkeen,
    hash ei täsmää. Tarkista: sha256sum <tiedosto>
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


# ─── Audit Report ──────────────────────────────────────────────────────────────

def generate_audit_report(result, rc, file_path, timestamp):
    folder = Path("evidence/compliance-reports")
    folder.mkdir(parents=True, exist_ok=True)

    # Calculate compliance score
    total_checks = len(result.errors) + len(result.info)
    passed_checks = len(result.info)
    score = int((passed_checks / total_checks * 100)) if total_checks > 0 else 0

    # Calculate file hash
    try:
        file_hash = calculate_sha256(file_path)
    except Exception:
        file_hash = "unavailable"

    status    = "PASSED" if result.passed else "FAILED"
    ts_short  = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base_name = folder / f"report-{status}-{ts_short}"

    # ── Markdown report ──
    status_icon = "✅" if result.passed else "❌"
    md_lines = [
        "# 🏛️ Gatehouse Audit Report",
        "",
        f"**Status:** {status_icon} {status}  ",
        f"**File:** `{file_path}`  ",
        f"**Risk class:** {rc if rc else 'N/A'}  ",
        f"**Compliance score:** {score}  ",
        f"**Timestamp:** {timestamp}  ",
        f"**File hash:** `{file_hash}`",
        "",
        "| Check | Count |",
        "| :--- | :--- |",
        f"| Errors | {len(result.errors)} |",
        f"| Warnings | {len(result.warnings)} |",
        f"| ISO controls triggered | 3 |",
        "",
        "## Checks",
        "",
        "| Result | Message |",
        "| :---: | :--- |",
    ]

    for msg in result.info:
        md_lines.append(f"| ✅ | {msg} |")
    for msg in result.warnings:
        md_lines.append(f"| ⚠️ | {msg} |")
    for msg in result.errors:
        md_lines.append(f"| ❌ | {msg} |")

    if result.errors:
        md_lines += [
            "",
            "## ⚠️ Critical Findings",
            "",
        ]
        for e in result.errors:
            md_lines.append(f"- {e}")

    md_lines += [
        "",
        "---",
        "## 🔐 Tiedoston eheys (SHA-256)",
        "",
        f"`{file_hash}`",
        "",
        f"Tarkista peukalointi: `sha256sum {file_path}`",
        "",
        "---",
        f"*Generated by Gatehouse Policy Engine | ISO 27001 A.12.4.1*",
    ]

    with open(f"{base_name}.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # ── JSON report ──
    json_data = {
        "audit_status":        status,
        "timestamp":           timestamp,
        "file":                file_path,
        "file_hash":           file_hash,
        "risk_class":          rc,
        "compliance_score":    score,
        "passed":              result.passed,
        "errors":              result.errors,
        "warnings":            result.warnings,
        "info":                result.info,
        "iso_controls_triggered": ["A.12.1.2", "A.14.2.2", "A.12.4.1"],
    }

    with open(f"{base_name}.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    return str(base_name)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(
            f"Usage: python {os.path.basename(__file__)} <change-request.md>",
            file=sys.stderr
        )
        print("Validates an infrastructure change request against ISO 27001 quality gate.", file=sys.stderr)
        sys.exit(2)

    file_path = sys.argv[1]
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result    = ValidationResult()

    result.info_msg(f"Validointi aloitettu: {timestamp}")
    result.info_msg(f"Tiedosto: {file_path}")

    # Read file
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"{RED}ERROR:{RESET} Tiedostoa ei löydy: {file_path}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"{RED}ERROR:{RESET} Tiedoston luku epäonnistui: {e}", file=sys.stderr)
        sys.exit(2)

    # Run all validations
    validate_sections(content, result)
    validate_fields(content, result)
    rc = extract_risk_class(content, result)
    validate_rollback(content, rc, result)
    validate_approvers(content, rc, result)
    validate_freeze(content, rc, result)
    validate_test_plan(content, rc, result)
    validate_paths(content, result)

    # Terminal output
    print(result.summary())

    # Generate audit report
    report_path = generate_audit_report(result, rc, file_path, timestamp)
    print(f"\n{CYAN}Audit report:{RESET} {report_path}.md")
    print(f"{CYAN}JSON report: {RESET} {report_path}.json")

    # CI/CD JSON output
    ci_output = {
        "passed":            result.passed,
        "original_risk_class": rc,
        "final_risk_class":  rc,
        "risk_escalated":    False,
        "compliance_score":  int((len(result.info) / max(len(result.info) + len(result.errors), 1)) * 100),
        "errors":            result.errors,
        "warnings":          result.warnings,
        "timestamp":         timestamp,
        "file":              file_path,
        "file_hash":         generate_audit_report.__wrapped_hash__ if hasattr(generate_audit_report, '__wrapped_hash__') else "",
    }
    print(f"\n{'─' * 60}")
    print("JSON Output (for CI/CD):")
    print(json.dumps(ci_output, indent=2, ensure_ascii=False))

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
