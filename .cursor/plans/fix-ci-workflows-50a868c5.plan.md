<!-- 50a868c5-be08-4bf6-b268-698f7d6615f0 eb3182a9-b9df-498d-abe6-634b9ccfcc8f -->
# Enable Branch Protection and CI/CD Enhancements

## Phase 1: Automated Branch Protection Script

Создать скрипт для автоматического мониторинга и включения branch protection:

```python
core/scripts/ci/enable_branch_protection.py
```

Функционал:

- Проверка статуса всех 5 workflows через GitHub API
- Ожидание успешного завершения (с таймаутом)
- Автоматическое включение branch protection
- Верификация настроек

## Phase 2: CODEOWNERS Configuration

Создать `.github/CODEOWNERS`:

```
# Core architecture and database
/core/ @proektor1001
/core/database/ @proektor1001
/core/parsers/ @proektor1001

# CI/CD and workflows
/.github/ @proektor1001
/Makefile @proektor1001

# Configuration
*.yml @proektor1001
*.yaml @proektor1001
.env.example @proektor1001
pyproject.toml @proektor1001
requirements.txt @proektor1001
```

Обоснование: централизованная ответственность на начальной фазе проекта

## Phase 3: GitHub Secrets Setup

Создать скрипт для настройки GitHub Secrets:

```python
core/scripts/ci/setup_github_secrets.py
```

Функционал:

- Чтение GITHUB_PAT из .env
- Загрузка в GitHub Secrets через API
- Проверка доступности секретов для workflows
- Сохранение GITHUB_PAT в .env (не удалять)

## Phase 4: Pre-commit Hooks (Optional)

Создать `.pre-commit-config.yaml`:

- black (code formatting)
- flake8 (linting)
- isort (import sorting)
- end-of-file-fixer
- trailing-whitespace
- check-yaml

Создать workflow `.github/workflows/pre-commit.yml` для CI

## Phase 5: Semantic Release (Optional)

Оценить целесообразность:

- Проект на этапе v0.9.x
- Уже есть VERSION.txt и CHANGELOG.md
- semantic-release добавит автоматизацию версионирования

Рекомендация: отложить до v1.0.0, когда API стабилизируется

## Success Criteria

- Branch protection включен автоматически после успешных workflows
- CODEOWNERS настроен для критических директорий
- GITHUB_PAT доступен в GitHub Secrets
- Pre-commit hooks работают локально и в CI
- Документация обновлена с новыми процессами

## Implementation Order

1. Create automated branch protection script
2. Set up CODEOWNERS
3. Configure GitHub Secrets automation
4. Add pre-commit hooks (if appropriate)
5. Update documentation
6. Test full CI/CD pipeline

### To-dos

- [ ] Create automated branch protection monitoring and enablement script
- [ ] Create .github/CODEOWNERS with responsibility zones
- [ ] Create script to sync GITHUB_PAT to GitHub Secrets
- [ ] Add .pre-commit-config.yaml and pre-commit.yml workflow
- [ ] Update README and docs with new CI/CD processes
- [ ] Test complete CI/CD pipeline end-to-end