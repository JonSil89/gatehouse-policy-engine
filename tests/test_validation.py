import pytest
from validation.pre_merge_checks.validate_change_request import validate_change

def test_valid_change_request():
    result = validate_change("examples/example-change-request.md")
    assert result["status"] == "PASSED"

def test_invalid_change_request():
    result = validate_change("examples/invalid-change-request.md")
    assert result["status"] == "FAILED"
