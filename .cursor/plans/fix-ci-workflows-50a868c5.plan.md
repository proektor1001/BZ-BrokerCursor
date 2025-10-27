<!-- 50a868c5-be08-4bf6-b268-698f7d6615f0 51889e41-1ef4-43d8-a86a-84a02b6b56cc -->
# Fix CI/CD Workflows for Branch Protection

## Identified Issues

### 1. Code Quality Workflow

- Missing tools in requirements.txt (flake8, black, isort, mypy)
- Git diff comparison fails on push to main (no origin/main...HEAD)
- Potential formatting issues in Python files

### 2. Security Workflow

- Missing tools in requirements.txt (pip-audit, bandit)
- Same git diff issue as code-quality
- May need .bandit configuration adjustments

### 3. Unit Tests Workflow

- Missing pytest and pytest-cov installation validation
- No test discovery validation

### 4. Docs Validation Workflow

- markdownlint-cli2 command syntax may need adjustment
- File encoding check uses 'file' command (not available on all runners)
- May fail on Windows line endings in existing files

### 5. Dependency Check Workflow

- Missing pip-check tool in requirements.txt
- requirements.txt may not be sorted correctly
- Only runs on schedule/manual, needs trigger on push/PR

## Fix Strategy

### Phase 1: Update requirements.txt

Add all missing CI/CD tools with pinned versions and sort alphabetically

### Phase 2: Fix Git Diff Logic

Add robust protection for first commit scenarios and missing origin/main:

```yaml
- name: Check for forbidden files
  run: |
    echo "Checking for forbidden files..."
    if git rev-parse --verify origin/main >/dev/null 2>&1; then
      CHANGED_FILES=$(git diff --name-only origin/main...HEAD)
    else
      CHANGED_FILES=$(git diff --name-only HEAD~1 2>/dev/null || echo "")
    fi
    if echo "$CHANGED_FILES" | grep -E '\.env$|\.sqlite|\.log|\.db$'; then
      echo "❌ Forbidden files detected!"
      exit 1
    else
      echo "✅ No forbidden files"
    fi
```

### Phase 3: Fix Documentation Validation

- Create `.markdownlint-cli2.jsonc` configuration
- Install `markdownlint-cli2` explicitly via `npm install -g` (not npx)
- Replace `file` command with Python-based encoding check using chardet or portable iconv
- Update glob pattern to properly exclude diagnostics

### Phase 4: Fix Dependency Check

- Add pip-check to requirements.txt with pinned version
- Sort requirements.txt alphabetically
- Add duplicate detection check in workflow
- Add push/PR triggers (not only schedule)
- Implement pip cache via `actions/cache@v4`

### Phase 5: Pre-commit Hook Validation (Optional)

- Create `.pre-commit-config.yaml` with hooks: black, flake8, mypy, end-of-file-fixer, check-yaml
- Create separate workflow `.github/workflows/pre-commit.yml`
- Run `pre-commit run --all-files` in CI

### Phase 6: Test and Enable Branch Protection

- Commit all fixes to trigger workflows
- Verify all 5 workflows pass on push and PR
- Confirm forbidden file check works correctly
- Use GitHub API `PATCH /repos/.../branches/main/protection` to enable required_status_checks
- Verify with `GET /repos/.../branches/main/protection`

## Files to Modify

- `requirements.txt` - add missing tools, sort entries, remove duplicates
- `.github/workflows/code-quality.yml` - fix git diff logic, add caching
- `.github/workflows/security.yml` - fix git diff logic, add caching
- `.github/workflows/docs-validation.yml` - fix file encoding check, explicit npm install
- `.github/workflows/dependency-check.yml` - add triggers, duplicate check, caching
- `.markdownlint-cli2.jsonc` - create proper configuration
- `.pre-commit-config.yaml` - optional, create pre-commit configuration
- `.github/workflows/pre-commit.yml` - optional, create pre-commit workflow

## Success Criteria

- All 5 workflows execute on both push and PR
- Forbidden file check passes successfully (no .env, *.db, etc in commits)
- All workflows show green status on GitHub Actions
- GitHub registers all 5 status check contexts
- `GET /branches/main/protection` returns required_status_checks after activation
- Branch protection can be enabled via API with all 5 required checks

### To-dos

- [ ] Update requirements.txt with all CI tools and sort entries
- [ ] Fix git diff logic in code-quality.yml workflow
- [ ] Fix git diff logic in security.yml workflow
- [ ] Fix file encoding check and markdownlint config in docs-validation.yml
- [ ] Add triggers and fix requirements.txt validation in dependency-check.yml
- [ ] Create .markdownlint-cli2.jsonc configuration file
- [ ] Commit changes and verify all workflows pass