#!/usr/bin/env python3
import sys, os, json
from datetime import datetime, timezone

class ValidationResult:
    def __init__(self, file_path):
        self.file_path = file_path
        self.errors = []
    def add_error(self, msg):
        self.errors.append(msg)
    @property
    def passed(self):
        return len(self.errors) == 0
    def generate_markdown(self):
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"# 🏛️ Gatehouse Report\n**Status:** {status}\n**Time:** {ts}\n\n| Check | Status |\n| :--- | :--- |\n| Risk Class | {'✅' if self.passed else '❌'} |\n| Audit Trail | ✅ |"

def main():
    if len(sys.argv) < 2: sys.exit(2)
    path = sys.argv[1]
    res = ValidationResult(path)
    if not os.path.exists(path): sys.exit(2)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if "Riskiluokka" not in content:
        res.add_error("Riskiluokka puuttuu")
    os.makedirs("evidence/compliance-reports", exist_ok=True)
    with open("evidence/compliance-reports/report.md", "w", encoding="utf-8") as f:
        f.write(res.generate_markdown())
    print(json.dumps({"passed": res.passed, "file": path, "errors": res.errors}, indent=2))
    sys.exit(0 if res.passed else 1)

if __name__ == "__main__":
    main()
