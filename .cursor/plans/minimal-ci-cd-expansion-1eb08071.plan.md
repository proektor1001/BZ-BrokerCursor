<!-- 1eb08071-eaa6-4325-8e3c-5d34f769263d 5028614d-1e0f-4387-bcf2-4e7d99a07d4f -->
# Minimal CI/CD Expansion Plan for BrokerCursor

## Current State Analysis

### Existing Infrastructure

- **Single workflow**: `smoke-test.yml` - comprehensive smoke testing on Ubuntu and Windows with PostgreSQL
- **Makefile commands**: 13 commands including `verify`, `import`, `smoke-test`, `clean`
- **Test framework**: `unittest` (standard library) with 2 test files in `tests/`
- **No linters/formatters**: requirements.txt contains no code quality tools (flake8, black, mypy, etc.)
- **No pre-commit hooks**: no `.pre-commit-config.yaml`
- **Database-centric**: PostgreSQL + JSONB architecture with strong focus on data integrity

### Strengths

- Multi-platform testing (Ubuntu + Windows)
- PostgreSQL service integration
- Artifact upload for diagnostics
- Comprehensive verification scripts in `core/scripts/verify/`

### Gaps

- No code quality checks (linting, formatting, type checking)
- No security scanning (dependencies, secrets)
- No requirements.txt validation
- No documentation validation
- Limited unit test coverage

## Proposed CI/CD Components (Priority Order)

### 1. Code Quality Workflow (HIGH PRIORITY)

**File**: `.github/workflows/code-quality.yml`

**Purpose**: Automated code quality checks on every PR and push

**Components**:

- `flake8` - PEP 8 linting with project-specific rules
- `black` - code formatting verification (check mode)
- `isort` - import sorting verification
- `mypy` - static type checking (basic configuration)

**Risk**: Low | **Effort**: Low | **Value**: High

**Why first**: Catches syntax errors, style issues, and basic type errors before smoke tests run, saving CI time and improving code consistency.

### 2. Security Scanning Workflow (HIGH PRIORITY)

**File**: `.github/workflows/security.yml`

**Purpose**: Dependency vulnerability scanning and secret detection

**Components**:

- `pip-audit` - scan requirements.txt for known vulnerabilities
- `bandit` - security linting for Python code
- `trufflehog` or `gitleaks` - secret scanning in commits (optional)

**Risk**: Low | **Effort**: Low | **Value**: High

**Why second**: Critical for production readiness; detects vulnerable dependencies and potential security issues without breaking existing workflows.

### 3. Unit Tests Workflow (MEDIUM PRIORITY)

**File**: `.github/workflows/unit-tests.yml`

**Purpose**: Fast unit tests without database (separate from smoke-test)

**Components**:

- `pytest` - modern test runner with better output
- Coverage reporting with `pytest-cov`
- Run only unit tests (mocked database)
- Faster feedback loop (~30s vs 5min for smoke-test)

**Risk**: Low | **Effort**: Medium | **Value**: Medium

**Why third**: Provides fast feedback for basic logic errors; complements existing smoke-test.yml which tests full integration.

### 4. Documentation Validation (MEDIUM PRIORITY)

**File**: `.github/workflows/docs-validation.yml`

**Purpose**: Ensure documentation follows project standards

**Components**:

- Markdown linting (`markdownlint-cli2`)
- Check `.md` files follow `markdown_writing_standard` rules
- Verify encoding (UTF-8 without BOM)
- Verify line endings (LF only)
- Check max line length (80 chars)

**Risk**: Very Low | **Effort**: Low | **Value**: Medium

**Why fourth**: Enforces documentation standards from user rules; prevents technical debt in docs.

### 5. Dependency Management (LOW PRIORITY)

**File**: `.github/workflows/dependency-check.yml`

**Purpose**: Validate and maintain requirements.txt

**Components**:

- Verify `requirements.txt` is sorted
- Check for pinned versions (security best practice)
- Detect unused dependencies (using `pip-check`)
- Weekly scheduled run to detect outdated packages

**Risk**: Very Low | **Effort**: Low | **Value**: Low

**Why fifth**: Nice-to-have; helps maintain clean dependencies but not critical for immediate needs.

## Implementation Recommendations

### Phase 1: Foundation (Week 1)

1. Add code quality tools to `requirements.txt`: `flake8`, `black`, `isort`, `mypy`
2. Create `.flake8` configuration file with project rules
3. Create `pyproject.toml` for `black` and `isort` settings
4. Implement `code-quality.yml` workflow with pip caching
5. Add `make lint` and `make format` commands to Makefile
6. Add pre-check script for forbidden files (`.env`, `.sqlite`, `*.log`, `*.db`)

### Phase 2: Security (Week 2)

