#!/usr/bin/env python3
import re, sys, os, json
from datetime import datetime, timezone

class GatehouseEngine:
    def __init__(self, content):
        self.content = content
        self.results = {}
        self.errors = []

    def extract_value(self, field_name):
        # Etsii arvon Markdown-taulukosta tai listasta
        # Tukee muotoja: | Kenttä | Arvo |  TAI  **Kenttä:** Arvo
        patterns = [
            rf"\| {field_name} \| (.*?) \|",
            rf"{field_name}[:\s\*]+(.*?)(?:\n|$)"
        ]
        for pattern in patterns:
            match = re.search(pattern, self.content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def validate(self):
        # 1. Louhitaan Riskiluokka
        ri_luokka = self.extract_value("Riskiluokka")
        self.results['Riskiluokka'] = ri_luokka
        if not ri_luokka:
            self.errors.append("Riskiluokkaa ei löydetty dokumentista.")

        # 2. Tarkistetaan onko palautussuunnitelma mainittu
        has_rollback = "palautussuunnitelma" in self.content.lower()
        self.results['Rollback'] = "Löytyy" if has_rollback else "PUUTTUU"
        if not has_rollback:
            self.errors.append("Palautussuunnitelma puuttuu.")

        return len(self.errors) == 0

    def generate_report(self, path):
        status = "✅ HYVÄKSYTTY" if not self.errors else "❌ HYLÄTTY"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        md = [
            f"# 🏛️ Gatehouse Audit Report",
            f"**Status:** {status}  ",
            f"**Aikaleima:** {ts}\n",
            "| Tarkistuskohde | Havaittu arvo | Tila |",
            "| :--- | :--- | :--- |",
            f"| Riskiluokka | {self.results.get('Riskiluokka', 'Ei löydy')} | {'✅' if self.results.get('Riskiluokka') else '❌'} |",
            f"| Rollback-suunnitelma | {self.results.get('Rollback')} | {'✅' if self.results.get('Rollback') == 'Löytyy' else '❌'} |",
        ]
        if self.errors:
            md.append("\n### ⚠️ Huomiot:")
            for err in self.errors: md.append(f"- {err}")
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f: f.write("\n".join(md))

def main():
    if len(sys.argv) < 2: sys.exit(1)
    file_to_check = sys.argv[1]
    
    with open(file_to_check, 'r', encoding='utf-8') as f:
        content = f.read()
    
    engine = GatehouseEngine(content)
    passed = engine.validate()
    engine.generate_report("evidence/compliance-reports/report.md")
    
    output = {
        "passed": passed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file": file_to_check,
        "findings": engine.results,
        "errors": engine.errors
    }
    print(json.dumps(output, indent=2))
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
