#!/usr/bin/env python3
"""
Infrastructure Change Quality Gate - Muutospyynnon validointi.

Tarkistaa PR:aan liitetyn muutospyynnon automaattisesti:
- Pakolliset kentat
- Riskiluokan validointi (1-3)
- Palautussuunnitelma (luokat 2-3)
- Hyvaksyntaketju (riskiluokan mukaan)
- Freeze-periodin tarkistus (luokka 3)

Exit-koodit:
  0 = Hyvaksytty
  1 = Hylatty (puutteita)
  2 = Virhe (skriptin suorituksessa)

Kayttaa vain Python-standardikirjastoa (ei ulkoisia riippuvuuksia).
POSIX-yhteensopiva: relatiiviset polut, LF-rivinvaihdot.
"""

import re
import sys
import os
import json
from datetime import datetime, timezone
from pathlib import PurePosixPath


# --- Configuration ---

REQUIRED_SECTIONS = [
    "Perustiedot",
    "Kuvaus",
    "Vaikutusanalyysi",
]

REQUIRED_FIELDS = {
    "Muutoksen nimi": r"\*\*Muutoksen nimi:\*\*\s+\S",
    "Pyytaja": r"\*\*Pyytäjä:\*\*\s+\S",
    "Paivamaara": r"\*\*Päivämäärä:\*\*\s+\d{4}-\d{2}-\d{2}",
    "Riskiluokka": r"\*\*Riskiluokka:\*\*\s+[123]",
    "Kohdeymparisto": r"\*\*Kohdeympäristö:\*\*\s+(dev|staging|production)",
}

RISK_CLASS_PATTERN = re.compile(r"\*\*Riskiluokka:\*\*\s+([123])")

APPROVER_PATTERN = re.compile(
    r"\*\*Hyväksyjä\s+\d+:\*\*\s+(?!\[Nimi\])(\S+)"
)

ROLLBACK_SECTION_PATTERN = re.compile(
    r"## Palautussuunnitelma", re.IGNORECASE
)

ROLLBACK_STRATEGY_PATTERN = re.compile(
    r"\*\*Palautusstrategia:\*\*\s+(?!\[)(git revert|konfiguraation palautus|snapshot restore|blue-green switch|\S+)"
)

FREEZE_CHECK_PATTERN = re.compile(
    r"\*\*Freeze-periodi tarkistettu:\*\*\s+Kyllä", re.IGNORECASE
)

MIN_APPROVERS = {
    1: 1,
    2: 2,
    3: 3,
}

# Example freeze periods (ISO format date ranges)
# In production, these would be loaded from a configuration file
FREEZE_PERIODS = [
    # ("2026-12-20", "2027-01-05"),  # Year-end freeze
]


class ValidationResult:
    """Collects validation findings."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

    def add_error(self, message):
        self.errors.append(message)

    def add_warning(self, message):
        self.warnings.append(message)

    def add_info(self, message):
        self.info.append(message)

   @property
    def passed(self):
        return len(self.errors) == 0

    def summary(self):
        GREEN = '\033[92m'
        RED = '\033[91m'
        RESET = '\033[0m'

        lines = []
        lines.append("=" * 60)
        if self.passed:
            lines.append(f"{GREEN}QUALITY GATE: PASSED{RESET}")
        else:
            lines.append(f"{RED}QUALITY GATE: FAILED{RESET}")
        lines.append("=" * 60)
        if self.passed:
            lines.append(f"{GREEN}QUALITY GATE: PASSED{RESET}")
        else:
            lines.append(f"{RED}QUALITY GATE: FAILED{RESET}")
        lines.append("=" * 60)

        if self.warnings:
            lines.append("")
            lines.append(f"WARNINGS ({len(self.warnings)}):")
            for i, warn in enumerate(self.warnings, 1):
                lines.append(f"  [{i}] {warn}")

        if self.info:
            lines.append("")
            lines.append("INFO:")
            for msg in self.info:
                lines.append(f"  - {msg}")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)


def read_change_request(file_path):
    """Read a change request file using relative path."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"ERROR: Change request file not found: {file_path}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"ERROR: Could not read file: {e}", file=sys.stderr)
        sys.exit(2)


def validate_required_sections(content, result):
    """Check that all required sections exist."""
    for section in REQUIRED_SECTIONS:
        pattern = re.compile(rf"^##\s+{re.escape(section)}", re.MULTILINE)
        if not pattern.search(content):
            result.add_error(f"Pakollinen osio puuttuu: '{section}'")
        else:
            result.add_info(f"Osio loytyi: '{section}'")


def validate_required_fields(content, result):
    """Check that all required fields are filled in (not placeholder values)."""
    for field_name, pattern_str in REQUIRED_FIELDS.items():
        pattern = re.compile(pattern_str)
        if not pattern.search(content):
            result.add_error(
                f"Pakollinen kentta puuttuu tai ei ole taytetty: '{field_name}'"
            )
        else:
            result.add_info(f"Kentta taytetty: '{field_name}'")


def extract_risk_class(content):
    """Extract risk class (1-3) from content."""
    match = RISK_CLASS_PATTERN.search(content)
    if match:
        return int(match.group(1))
    return None


def validate_risk_class(content, result):
    """Validate risk class is present and valid."""
    risk_class = extract_risk_class(content)
    if risk_class is None:
        result.add_error("Riskiluokka puuttuu tai on virheellinen (pitaa olla 1, 2 tai 3)")
        return None

    result.add_info(f"Riskiluokka: {risk_class}")

    # Check that risk class justification exists
    justification_pattern = re.compile(
        r"### Riskiluokan perustelu\s*\n+(?!\[Miksi)(\S+)", re.MULTILINE
    )
    if not justification_pattern.search(content):
        result.add_error("Riskiluokan perustelu puuttuu tai on placeholder-arvo")

    return risk_class


