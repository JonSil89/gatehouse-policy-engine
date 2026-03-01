#!/usr/bin/env python3
import re
import sys
import os
import json
from datetime import datetime, timezone

class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.infos = []

    def add_error(self, msg):
        self.errors.append(msg)

    def add_warning(self, msg):
        self.warnings.append(msg)

    def add_info(self, msg):
        self.infos.append(msg)

   @property
    def passed(self):
        return len(self.errors) == 0

    def summary(self):
        GREEN = '\033[92m'
        RED = '\033[91m'
        RESET = '\033[0m'
        lines = ["=" * 60]
        if self.passed:
            lines.append(f"{GREEN}QUALITY GATE: PASSED{RESET}")
        else:
            lines.append(f"{RED}QUALITY GATE: FAILED{RESET}")
        lines.append("=" * 60)
<<<<<<< HEAD
        if self.passed:
            lines.append(f"{GREEN}QUALITY GATE: PASSED{RESET}")
        else:
            lines.append(f"{RED}QUALITY GATE: FAILED{RESET}")
        lines.append("=" * 60)

=======
        if self.infos:
            lines.append("\nINFO:")
            for info in self.infos:
                lines.append(f"  [i] {info}")
>>>>>>> 81b48bc (compliance: finalize validation engine and archive audit evidence)
        if self.warnings:
            lines.append("\nWARNINGS:")
            for warn in self.warnings:
                lines.append(f"  [!] {warn}")
        if self.errors:
            lines.append("\nERRORS:")
            for error in self.errors:
                lines.append(f"  [X] {error}")
        lines.append("-" * 60)
        return "\n".join(lines)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate-change-request.py <file>")
        sys.exit(2)
    
    file_path = sys.argv[1]
    result = ValidationResult()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    result.add_info(f"Validointi aloitettu: {timestamp}")
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        sys.exit(2)
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Yksinkertaistettu validointi esimerkkia varten
    if "Riskiluokka" not in content:
        result.add_error("Riskiluokka-kenttä puuttuu")
    
    print(result.summary())
    
    json_out = {
        "passed": result.passed,
        "timestamp": timestamp,
        "file": file_path,
        "errors": result.errors
    }
    print("\n--- JSON Output ---")
    print(json.dumps(json_out, indent=2))
    
    sys.exit(0 if result.passed else 1)

if __name__ == "__main__":
    main()
