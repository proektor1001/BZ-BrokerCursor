<!-- 7bed7a87-7d60-4da0-81ce-ca5afb8ae548 f88474d2-b917-4d46-86d7-c204d215e4ef -->
# GitHub Infrastructure Security Setup

## Objective

Maximize the effectiveness of the existing `GITHUB_PAT` token to complete secure GitHub infrastructure configuration for the BZ-BrokerCursor project.

## Implementation Steps

### 1. Enable Branch Protection Rules

Configure branch protection for `main` branch via GitHub API:

**Settings:**

- Require pull request reviews before merging
- Require status checks to pass before merging
- **Status checks to require (all must pass):**
                - `code-quality`
                - `security-scan`
                - `unit-tests`
                - `docs-validation`
                - `dependency-check`
- Require branches to be up to date before merging
- Include administrators (optional)
- Restrict direct pushes to main

**API endpoint:** `PATCH /repos/proektor1001/BZ-BrokerCursor/branches/main/protection`

**Benefits:**

- Prevents accidental direct commits to main
- Enforces code review process
- Ensures all CI checks pass before merge
- Maintains code quality standards

### 2. Add Status Badges to README

Update `README.md` with workflow status badges:

```markdown
[![Code Quality](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/code-quality.yml/badge.svg)](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/code-quality.yml)
[![Security Scanning](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/security.yml/badge.svg)](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/security.yml)
[![Unit Tests](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/unit-tests.yml)
[![Docs Validation](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/docs-validation.yml/badge.svg)](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/docs-validation.yml)
[![Dependency Check](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/dependency-check.yml/badge.svg)](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/dependency-check.yml)
```

**Location:** Insert after project title in `README.md` (line 1-2)

### 3. Configure Dependabot

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
    open-pull-requests-limit: 5
    reviewers:
      - "proektor1001"
    labels:
      - "dependencies"
      - "python"
    commit-message:
      prefix: "deps"
      include: "scope"
  
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
    open-pull-requests-limit: 3
    reviewers:
      - "proektor1001"
    labels:
      - "dependencies"
      - "github-actions"
    commit-message:
      prefix: "ci"
      include: "scope"
```

**Benefits:**

- Automatic security vulnerability detection
- Weekly dependency update PRs
- GitHub Actions workflow updates
- Automatic labeling and assignment

### 4. Update .env.example

Add `GITHUB_PAT` placeholder to `.env.example` (if not already present):

```env
# GitHub Configuration (optional, for CI/CD integrations)
GITHUB_PAT=your_github_personal_access_token_here
```

**Note:** Ensure actual token remains ONLY in `.env` (already in .gitignore)

## Key Files to Modify

- `README.md` - Add badges after line 1
- `.github/dependabot.yml` - New file
- `.env.example` - Add GITHUB_PAT documentation (if needed)

## Security Considerations

- `GITHUB_PAT` token already stored in `.env` (gitignored)
- Token has 90-day expiration policy
- Branch protection prevents unauthorized changes
- All changes via API or configuration files (no manual web console)

## Verification Steps

After implementation:

1. Verify branch protection via API: `GET /repos/proektor1001/BZ-BrokerCursor/branches/main/protection`
2. Check badges render correctly in GitHub UI
3. Verify Dependabot creates initial scan
4. Confirm no secrets committed to repository

## Expected Outcome

- Protected main branch requiring PR + passing CI
- Real-time CI status visibility via badges
- Automated weekly dependency monitoring
- Enhanced security posture without manual intervention

### To-dos

- [ ] Enable branch protection rules for main branch via GitHub API
- [ ] Add GitHub Actions status badges to README.md
- [ ] Create .github/dependabot.yml for automated dependency monitoring
- [ ] Verify all configurations and ensure no secrets are exposed