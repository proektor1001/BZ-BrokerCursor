# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.9.0] – 2025-10-24

### Added

- ✅ Smoke test: 29/29 успешных проверок (28 PASS + 1 SKIP)
- 🔁 Идемпотентный smoke test с SKIP-статусами для ожидаемого поведения
- 🧠 Парсер: поле `trade_count`, улучшена структура JSON
- 💻 CLI: совместимость с Windows (UTF-8, символ ₽)
- 📦 Операции с БД: `update_report_parsed_data()`
- 📄 Отчёт: `smoke_test_report_<timestamp>.md` + latest.md

### Changed

- Обновлена документация README.md с разделом Smoke Test
- Версия проекта обновлена до 0.9.0

### Technical Details

- **Smoke Test Coverage**: 29 проверок включают целостность БД, структуру данных, CLI команды, аудит логи, стабильность системы, SQL запросы
- **Cross-platform**: Поддержка Windows и Linux для CI/CD
- **Idempotent Design**: Возможность многократного запуска без побочных эффектов
- **Report Structure**: Структурированные отчёты с временными метками и детальными результатами

### Files Modified

- `README.md` — добавлен раздел Smoke Test, обновлена версия
- `core/scripts/verify/smoke_test.py` — комплексная система валидации
- `diagnostics/smoke_test_report.md` — отчёт о результатах тестирования

### CI/CD Ready

- Готовность к интеграции с GitHub Actions
- Кросс-платформенная поддержка (Windows/Linux)
- Автоматическая генерация артефактов тестирования
