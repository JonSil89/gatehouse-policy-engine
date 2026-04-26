import json


def emit_json_output(result, risk_class, timestamp, file_path):
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
