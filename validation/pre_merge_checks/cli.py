#!/usr/bin/env python3
"""
Infrastructure Change Quality Gate - Muutospyynnon validointi.
"""

import os
import sys
from datetime import datetime, timezone

from validation.pre_merge_checks.config import (
    get_allowed_environments,
    get_freeze_periods,
    get_required_approvers,
    get_required_sections,
    get_rule_toggle,
    load_config,
)
from validation.pre_merge_checks.parser import read_change_request
from validation.pre_merge_checks.reporter import emit_json_output
from validation.pre_merge_checks.rules import (
    ValidationResult,
    build_required_fields,
    validate_approvers,
    validate_freeze_period,
    validate_no_absolute_paths,
    validate_required_fields,
    validate_required_sections,
    validate_risk_class,
    validate_rollback_plan,
    validate_test_plan,
)


def main():
    """Main validation entry point."""
    if len(sys.argv) < 2:
        script_name = os.path.basename(sys.argv[0])
        print(f"Usage: python {script_name} <change-request.md>", file=sys.stderr)
        print("", file=sys.stderr)
        print("Validates an infrastructure change request against quality gate criteria.", file=sys.stderr)
        sys.exit(2)

    file_path = sys.argv[1]
    config = load_config()
    result = ValidationResult()

    # Log start
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result.add_info(f"Validointi aloitettu: {timestamp}")
    result.add_info(f"Tiedosto: {file_path}")

    # Read file
    content = read_change_request(file_path)

    required_sections = get_required_sections(config)
    required_fields = build_required_fields(get_allowed_environments(config))
    min_approvers = get_required_approvers(config)
    freeze_periods = get_freeze_periods(config)

    # Run validations
    validate_required_sections(content, result, required_sections)
    validate_required_fields(content, result, required_fields)

    risk_class = validate_risk_class(
        content,
        result,
        require_risk_justification=get_rule_toggle(
            config, "require_risk_justification", True
        ),
    )

    validate_rollback_plan(
        content,
        risk_class,
        result,
        require_rollback_for_class_2_3=get_rule_toggle(
            config, "require_rollback_for_class_2_3", True
        ),
        require_rollback_test_for_class_3=get_rule_toggle(
            config, "require_rollback_test_for_class_3", True
        ),
    )
    validate_approvers(content, risk_class, result, min_approvers)
    validate_freeze_period(
        content,
        risk_class,
        result,
        freeze_periods=freeze_periods,
        require_freeze_check_for_class_3=get_rule_toggle(
            config, "require_freeze_check_for_class_3", True
        ),
    )
    validate_test_plan(
        content,
        risk_class,
        result,
        require_test_plan_for_class_2_3=get_rule_toggle(
            config, "require_test_plan_for_class_2_3", True
        ),
    )
    validate_no_absolute_paths(
        content,
        result,
        enabled=get_rule_toggle(config, "warn_on_absolute_paths", True),
    )

    # Output results
    print(result.summary())
    emit_json_output(result, risk_class, timestamp, file_path)

    # Exit code
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
