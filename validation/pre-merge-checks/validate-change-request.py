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

RISK_CLASS_PATTERN      = re.compile(r"\*\*Riskiluokka:\*\*\s+([123])")
APPROVER_PATTERN        = re.compile(r"\*\*Hyväksyjä\s+\d+:\*\*\s+(?!\[Nimi\])(\S+)")
ROLLBACK_SECTION        = re.compile(r"##\s+Palautussuunnitelma", re.IGNORECASE)
ROLLBACK_STRATEGY       = re.compile(
    r"\*\*Palautusstrategia:\*\*\s+(?!\[)"
    r"(git revert|konfiguraation palautus|snapshot restore|blue-green switch|\S+)"
)
ROLLBACK_TESTED         = re.compile(r"\*\*Onko palautus testattu\?\*\*\s+Kyllä", re.IGNORECASE)
TEST_SECTION            = re.compile(r"##\s+Testaussuunnitelma", re.IGNORECASE)
TEST_ENV                = re.compile(r"\*\*Testausympäristö:\*\*\s+(?!\[)(dev|staging)", re.IGNORECASE)
TEST_ENV_STAGING        = re.compile(r"\*\*Testausympäristö:\*\*\s+staging", re.IGNORECASE)
FREEZE_CHECK            = re.compile(r"\*\*Freeze-periodi tarkistettu:\*\*\s+Kyllä", re.IGNORECASE)
PROPOSED_DATE           = re.compile(r"\*\*Ehdotettu toteutusaika:\*\*\s+(\d{4}-\d{2}-\d{2})")
RISK_JUSTIFICATION      = re.compile(
    r"###\s+Riskiluokan perustelu\s*\n+(?!\[Miksi)(\S+)", re.MULTILINE
)
CISO_PATTERN            = re.compile(r"CISO", re.IGNORECASE)

MIN_APPROVERS = {1: 1, 2: 2, 3: 3}

# Add freeze periods here when needed:
# ("2026-12-20", "2027-01-05"),  # Year-end freeze
FREEZE_PERIODS = []


# ─── Validation Result ─────────────────────────────────────────────────────────

class ValidationResult:
    def __init__(self):
        self.errors   = []
        self.warnings = []
        self.info     = []

    def error(self, msg):   self.errors.append(msg)
    def warning(self, msg): self.warnings.append(msg)
    def info_msg(self, msg): self.info.append(msg)

    @property
    def passed(self):
        return len(self.errors) == 0

    def summary(self):
        lines = []
        sep = "=" * 60

        lines.append(sep)
        if self.passed:
            lines.append(f"{GREEN}{BOLD}QUALITY GATE: PASSED{RESET}")
        else:
            lines.append(f"{RED}{BOLD}QUALITY GATE: FAILED{RESET}")
        lines.append(sep)

        if self.errors:
            lines.append(f"\n{RED}ERRORS ({len(self.errors)}):{RESET}")
            for i, e in enumerate(self.errors, 1):
                lines.append(f"  {RED}[{i}]{RESET} {e}")

        if self.warnings:
            lines.append(f"\n{YELLOW}WARNINGS ({len(self.warnings)}):{RESET}")
            for i, w in enumerate(self.warnings, 1):
                lines.append(f"  {YELLOW}[{i}]{RESET} {w}")

        if self.info:
            lines.append(f"\n{CYAN}INFO:{RESET}")
            for msg in self.info:
                lines.append(f"  - {msg}")

        lines.append(f"\n{sep}")
        return "\n".join(lines)


# ─── Validation Functions ──────────────────────────────────────────────────────

def validate_sections(content, result):
    for section in REQUIRED_SECTIONS:
        pattern = re.compile(rf"^##\s+{re.escape(section)}", re.MULTILINE)
        if not pattern.search(content):
            result.error(f"Pakollinen osio puuttuu: '{section}'")
        else:
            result.info_msg(f"Osio löytyi: '{section}'")


def validate_fields(content, result):
    for name, pattern_str in REQUIRED_FIELDS.items():
        if not re.search(pattern_str, content):
            result.error(f"Pakollinen kenttä puuttuu tai ei ole täytetty: '{name}'")
        else:
            result.info_msg(f"Kenttä täytetty: '{name}'")


def extract_risk_class(content, result):
    match = RISK_CLASS_PATTERN.search(content)
    if not match:
        result.error("Riskiluokka puuttuu tai on virheellinen (1, 2 tai 3)")
        return None
    rc = int(match.group(1))
    result.info_msg(f"Riskiluokka: {rc}")

    if not RISK_JUSTIFICATION.search(content):
        result.error("Riskiluokan perustelu puuttuu tai on placeholder-arvo")

    return rc


