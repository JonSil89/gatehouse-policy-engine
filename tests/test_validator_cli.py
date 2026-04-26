import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from validation.pre_merge_checks.config import get_required_approvers, load_config
VALIDATOR = REPO_ROOT / "validation" / "pre-merge-checks" / "validate-change-request.py"
VALID_EXAMPLE = REPO_ROOT / "examples" / "example-change-request.md"
TEMPLATE_FILE = REPO_ROOT / "templates" / "change-request-template.md"


class ValidatorCliTests(unittest.TestCase):
    def run_validator(self, target_file):
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(target_file)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

    def test_valid_example_passes(self):
        result = self.run_validator(VALID_EXAMPLE)
        self.assertEqual(result.returncode, 0)
        self.assertIn("QUALITY GATE: PASSED", result.stdout)
        self.assertIn('"passed": true', result.stdout)

    def test_template_fails(self):
        result = self.run_validator(TEMPLATE_FILE)
        self.assertEqual(result.returncode, 1)
        self.assertIn("QUALITY GATE: FAILED", result.stdout)
        self.assertIn('"passed": false', result.stdout)

    def test_missing_argument_fails(self):
        result = subprocess.run(
            [sys.executable, str(VALIDATOR)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage: python", result.stderr)

    def test_config_fallback_defaults(self):
        config = load_config(config_path=str(REPO_ROOT / "missing-gatehouse.yaml"))
        self.assertEqual(get_required_approvers(config)[2], 2)

    def test_config_override_required_approvers(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "gatehouse.yaml"
            config_path.write_text(
                json.dumps(
                    {
                        "policy": {
                            "required_approvers": {
                                "1": 1,
                                "2": 5,
                                "3": 3,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            config = load_config(config_path=str(config_path))
            self.assertEqual(get_required_approvers(config)[2], 5)


if __name__ == "__main__":
    unittest.main()