def validate_rollback_plan(content, risk_class, result):
    """Validate rollback plan for risk classes 2 and 3."""
    if risk_class is None or risk_class < 2:
        if risk_class == 1:
            result.add_info("Luokka 1: Rollback-suunnitelma suositeltu mutta ei pakollinen")
        return

    if not ROLLBACK_SECTION_PATTERN.search(content):
        result.add_error(
            f"Luokka {risk_class}: Palautussuunnitelma-osio puuttuu (pakollinen)"
        )
        return

    if not ROLLBACK_STRATEGY_PATTERN.search(content):
        result.add_error(
            f"Luokka {risk_class}: Palautusstrategia ei ole maaritelty"
        )

    if risk_class == 3:
        tested_pattern = re.compile(
            r"\*\*Onko palautus testattu\?\*\*\s+Kyllä", re.IGNORECASE
        )
        if not tested_pattern.search(content):
            result.add_error(
                "Luokka 3: Palautussuunnitelmaa ei ole merkitty testatuksi (pakollinen)"
            )


def validate_approvers(content, risk_class, result):
    """Validate sufficient number of approvers are named."""
    if risk_class is None:
        return

    approvers = APPROVER_PATTERN.findall(content)
    required = MIN_APPROVERS.get(risk_class, 1)

    if len(approvers) < required:
        result.add_error(
            f"Luokka {risk_class}: Tarvitaan vahintaan {required} nimettyä hyväksyjää, "
            f"loytyi {len(approvers)}"
        )
    else:
        result.add_info(f"Hyvaksyjat: {len(approvers)}/{required} (OK)")


def validate_freeze_period(content, risk_class, result):
    """Check freeze period for risk class 3."""
    if risk_class is None or risk_class < 3:
        return

    if not FREEZE_CHECK_PATTERN.search(content):
        result.add_error(
            "Luokka 3: Freeze-periodi ei ole tarkistettu (pakollinen)"
        )
        return

    # Check proposed date against freeze periods
    date_pattern = re.compile(
        r"\*\*Ehdotettu toteutusaika:\*\*\s+(\d{4}-\d{2}-\d{2})"
    )
    date_match = date_pattern.search(content)
    if date_match:
        proposed_date = date_match.group(1)
        for freeze_start, freeze_end in FREEZE_PERIODS:
            if freeze_start <= proposed_date <= freeze_end:
                result.add_error(
                    f"Luokka 3: Ehdotettu paiva {proposed_date} osuu "
                    f"freeze-periodille ({freeze_start} - {freeze_end})"
                )
                return
        result.add_info(f"Freeze-tarkistus OK: {proposed_date} ei osu freeze-periodille")


def validate_test_plan(content, risk_class, result):
    """Validate test plan for risk classes 2 and 3."""
    if risk_class is None or risk_class < 2:
        return

    test_section_pattern = re.compile(r"## Testaussuunnitelma", re.IGNORECASE)
    if not test_section_pattern.search(content):
        result.add_error(
            f"Luokka {risk_class}: Testaussuunnitelma-osio puuttuu (pakollinen)"
        )
        return

    env_pattern = re.compile(
        r"\*\*Testausympäristö:\*\*\s+(?!\[)(dev|staging)"
    )
    if not env_pattern.search(content):
        result.add_warning(
            f"Luokka {risk_class}: Testausymparistoa ei ole maaritelty"
        )

    if risk_class == 3:
        staging_pattern = re.compile(
            r"\*\*Testausympäristö:\*\*\s+staging", re.IGNORECASE
        )
        if not staging_pattern.search(content):
            result.add_error(
                "Luokka 3: Testaus pitaa suorittaa staging-ymparistossa"
            )


def validate_no_absolute_paths(content, result):
    """Ensure no absolute paths are present in the change request."""
    abs_path_patterns = [
        (r'[A-Z]:\\', "Windows-tyylinen absoluuttinen polku"),
        (r'(?<!\[)/(?:Users|home|etc|var|opt|usr)/', "Unix absoluuttinen polku"),
    ]
    for pattern_str, description in abs_path_patterns:
        pattern = re.compile(pattern_str)
        if pattern.search(content):
            result.add_warning(
                f"Dokumentti sisaltaa mahdollisen absoluuttisen polun ({description})"
            )


def main():
    """Main validation entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate-change-request.py <change-request.md>", file=sys.stderr)
        print("", file=sys.stderr)
        print("Validates an infrastructure change request against quality gate criteria.", file=sys.stderr)
        sys.exit(2)

    file_path = sys.argv[1]
    result = ValidationResult()

    # Log start
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result.add_info(f"Validointi aloitettu: {timestamp}")
    result.add_info(f"Tiedosto: {file_path}")

    # Read file
    content = read_change_request(file_path)

    # Run validations
    validate_required_sections(content, result)
    validate_required_fields(content, result)

    risk_class = validate_risk_class(content, result)

    validate_rollback_plan(content, risk_class, result)
    validate_approvers(content, risk_class, result)
    validate_freeze_period(content, risk_class, result)
    validate_test_plan(content, risk_class, result)
    validate_no_absolute_paths(content, result)

    # Output results
    print(result.summary())

    # Output JSON for CI/CD integration
    json_result = {
        "passed": result.passed,
        "risk_class": risk_class,
        "errors": result.errors,
        "warnings": result.warnings,
        "timestamp": timestamp,
        "file": file_path,
    }
    print("")
    print("--- JSON Output (for CI/CD) ---")
    print(json.dumps(json_result, indent=2, ensure_ascii=False))

    # Exit code
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
