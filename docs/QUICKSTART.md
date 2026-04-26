# Gatehouse Compliance Kit — Quickstart

## 1) Install into a repository
From the Compliance Kit repository root:

```bash
./install.sh /path/to/your-repository
```

If no target path is provided, files are installed into the current working directory.

The installer is idempotent:
- creates required folders
- copies missing files
- does not overwrite existing files

## 2) Fill a change request
Use:
- `templates/change-request-template.md`
- `templates/rollback-plan-template.md`

Keep a reference example in:
- `examples/example-change-request.md`

## 3) Validate locally
```bash
python validation/pre-merge-checks/validate-change-request.py examples/example-change-request.md
```

Expected result:
- `QUALITY GATE: PASSED`
- JSON output at the end for CI/CD integration

## 4) Configure policy values
Edit `gatehouse.yaml`:
- `required_approvers` per risk class
- `allowed_environments`
- `rule_toggles`

If config is missing or invalid, defaults are used (backward-compatible behavior).

## 5) GitHub Actions
Workflow file:
- `.github/workflows/quality-gate-demo.yml`

The workflow is fail-closed:
- if no valid change request file is detected, validation fails
