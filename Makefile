# BrokerCursor Makefile
# Standard CLI shortcuts for project management

.PHONY: help setup init-db migrate import verify stats clean smoke-test sync-external verify-duplicates test-duplicates reorganize-archive lint format typecheck security-scan test test-coverage lint-docs check-deps

help:
	@echo "BrokerCursor - Available Commands:"
	@echo "  setup     - Install dependencies and initialize database"
	@echo "  init-db   - Initialize database schema"
	@echo "  migrate   - Run database migration for multi-broker support"
	@echo "  import    - Import reports from inbox directory"
	@echo "  verify    - Run all verification scripts"
	@echo "  smoke-test - Run comprehensive smoke test validation"
	@echo "  stats     - Show database statistics"
	@echo "  clean     - Remove Python cache files"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  lint      - Run code quality checks (flake8, black, isort)"
	@echo "  format    - Auto-format code (black, isort)"
	@echo "  typecheck - Run type checking (mypy)"
	@echo ""
	@echo "Security Commands:"
	@echo "  security-scan - Run security scans (pip-audit, bandit)"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test         - Run unit tests"
	@echo "  test-coverage - Run tests with coverage report"
	@echo ""
	@echo "Documentation Commands:"
	@echo "  lint-docs - Lint markdown documentation"
	@echo ""
	@echo "Dependency Commands:"
	@echo "  check-deps - Check for unused dependencies"
	@echo ""
	@echo "Duplicate Protection Commands:"
	@echo "  sync-external     - Sync files from external directory to inbox"
	@echo "  verify-duplicates - Verify semantic duplicates in parsed_data"
	@echo "  test-duplicates   - Test duplicate protection functionality"
	@echo "  reorganize-archive - Move existing files to new archive structure"

setup: init-db
	pip install -r requirements.txt

init-db:
	python core/scripts/init_db.py

migrate:
	python core/scripts/migrate_db.py

import:
	python core/scripts/import/import_reports.py

verify:
	python core/scripts/verify/verify_setup.py
	python core/scripts/verify/verify_import.py
	python core/scripts/verify/verify_db_integrity.py
	python core/scripts/verify/verify_report_data.py

stats:
	python core/scripts/import/import_reports.py --stats

smoke-test:
	python core/scripts/verify/smoke_test.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "*.pyd" -delete

# Duplicate Protection Commands
sync-external:
	@echo "Syncing external directory to inbox..."
	@echo "Usage: make sync-external SOURCE=/path/to/external/directory"
	@echo "Example: make sync-external SOURCE='D:/1-ФИНАНСЫ Ми/База знаний - Инвест Аналитик/Отчёты брокера оригинал'"
	@if [ -z "$(SOURCE)" ]; then \
		echo "Error: SOURCE parameter required"; \
		echo "Usage: make sync-external SOURCE=/path/to/external/directory"; \
		exit 1; \
	fi
	python core/scripts/import/sync_external_reports.py --source "$(SOURCE)"

verify-duplicates:
	@echo "Verifying semantic duplicates in parsed_data..."
	python core/scripts/verify/verify_semantic_duplicates.py

test-duplicates:
	@echo "Testing duplicate protection functionality..."
	python core/scripts/verify/test_duplicate_protection.py

reorganize-archive:
	@echo "Reorganizing existing archive files..."
	python core/scripts/import/reorganize_archive.py

fetch-summary:
	@echo "Fetching broker report summary..."
	python core/scripts/query/fetch_summary.py

fix-periods:
	@echo "Fixing invalid period values..."
	python core/scripts/verify/fix_invalid_periods.py

query-portfolio:
	@echo "Fetching current portfolio from database..."
	python core/scripts/query/fetch_portfolio.py

reparse-sber-portfolio:
	@echo "Reparsing Sber reports to fix securities_portfolio..."
	python core/scripts/parse/reparse_sber_reports.py

# Code Quality Commands
lint:
	@echo "Running code quality checks..."
	flake8 core/ tests/
	black --check core/ tests/
	isort --check core/ tests/

format:
	@echo "Formatting code..."
	black core/ tests/
	isort core/ tests/

typecheck:
	@echo "Running type checks..."
	mypy core/ --ignore-missing-imports

# Security Commands
security-scan:
	@echo "Running security scans..."
	pip-audit
	bandit -r core/ -ll

# Testing Commands
test:
	@echo "Running unit tests..."
	pytest tests/

test-coverage:
	@echo "Running tests with coverage..."
	pytest --cov=core --cov-report=html --cov-report=term tests/

# Documentation Commands
lint-docs:
	@echo "Linting documentation..."
	npx markdownlint-cli2 "**/*.md" "!node_modules" "!diagnostics"

# Dependency Commands
check-deps:
	@echo "Checking dependencies..."
	pip-check