1. Add security tools to `requirements.txt`: `pip-audit`, `bandit`
2. Create `.bandit` configuration (exclude tests/, diagnostics/)
3. Implement `security.yml` workflow
4. Add `make security-scan` command to Makefile

### Phase 3: Testing Enhancement (Week 3)

1. Add `pytest` and `pytest-cov` to `requirements.txt`
2. Create `pytest.ini` configuration
3. Implement `unit-tests.yml` workflow
4. Add `make test` and `make test-coverage` commands to Makefile
5. Convert existing unittest tests to pytest (optional)

### Phase 4: Documentation (Week 4)

1. Add `markdownlint-cli2` (npm-based) to workflow directly
2. Create `.markdownlint.json` configuration
3. Implement `docs-validation.yml` workflow
4. Add `make lint-docs` command to Makefile

### Phase 5: Dependency Management (Optional)

1. Add `pip-check` to requirements.txt
2. Implement `dependency-check.yml` with weekly schedule
3. Add `make check-deps` command to Makefile

## Configuration Files Needed

### `.flake8`

```ini
[flake8]
max-line-length = 100
exclude = .git,__pycache__,build,dist,.venv,venv,diagnostics
ignore = E203,W503
per-file-ignores = __init__.py:F401
```

### `pyproject.toml`

```toml
[tool.black]
line-length = 100
target-version = ['py311']
exclude = '/(\.git|\.venv|venv|build|dist|__pycache__|diagnostics)/'

[tool.isort]
profile = "black"
line_length = 100
skip_gitignore = true
```

### `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
```

### `.markdownlint.json`

```json
{
  "line-length": {"line_length": 80, "code_blocks": false},
  "no-duplicate-heading": true,
  "no-trailing-punctuation": false,
  "no-inline-html": false
}
```

## Makefile Extensions

```makefile
# Code Quality
lint:
	flake8 core/ tests/
	black --check core/ tests/
	isort --check core/ tests/

format:
	black core/ tests/
	isort core/ tests/

typecheck:
	mypy core/ --ignore-missing-imports

# Security
security-scan:
	pip-audit
	bandit -r core/ -ll

# Testing
test:
	pytest tests/

test-coverage:
	pytest --cov=core --cov-report=html --cov-report=term tests/

# Documentation
lint-docs:
	npx markdownlint-cli2 "**/*.md" "!node_modules" "!diagnostics"

# Dependencies
check-deps:
	pip-check
```

## Success Metrics

### Code Quality

- All PRs pass linting before merge
- Code formatting is consistent across project
- Type hints coverage increases over time

### Security

- Zero high/critical vulnerabilities in dependencies
- No secrets committed to repository
- Security issues detected before production

### Testing

- Unit test coverage >70% for core modules
- Fast feedback (<2 min for unit tests)
- Smoke tests remain comprehensive (current state)

### Documentation

- All `.md` files follow standards
- Consistent formatting across docs
- UTF-8 LF encoding enforced

## Risk Mitigation

### Potential Issues

1. **CI time increase**: Mitigated by parallel job execution
2. **False positives**: Use project-specific configurations
3. **Developer friction**: Add `make format` for auto-fixing
4. **Breaking existing code**: Run locally first, fix issues before enabling

### Rollback Plan

- Each workflow can be disabled independently
- No changes to existing `smoke-test.yml`
- All tools optional in local development

## Cost Analysis

### Time Investment

- Setup: ~8-16 hours total
- Maintenance: ~1-2 hours/month
- Developer impact: +30s per commit (auto-fixable)

### CI Minutes

- Current: ~10 min/run (smoke-test only)
- After expansion: ~15 min/run (all workflows)
- GitHub Free: 2000 min/month (enough for ~130 runs)

### Value

- Reduced bugs in production
- Consistent code quality
- Better security posture
- Easier onboarding for new developers

## Excluded (Out of Scope)

- Deployment automation
- Release automation
- Docker image building
- Performance testing
- Integration testing (covered by smoke-test)
- End-to-end testing
- Visual regression testing
- Chaos engineering

## Next Steps

1. Review plan with team
2. Create GitHub issues for each phase
3. Implement Phase 1 (code quality)
4. Iterate based on feedback
5. Gradually enable stricter rules

## Notes

- All workflows should have `pull_request` and `push` triggers
- Use matrix strategy for multi-Python version testing if needed
- Cache pip dependencies to speed up workflows
- Use `actions/cache@v4` for dependency caching
- Consider branch protection rules after workflows are stable

### To-dos

- [ ] Analyze existing CI/CD infrastructure (.github/workflows/, Makefile, requirements.txt)
- [ ] Create minimal_ci_expansion_plan.md in diagnostics/ with priority-ordered components
- [ ] Define required configuration files (.flake8, pyproject.toml, pytest.ini, .markdownlint.json)
- [ ] Document 5-phase implementation strategy with timeline and dependencies