def validate_rollback(content, rc, result):
    if rc is None or rc < 2:
        if rc == 1:
            result.info_msg("Luokka 1: Rollback-suunnitelma suositeltu mutta ei pakollinen")
        return

    if not ROLLBACK_SECTION.search(content):
        result.error(f"Luokka {rc}: Palautussuunnitelma-osio puuttuu (pakollinen)")
        return

    if not ROLLBACK_STRATEGY.search(content):
        result.error(f"Luokka {rc}: Palautusstrategia ei ole määritelty")

    if rc == 3 and not ROLLBACK_TESTED.search(content):
        result.error("Luokka 3: Palautussuunnitelmaa ei ole merkitty testatuksi (pakollinen)")


def validate_approvers(content, rc, result):
    if rc is None:
        return

    approvers = APPROVER_PATTERN.findall(content)
    required  = MIN_APPROVERS.get(rc, 1)

    if len(approvers) < required:
        result.error(
            f"Luokka {rc}: Vaaditaan vähintään {required} hyväksyjää, "
            f"löytyi {len(approvers)}"
        )
    else:
        result.info_msg(f"Hyväksyjät: {len(approvers)}/{required} (OK)")

    # Class 3: verify CISO is among approvers
    if rc == 3:
        approver_block = re.findall(
            r"\*\*Hyväksyjä\s+\d+:\*\*.*", content, re.IGNORECASE
        )
        ciso_found = any(CISO_PATTERN.search(line) for line in approver_block)
        if not ciso_found:
            result.error("Luokka 3: CISO:n hyväksyntä puuttuu (pakollinen)")
        else:
            result.info_msg("CISO-hyväksyntä: löytyi")


def validate_test_plan(content, rc, result):
    if rc is None or rc < 2:
        return

    if not TEST_SECTION.search(content):
        result.error(f"Luokka {rc}: Testaussuunnitelma-osio puuttuu (pakollinen)")
        return

    if not TEST_ENV.search(content):
        result.warning(f"Luokka {rc}: Testausympäristöä ei ole määritelty")

    if rc == 3 and not TEST_ENV_STAGING.search(content):
        result.error("Luokka 3: Testaus pitää suorittaa staging-ympäristössä")


def validate_freeze(content, rc, result):
    if rc is None or rc < 3:
        return

    if not FREEZE_CHECK.search(content):
        result.error("Luokka 3: Freeze-periodi ei ole tarkistettu (pakollinen)")
        return

    date_match = PROPOSED_DATE.search(content)
    if date_match:
        proposed = date_match.group(1)
        for start, end in FREEZE_PERIODS:
            if start <= proposed <= end:
                result.error(
                    f"Luokka 3: Ehdotettu päivä {proposed} osuu "
                    f"freeze-periodille ({start} – {end})"
                )
                return
        result.info_msg(f"Freeze-tarkistus OK: {proposed} ei osu freeze-periodille")


def validate_paths(content, result):
    checks = [
        (r'[A-Z]:\\', "Windows absoluuttinen polku"),
        (r'(?<!\[)/(?:Users|home|etc|var|opt|usr)/', "Unix absoluuttinen polku"),
    ]
    for pattern, desc in checks:
        if re.search(pattern, content):
            result.warning(f"Mahdollinen absoluuttinen polku havaittu ({desc})")


# ─── Audit Report Generator ────────────────────────────────────────────────────

def generate_audit_report(result, rc, file_path, timestamp):
    folder = Path("evidence/compliance-reports")
    folder.mkdir(parents=True, exist_ok=True)

    status    = "PASSED" if result.passed else "FAILED"
    ts_short  = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base_name = folder / f"report-{status}-{ts_short}"

    # Markdown report
    status_icon = "✅" if result.passed else "❌"
    md_lines = [
        "# 🏛️ Gatehouse Audit Report",
        "",
        f"**Status:** {status_icon} {status}  ",
        f"**File:** `{file_path}`  ",
        f"**Timestamp:** {timestamp}  ",
        f"**Risk Class:** {rc if rc else 'N/A'}",
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
        f"*Generated by Gatehouse Policy Engine | ISO 27001 A.12.4.1*",
    ]

    with open(f"{base_name}.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # JSON report
    json_data = {
        "audit_status": status,
        "timestamp":    timestamp,
        "file":         file_path,
        "risk_class":   rc,
        "passed":       result.passed,
        "errors":       result.errors,
        "warnings":     result.warnings,
        "info":         result.info,
        "iso_controls": ["A.12.1.2", "A.14.2.2", "A.12.4.1"],
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
        "passed":     result.passed,
        "risk_class": rc,
        "errors":     result.errors,
        "warnings":   result.warnings,
        "timestamp":  timestamp,
        "file":       file_path,
    }
    print(f"\n{'─' * 60}")
    print("JSON Output (for CI/CD):")
    print(json.dumps(ci_output, indent=2, ensure_ascii=False))

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
