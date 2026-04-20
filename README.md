<div align="center">

# 🏛️ Gatehouse Policy Engine

**Policy validation engine & approval gates for infrastructure changes**

[![ISO 27001](https://img.shields.io/badge/ISO%2027001-Ready-blue)](https://www.iso.org/standard/27001)
[![Core](https://img.shields.io/badge/Gatehouse-Core-purple)](#)
[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-yellow)](validation/)


[![🏛️ Gatehouse Compliance Check](https://github.com/JonSil89/gatehouse-policy-engine/actions/workflows/compliance-check.yml/badge.svg)](https://github.com/JonSil89/gatehouse-policy-engine/actions/workflows/compliance-check.yml)
[![Infrastructure Change Quality Qate](https://github.com/JonSil89/gatehouse-policy-engine/actions/workflows/compliance-check.yml/badge.svg)](https://github.com/JonSil89/gatehouse-policy-engine/actions/workflows/compliance-check.yml)

</div>

---

## 📋 Purpose

This repository implements a **formal change management process for critical infrastructure**. The system is based on ISO 27001 change management controls and provides an automated quality gate that ensures the quality, security, and traceability of every infrastructure change.

---

## 🏗️ Architecture


```mermaid
flowchart LR
    A[Developer] --> B[PR + Change Request]
    B --> C{GATE 1\nAutomated Validation\nCI/CD Script}
    C -->|Pass| D{GATE 2\nManual Review\nReview Policy}
    C -->|Fail| X[❌ Rejected]
    D -->|Approved| E{GATE 3\nDeployment Condition\nTime Windows}
    D -->|Rejected| X
    E -->|Clear| F[✅ Merge]
    E -->|Blocked| Y[⏸ Postponed]
```



### Three Quality Gates

| Gate | Name | Description |
|------|------|-------------|
| **1** | **Automated validation (CI/CD)** | Python script checks change request structure, risk level, rollback plan, and freeze windows |
| **2** | **Manual review** | Number of reviewers based on risk level (1-3 persons) |
| **3** | **Deployment condition** | Time window check, staging validation, communication plan for critical changes |

---

## ⚠️ Risk Classes

| Class | Level | Approvers | Examples |
|:-----:|-------|-----------|----------|
| **1** | Low | 1 | Documentation, minor configurations |
| **2** | Medium | 2 | Infrastructure config, CI/CD changes, access management |
| **3** | Critical | 3 + CISO | Network architecture, database migrations, security |

---

## 🔒 ISO 27001 Mapping

| Control | Description |
|---------|-------------|
| **A.12.1.2** | **Change Management** — Changes are documented, classified, and approved |
| **A.14.2.2** | **System Change Control** — Formal, auditable change process |
| **A.12.4.1** | **Event Logging** — Automated audit trail via CI/CD |

---




## 📁 Repository Structure


---
```
. 
├── .github/workflows/          # CI/CD quality gate
├── docs/                       # Risk classification
│   ├── risk-matrix.md
│   └── change-classification.md
├── templates/                  # Change request templates
│   ├── change-request-template.md
│   └── rollback-plan-template.md
├── validation/                 # Automated validation script
│   └── pre-merge-checks/
│       └── validate-change-request.py
└── examples/                   # Pre-filled examples
```

---


---

## 🚀 Getting Started

1. **Copy** `templates/change-request-template.md` to PR description
2. **Fill** in all required fields
3. **CI/CD** runs automated validation
4. **Request review** according to risk level
5. **Merge** only after passing all gates

---
## 🧪 Quick Demo — Run the Quality Gate Locally

Test the policy engine in under 2 minutes on your local machine.

### Prerequisites
- Python 3.8+
- Git
- Bash or Git Bash (Windows)

### Run it

**1. Clone and enter the repo**
```bash
git clone https://github.com/JonSil89/gatehouse-policy-engine.git
cd gatehouse-policy-engine
```

**2. Test a valid Class 2 change request (should PASS)**
```bash
python3 validation/pre-merge-checks/validate-change-request.py \
  examples/example-class2-cicd-pipeline-update.md
```
**3. Test a valid Class 3 change request (should PASS)**
```bash
python3 validation/pre-merge-checks/validate-change-request.py \
 examples/example-class3-production-network-change.md
```
Expected output: `QUALITY GATE: PASSED`

**4. Test an invalid request (should FAIL)**
```bash
echo "# Empty request" > /tmp/test-fail.md
python3 validation/pre-merge-checks/validate-change-request.py \
  /tmp/test-fail.md
```

Expected output: `QUALITY GATE: FAILED`

**5. Clean up**
```bash
cd / && rm -rf /tmp/gate_test
```

### What the validator checks
- ✅ Required sections present (Perustiedot, Kuvaus, Vaikutusanalyysi)
- ✅ All mandatory fields filled
- ✅ Risk class defined and justified (1-3)
- ✅ Rollback plan present (Class 2-3)
- ✅ Sufficient approvers named (1-3 based on risk)
- ✅ Test plan present (Class 2-3)
- ✅ Freeze period checked (Class 3)
- ✅ JSON output for CI/CD integration
---

## 🌿 Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Protected production branch, direct pushes blocked |
| `develop` | Active development branch |
| `demo/leadership-demo` | Pre-filled examples for leadership demonstration |

---

## 📜 License

MIT License. See [LICENSE](LICENSE) file for details.

---

<div align="center">

## 🔗 Part of [Gatehouse Infrastructure](https://github.com/JonSil89)

| Repository | Description |
|------------|-------------|
| [🔧 **AI-ITSM-Compliance-Auto**](https://github.com/JonSil89/AI-ITSM-Compliance-Auto) | Intelligent workflow orchestration |
| [🏠 **HAaaS**](https://github.com/JonSil89/Home-Assistant-as-a-Service-HAaaS-) | IoT lifecycle management platform |

</div>
