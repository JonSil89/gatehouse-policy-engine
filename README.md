# Gatehouse Policy Engine

Policy validation engine & approval gates for infrastructure changes.

## Purpose
This repository implements a formal change management process for critical infrastructure. The system is based on ISO 27001 change management controls and provides an automated quality gate that ensures the quality, security, and traceability of every infrastructure change.

## Architecture
Developer → PR + change request → Automated validation → Review → Deployment condition → Merge
                                      │                        │              │
                                 GATE 1                   GATE 2         GATE 3
                              (CI/CD script)         (review policy)   (time windows)

### Three Quality Gates
1. **Automated validation (CI/CD)** — Python script checks change request structure, risk level, rollback plan, and freeze windows
2. **Manual review** — Number of reviewers based on risk level (1-3 persons)
3. **Deployment condition** — Time window check, staging validation, communication plan for critical changes

### Risk Classes
| Class | Level | Approvers | Examples |
|-------|-------|-----------|----------|
| 1 | Low | 1 | Documentation, minor configurations |
| 2 | Medium | 2 | Infrastructure config, CI/CD changes, access management |
| 3 | Critical | 3 + CISO | Network architecture, database migrations, security |

## ISO 27001 Mapping
- **A.12.1.2 Change Management** — Changes are documented, classified, and approved
- **A.14.2.2 System Change Control** — Formal, auditable change process
- **A.12.4.1 Event Logging** — Automated audit trail via CI/CD

## Repository Structure
├── .github/workflows/         # CI/CD quality gate
├── docs/                      # Risk classification and change classification
│   ├── risk-matrix.md
│   └── change-classification.md
├── templates/                 # Change request and rollback templates
│   ├── change-request-template.md
│   └── rollback-plan-template.md
├── validation/                # Automated validation script
│   └── pre-merge-checks/
│       └── validate-change-request.py
└── examples/                  # Pre-filled examples (in demo branch)

## Getting Started
1. Copy `templates/change-request-template.md` to PR description
2. Fill in all required fields
3. CI/CD runs automated validation
4. Request review according to risk level
5. Merge only after passing all gates

## Branch Strategy
- `main` — Protected production branch, direct pushes blocked
- `develop` — Active development branch
- `demo/leadership-demo` — Pre-filled examples for leadership demonstration

## License
MIT License. See `LICENSE` file for details.

---
<div align="center">

## 🔗 Part of [Gatehouse Infrastructure](https://github.com/JonSil89)

| Repository | Description |
|------------|-------------|
| [🔧 **AI-ITSM-Compliance-Auto**](https://github.com/JonSil89/AI-ITSM-Compliance-Auto) | Intelligent workflow orchestration |
| [🏠 **HAaaS**](https://github.com/JonSil89/Home-Assistant-as-a-Service-HAaaS-) | IoT lifecycle management platform |

</div>
