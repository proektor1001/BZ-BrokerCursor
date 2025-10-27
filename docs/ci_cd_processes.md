# CI/CD и DevOps Процессы

## Обзор

BrokerCursor использует современную систему CI/CD с автоматизированными проверками качества кода, безопасности и развертывания.

## GitHub Actions Workflows

### 1. Code Quality (`code-quality.yml`)
**Назначение:** Проверка качества и форматирования кода

**Проверки:**
- `black` — форматирование кода (line-length=100)
- `flake8` — линтинг (max-line-length=100, ignore=E203,W503)
- `isort` — сортировка импортов (profile=black)
- `mypy` — проверка типов (--ignore-missing-imports)
- Проверка запрещенных файлов (.env, *.db, *.log, *.sqlite)

**Триггеры:** push, pull_request на main/master

### 2. Security Scan (`security.yml`)
**Назначение:** Анализ безопасности зависимостей и кода

**Проверки:**
- `pip-audit` — проверка уязвимостей в зависимостях
- `bandit` — статический анализ безопасности Python кода
- Проверка запрещенных файлов

**Триггеры:** push, pull_request на main/master

### 3. Unit Tests (`unit-tests.yml`)
**Назначение:** Запуск тестов с измерением покрытия

**Проверки:**
- `pytest` — запуск тестов
- `pytest-cov` — измерение покрытия кода
- Загрузка покрытия в Codecov

**Триггеры:** push, pull_request на main/master

### 4. Documentation Validation (`docs-validation.yml`)
**Назначение:** Проверка качества документации

**Проверки:**
- `markdownlint-cli2` — линтинг Markdown файлов
- Проверка кодировки UTF-8 и окончаний строк LF
- Исключение папки `diagnostics/`

**Триггеры:** push, pull_request на main/master

### 5. Dependency Check (`dependency-check.yml`)
**Назначение:** Валидация зависимостей проекта

**Проверки:**
- `pip-check` — проверка неиспользуемых зависимостей
- Сортировка requirements.txt
- Проверка дубликатов пакетов
- Проверка закрепленных версий

**Триггеры:** push, pull_request, schedule (еженедельно), workflow_dispatch

### 6. Pre-commit Hooks (`pre-commit.yml`)
**Назначение:** Дополнительная проверка качества кода

**Проверки:**
- Все проверки из `.pre-commit-config.yaml`
- Форматирование, линтинг, безопасность
- Проверка YAML, JSON, TOML файлов

**Триггеры:** push, pull_request на main/master

## Pre-commit Hooks

### Установка
```bash
pip install pre-commit
pre-commit install
```

### Конфигурация (`.pre-commit-config.yaml`)
- **Python:** black, flake8, isort, mypy, bandit
- **Общие:** trailing-whitespace, end-of-file-fixer, check-yaml
- **Безопасность:** detect-private-key, check-added-large-files
- **Markdown:** markdownlint-cli

### Исключения
- `diagnostics/` — диагностические файлы
- `modules/` — пользовательские данные
- `.env*` — файлы окружения

## Branch Protection

### Настройки защиты ветки `main`
- **Required Status Checks:** все 5 основных workflows
- **Strict Mode:** включен (требует актуального статуса)
- **Required Reviews:** 1 одобрение для PR
- **Dismiss Stale Reviews:** включено
- **Code Owner Reviews:** отключено (на начальной фазе)

### Контексты проверок
- `code-quality`
- `security-scan`
- `unit-tests`
- `docs-validation`
- `dependency-check`

## CODEOWNERS

### Зоны ответственности
```
# Архитектура и БД
/core/ @proektor1001
/core/database/ @proektor1001
/core/parsers/ @proektor1001

# CI/CD
/.github/ @proektor1001
/Makefile @proektor1001

# Конфигурация
*.yml @proektor1001
pyproject.toml @proektor1001
requirements.txt @proektor1001
```

## GitHub Secrets

### Автоматическая синхронизация
Скрипт `core/scripts/ci/setup_github_secrets.py` синхронизирует:
- `GITHUB_PAT` — токен для API
- `DB_*` — параметры подключения к БД

### Безопасность
- Секреты шифруются публичным ключом репозитория
- `GITHUB_PAT` остается в `.env` для локальной разработки
- Автоматическая проверка доступности секретов

## Автоматизация Branch Protection

### Скрипт мониторинга
`core/scripts/ci/enable_branch_protection.py`:
- Мониторинг статуса workflows
- Автоматическое включение защиты ветки
- Верификация настроек

### Использование
```bash
python core/scripts/ci/enable_branch_protection.py
```

## Troubleshooting

### Частые проблемы

1. **Workflows не запускаются**
   - Проверить триггеры в `.github/workflows/`
   - Убедиться в корректности YAML синтаксиса

2. **Pre-commit hooks не работают**
   - Переустановить: `pre-commit install --overwrite`
   - Обновить хуки: `pre-commit autoupdate`

3. **Branch protection не включается**
   - Дождаться успешного завершения всех workflows
   - Проверить права доступа GITHUB_PAT

4. **Secrets недоступны**
   - Запустить `python core/scripts/ci/setup_github_secrets.py`
   - Проверить права токена

### Логи и диагностика
- GitHub Actions: https://github.com/proektor1001/BZ-BrokerCursor/actions
- Локальные логи: `pre-commit run --all-files --verbose`

## Расширения (будущие версии)

### Semantic Release
- Автоматическое версионирование
- Генерация CHANGELOG
- Создание релизов

### Advanced Security
- Dependabot для обновлений
- CodeQL для анализа кода
- Secret scanning

### Deployment
- Автоматическое развертывание
- Docker контейнеризация
- Мониторинг и алерты
