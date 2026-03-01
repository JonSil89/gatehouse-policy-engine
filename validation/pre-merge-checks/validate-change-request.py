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
        # 1. Riskiluokka
        ri_luokka = self.extract_value("Riskiluokka")
        self.results['Riskiluokka'] = ri_luokka
        if not ri_luokka:
            self.errors.append("Riskiluokkaa ei löydetty.")
        
        # 2. Palautussuunnitelma
        has_rollback = "palautussuunnitelma" in self.content.lower()
        self.results['Rollback'] = "Löytyy" if has_rollback else "PUUTTUU"
        if not has_rollback:
            self.errors.append("Palautussuunnitelma puuttuu.")

        return len(self.errors) == 0

    def generate_reports(self, folder_path):
        os.makedirs(folder_path, exist_ok=True)
        ts_file = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
        status_str = "PASSED" if not self.errors else "FAILED"
        
        # Tiedoston perusnimi sisältää statuksen, jotta ne eivät ylikirjoita toisiaan
        base_name = f"report-{status_str}"
        full_path = os.path.join(folder_path, base_name)

        ts_human = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        status_icon = "✅ PASSED" if not self.errors else "❌ FAILED"

        # --- MD Raportti ---
        md = [
            f"# 🏛️ Gatehouse Audit Report",
            f"**Status:** {status_icon}",
            f"**Timestamp:** {ts_human}\n",
            "| Check | Value | Status |",
            "| :--- | :--- | :--- |",
            f"| Risk Class | {self.results.get('Riskiluokka', 'N/A')} | {'✅' if self.results.get('Riskiluokka') else '❌'} |",
            f"| Rollback Plan | {self.results.get('Rollback')} | {'✅' if self.results.get('Rollback') == 'Löytyy' else '❌'} |"
        ]
        if self.errors:
            md.append("\n### ⚠️ Critical Findings:")
            for err in self.errors: md.append(f"- {err}")
        
        with open(f"{full_path}.md", "w", encoding="utf-8") as f:
            f.write("\n".join(md))

        # --- JSON Raportti ---
        json_data = {
            "audit_status": status_str,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": self.results,
            "errors": self.errors
        }
        with open(f"{full_path}.json", "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)

def main():
    if len(sys.argv) < 2: sys.exit(1)
    file_to_check = sys.argv[1]
    
    with open(file_to_check, 'r', encoding='utf-8') as f:
        content = f.read()
    
    engine = GatehouseEngine(content)
    passed = engine.validate()
    
    # Tallennetaan raportit kansioon
    engine.generate_reports("evidence/compliance-reports")
    
    print(json.dumps({"file": file_to_check, "passed": passed, "errors": engine.errors}, indent=2))
    # CI/CD: Exit 0 vaikka failaisi, jotta workflow jatkuu raportin tallennukseen asti jos halutaan
    # Mutta yleensä exit 1 on parempi blockaamiseen.
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
