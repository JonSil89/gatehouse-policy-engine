import re


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


def build_required_fields(allowed_environments):
    envs = [e for e in allowed_environments if isinstance(e, str) and e.strip()]
    if not envs:
        envs = ["dev", "staging", "production"]
    env_pattern = "|".join(re.escape(e.lower()) for e in envs)

    return {
        "Muutoksen nimi": r"\*\*Muutoksen nimi:\*\*\s+\S",
        "Pyytaja": r"\*\*Pyytäjä:\*\*\s+\S",
        "Paivamaara": r"\*\*Päivämäärä:\*\*\s+\d{4}-\d{2}-\d{2}",
        "Riskiluokka": r"\*\*Riskiluokka:\*\*\s+[123]",
        "Kohdeymparisto": rf"\*\*Kohdeympäristö:\*\*\s+({env_pattern})",
    }


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
        lines = []
        lines.append("=" * 60)
        if self.passed:
            lines.append("QUALITY GATE: PASSED")
        else:
            lines.append("QUALITY GATE: FAILED")
        lines.append("=" * 60)

        if self.errors:
            lines.append("")
            lines.append(f"ERRORS ({len(self.errors)}):")
            for i, err in enumerate(self.errors, 1):
                lines.append(f"  [{i}] {err}")

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


def validate_required_sections(content, result, required_sections):
    """Check that all required sections exist."""
    for section in required_sections:
        pattern = re.compile(rf"^##\s+{re.escape(section)}", re.MULTILINE)
        if not pattern.search(content):
            result.add_error(f"Pakollinen osio puuttuu: '{section}'")
        else:
            result.add_info(f"Osio loytyi: '{section}'")


def validate_required_fields(content, result, required_fields):
    """Check that all required fields are filled in (not placeholder values)."""
    for field_name, pattern_str in required_fields.items():
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


def validate_risk_class(content, result, require_risk_justification=True):
    """Validate risk class is present and valid."""
    risk_class = extract_risk_class(content)
    if risk_class is None:
        result.add_error("Riskiluokka puuttuu tai on virheellinen (pitaa olla 1, 2 tai 3)")
        return None

    result.add_info(f"Riskiluokka: {risk_class}")

    if require_risk_justification:
        justification_pattern = re.compile(
            r"### Riskiluokan perustelu\s*\n+(?!\[Miksi)(\S+)", re.MULTILINE
        )
        if not justification_pattern.search(content):
            result.add_error("Riskiluokan perustelu puuttuu tai on placeholder-arvo")

    return risk_class


def validate_rollback_plan(
    content,
    risk_class,
    result,
    require_rollback_for_class_2_3=True,
    require_rollback_test_for_class_3=True,
):
    """Validate rollback plan for risk classes 2 and 3."""
    if not require_rollback_for_class_2_3:
        return

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

    if risk_class == 3 and require_rollback_test_for_class_3:
        tested_pattern = re.compile(
            r"\*\*Onko palautus testattu\?\*\*\s+Kyllä", re.IGNORECASE
        )
        if not tested_pattern.search(content):
            result.add_error(
                "Luokka 3: Palautussuunnitelmaa ei ole merkitty testatuksi (pakollinen)"
            )


def validate_approvers(content, risk_class, result, min_approvers):
    """Validate sufficient number of approvers are named."""
    if risk_class is None:
        return

    approvers = APPROVER_PATTERN.findall(content)
    required = min_approvers.get(risk_class, 1)

    if len(approvers) < required:
        result.add_error(
            f"Luokka {risk_class}: Tarvitaan vahintaan {required} nimettyä hyväksyjää, "
            f"loytyi {len(approvers)}"
        )
    else:
        result.add_info(f"Hyvaksyjat: {len(approvers)}/{required} (OK)")


def validate_freeze_period(
    content,
    risk_class,
    result,
    freeze_periods,
    require_freeze_check_for_class_3=True,
):
    """Check freeze period for risk class 3."""
    if risk_class is None or risk_class < 3:
        return

    if require_freeze_check_for_class_3 and not FREEZE_CHECK_PATTERN.search(content):
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
        for freeze_start, freeze_end in freeze_periods:
            if freeze_start <= proposed_date <= freeze_end:
                result.add_error(
                    f"Luokka 3: Ehdotettu paiva {proposed_date} osuu "
                    f"freeze-periodille ({freeze_start} - {freeze_end})"
                )
                return
        if freeze_periods:
            result.add_info(f"Freeze-tarkistus OK: {proposed_date} ei osu freeze-periodille")


def validate_test_plan(
    content,
    risk_class,
    result,
    require_test_plan_for_class_2_3=True,
):
    """Validate test plan for risk classes 2 and 3."""
    if not require_test_plan_for_class_2_3:
        return

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


def validate_no_absolute_paths(content, result, enabled=True):
    """Ensure no absolute paths are present in the change request."""
    if not enabled:
        return

    abs_path_patterns = [
        (r"[A-Z]:\\", "Windows-tyylinen absoluuttinen polku"),
        (r"(?<!\[)/(?:Users|home|etc|var|opt|usr)/", "Unix absoluuttinen polku"),
    ]
    for pattern_str, description in abs_path_patterns:
        pattern = re.compile(pattern_str)
        if pattern.search(content):
            result.add_warning(
                f"Dokumentti sisaltaa mahdollisen absoluuttisen polun ({description})"
            )
