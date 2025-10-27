<!-- d6c9741d-fd01-4531-98ef-fbe6e6ff1361 715be11f-1896-4d30-bf72-5bd54bae5bd2 -->
# Finalize Smoke Test Documentation for v0.9.0

## Overview

Document the successful completion of 29 smoke test checks (28 PASS, 1 expected SKIP) and prepare BrokerCursor v0.9.0 for release by updating documentation and CI integration.

## Current State Analysis

- Smoke test script: `core/scripts/verify/smoke_test.py` with 29 comprehensive checks
- Test report: `diagnostics/smoke_test_report.md` shows 100% success rate (28/28 functional checks)
- No CHANGELOG.md exists yet
- No CI/CD workflows configured
- README.md structure: "CLI команды" section ends at line 282, "Утилиты" subsection ends at line 294, "Диагностика и верификация" starts at line 296
- No `pyproject.toml` or core-level `__init__.py` with version info

## Changes Required

### 1. Update README.md

**Место вставки:** после подраздела "Утилиты" (строка 294), перед разделом "Диагностика и верификация" (строка 296)

Добавить новый раздел `## Smoke Test`:

- Total checks: 29 (28 PASS + 1 SKIP)
- Purpose: DB consistency, parsed data validation, CLI commands, audit logs, new data stability, SQL queries
- Command: `python core/scripts/verify/smoke_test.py`
- Features: idempotent, SKIP statuses for expected behaviors, CI-ready
- Report location: `diagnostics/smoke_test_report.md`
- Expected report structure: timestamp, summary (total/passed/failed), detailed results by section, recommendations

**Обновить версию в конце файла:**

- Изменить `**Версия:** 1.0.0` на `**Версия:** 0.9.0` (строка 515)
- Изменить `**Обновлено:** 2025-10-23` на `**Обновлено:** 2025-10-24` (строка 517)

### 2. Create CHANGELOG.md

New file in project root with v0.9.0 entry:

- Date: 2025-10-24
- Smoke test: 29/29 checks (28 PASS, 1 expected SKIP)
- Idempotent design with SKIP status handling
- Parser improvements: `trade_count` field, enhanced JSON structure
- Windows CLI compatibility: UTF-8 encoding, ruble symbol support
- DB operations: `update_report_parsed_data()` method
- Report versioning: `smoke_test_report_<timestamp>.md` format

**Format:** Follow Keep a Changelog standard (UTF-8, LF, markdown structure)

**Note:** No `pyproject.toml` exists, version managed only in README.md and CHANGELOG.md

### 3. Create CI Workflow Template

Generate `.github/workflows/smoke-test.yml`:

- **Cross-platform:** matrix strategy for `ubuntu-latest` and `windows-latest`
- Trigger: on push to main, pull requests
- Setup Python 3.11
- PostgreSQL: service container (Linux) or setup action (Windows)
- Install dependencies: `pip install -r requirements.txt`
- Configure `.env` with test DB credentials
- Run: `python core/scripts/verify/smoke_test.py`
- Upload: `diagnostics/smoke_test_report.md` as artifact (always, even on failure)
- Exit code: fail build if smoke test returns non-zero

## Output Artifacts

- Updated `README.md` with Smoke Test section (after Утилиты, before Диагностика)
- New `CHANGELOG.md` with v0.9.0 milestone
- New `.github/workflows/smoke-test.yml` for CI/CD integration
- Structured smoke test report format documented: header, summary table, results by category, recommendations

## Success Criteria

- README includes comprehensive smoke test documentation at correct location
- Version updated to 0.9.0 in README.md
- CHANGELOG captures v0.9.0 milestone following standard format
- CI workflow template supports both Windows and Linux runners
- All documentation follows project markdown standards (UTF-8, LF, no emojis in body text)

### To-dos

- [ ] Add Smoke Test section to README.md after CLI Commands section
- [ ] Create CHANGELOG.md with v0.9.0 release notes
- [ ] Generate GitHub Actions workflow template for smoke test automation