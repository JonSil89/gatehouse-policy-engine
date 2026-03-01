#!/usr/bin/env python3
import re, sys, os, json
from datetime import datetime, timezone

class GatehouseEngine:
    def __init__(self, content):
        self.content = content
        self.results = {}
        self.errors = []

    def extract_value(self, field_name):
        patterns = [
            rf"\| {field_name} \| (.*?) \|",
            rf"{field_name}[:\s\*]+(.*?)(?:\n|$)"
        ]
        for pattern in patterns:
            match = re.search(pattern, self.content, re.IGNORECASE)
            if match: return match.group(1).strip()
        return None

    def validate(self):
        # 1. Riskiluokka (Pakollinen numero 1-3)
        ri_luokka = self.extract_value("Riskiluokka")
        self.results['Riskiluokka'] = ri_luokka
        if not ri_luokka:
            self.errors.append("Riskiluokkaa ei löydetty (odotettiin numeroa).")
        
        # 2. Palautussuunnitelma (Pakollinen avainsana)
        has_rollback = "palautussuunnitelma" in self.content.lower()
        self.results['Rollback'] = "Löytyy" if has_rollback else "PUUTTUU"
        if not has_rollback:
            self.errors.append("Kriittinen puute: Palautussuunnitelma (Rollback plan) puuttuu dokumentista.")

        return len(self.errors) == 0

    def generate_reports(self, base_path):
        os.makedirs(os.path.dirname(base_path), exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        status = "✅ PASSED" if not self.errors else "❌ FAILED"

        # --- Generoi Markdown ---
        md = [
            f"# 🏛️ Gatehouse Audit Report",
            f"**Status:** {status}",
            f"**Timestamp:** {ts}\n",
            "| Check | Value | Status |",
            "| :--- | :--- | :--- |",
            f"| Risk Class | {self.results.get('Riskiluokka', 'N/A')} | {'✅' if self.results.get('Riskiluokka') else '❌'} |",
            f"| Rollback Plan | {self.results.get('Rollback')} | {'✅' if self.results.get('Rollback') == 'Löytyy' else '❌'} |"
        ]
        if self.errors:
            md.append("\n### ⚠️ Critical Findings:")
            for err in self.errors: md.append(f"- {err}")
        
        with open(f"{base_path}.md", "w", encoding="utf-8") as f:
            f.write("\n".join(md))

        # --- Generoi JSON ---
        json_data = {
            "audit_status": "COMPLIANT" if not self.errors else "NON-COMPLIANT",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": self.results,
            "errors": self.errors
        }
        with open(f"{base_path}.json", "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)

def main():
    if len(sys.argv) < 2: sys.exit(1)
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    engine = GatehouseEngine(content)
    passed = engine.validate()
    engine.generate_reports("evidence/compliance-reports/report")
    
    # Tulostetaan JSON terminaaliin CI/CD:tä varten
    print(json.dumps({"passed": passed, "errors": engine.errors}, indent=2))
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
