# BrokerCursor

[![Code Quality](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/code-quality.yml/badge.svg)](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/code-quality.yml)
[![Security Scanning](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/security.yml/badge.svg)](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/security.yml)
[![Unit Tests](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/unit-tests.yml)
[![Documentation Validation](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/docs-validation.yml/badge.svg)](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/docs-validation.yml)
[![Dependency Check](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/dependency-check.yml/badge.svg)](https://github.com/proektor1001/BZ-BrokerCursor/actions/workflows/dependency-check.yml)

## Цель проекта

Создать централизованную систему хранения, обработки и анализа брокерских отчётов (HTML, TXT, PDF, MD) с возможностью масштабирования и повторного использования данных.

## Где размещать исходные отчёты

Входящие файлы (отчёты брокеров) помещаются вручную в папку:

```text
modules/broker-reports/inbox/
```

**Поддерживаемые форматы:**

- `.html` — брокерские отчёты
- `.txt`, `.pdf`, `.md` — вспомогательные или конвертированные форматы

**После помещения:**

- Выполните импорт командой:

  ```bash
  python core/scripts/import/import_reports.py
  ```

- Файлы будут обработаны, проверены на дубликаты и перенесены в `archive/`
- Структурированные данные сохраняются в базе (`parsed_data`)

## Архитектура

**PostgreSQL + JSONB + BeautifulSoup** — современная архитектура для гибкого хранения и обработки отчётов с автоматической дедупликацией.

### Основные компоненты

- **PostgreSQL** — структурированное хранение метаданных и операций
- **JSONB** — гибкое хранение HTML отчётов и извлечённых данных
- **BeautifulSoup4 + lxml** — парсинг HTML отчётов в структурированные данные
- **CLI Tools** — автоматизация импорта, парсинга и управления
- **Deduplication** — SHA-256 хеширование для предотвращения дубликатов
- **Import Log** — отслеживание всех операций импорта и статусов

### Ключевые зависимости

- `psycopg2-binary==2.9.9` — PostgreSQL драйвер
- `beautifulsoup4==4.12.2` + `lxml==4.9.3` — HTML парсинг
- `rich==13.7.0` — форматирование CLI
- `python-dotenv==1.0.0` — конфигурация
- `jsonschema==4.20.0` — валидация данных

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка базы данных

Скопируйте `.env.example` в `.env` и настройте подключение к PostgreSQL:

```bash
cp .env.example .env
# Отредактируйте .env с вашими настройками БД
```

### 3. Инициализация базы данных

```bash
python core/scripts/init_db.py
```

### 4. Проверка настройки

```bash
python core/scripts/verify/verify_setup.py
```

### 5. Импорт отчётов

```bash
# Поместите HTML/TXT/PDF/MD файлы в modules/broker-reports/inbox/
python core/scripts/import/import_reports.py

# Просмотр статистики
python core/scripts/import/import_reports.py --stats
```

## Структура проекта

```text
BZ-BrokerCursor/
├── core/
│   ├── database/           # Подключение к БД и операции
│   │   ├── connection.py
│   │   ├── operations.py
│   │   └── schema.sql
│   ├── parsers/            # HTML парсеры
│   │   └── sber_html_parser.py
│   ├── scripts/           # CLI инструменты
│   │   ├── import/        # Импорт отчётов
│   │   │   ├── import_reports.py
│   │   │   └── backfill_hashes.py
│   │   ├── parse/         # Парсинг отчётов
│   │   │   └── parse_reports.py
│   │   ├── query/         # Запросы к данным
│   │   │   └── query_reports.py
│   │   ├── verify/        # Верификация системы
│   │   │   ├── verify_import.py
│   │   │   ├── verify_db_integrity.py
│   │   │   ├── verify_report_data.py
│   │   │   └── verify_setup.py
│   │   ├── init_db.py     # Инициализация БД
│   │   └── migrate_db.py  # Миграции БД
│   ├── utils/              # Утилиты
│   │   └── file_manager.py
│   └── config.py          # Конфигурация
├── modules/
│   ├── broker-reports/    # Основное хранилище отчётов
│   │   ├── inbox/        # Входящие файлы
│   │   ├── archive/      # Обработанные файлы
│   │   └── parsed/       # JSON данные (опционально)
│   └── ...
├── diagnostics/           # Отчёты и логи
└── requirements.txt
```

## Схема базы данных

### Таблица `broker_reports`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | SERIAL | Уникальный идентификатор |
| `broker` | VARCHAR(50) | Брокер (sber, tinkoff, vtb, etc.) |
| `account` | VARCHAR(50) | Номер счёта |
| `period` | VARCHAR(7) | Период отчёта (YYYY-MM) |
| `file_name` | VARCHAR(500) | Имя файла |
| `file_hash` | VARCHAR(64) | SHA-256 хеш для дедупликации |
| `html_content` | TEXT | HTML содержимое |
| `parsed_data` | JSONB | Извлечённые данные |
| `processing_status` | VARCHAR(20) | Статус обработки |
| `created_at` | TIMESTAMP | Дата создания |
| `updated_at` | TIMESTAMP | Дата обновления |

### Таблица `import_log`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | SERIAL | Уникальный идентификатор |
| `operation_type` | VARCHAR(20) | Тип операции (import, update, delete, archive) |
| `broker` | VARCHAR(50) | Брокер |
| `file_name` | VARCHAR(500) | Имя файла |
| `file_hash` | VARCHAR(64) | SHA-256 хеш |
| `status` | VARCHAR(40) | Статус операции |
| `files_processed` | INTEGER | Количество обработанных файлов |
| `files_success` | INTEGER | Успешно обработанных |
| `files_failed` | INTEGER | Ошибок обработки |
| `started_at` | TIMESTAMP | Время начала |
| `completed_at` | TIMESTAMP | Время завершения |

### Статусы обработки

- `raw` — исходный файл загружен
- `processing` — в процессе обработки
- `parsed` — успешно обработан
- `duplicate_detected` — обнаружен дубликат
- `error` — ошибка обработки

### Ограничения уникальности

- `(broker, COALESCE(account, '∅'), period)` — предотвращает дубликаты отчётов

## Процессинг и Workflow

### Полный цикл обработки

1. **Загрузка** — файлы помещаются в `modules/broker-reports/inbox/`
2. **Импорт** — `import_reports.py` сканирует inbox и создаёт записи в БД
3. **Хеширование** — вычисляется SHA-256 для дедупликации
4. **Дедупликация** — проверка на существующие хеши
5. **Архивирование** — файлы перемещаются в `archive/`
6. **Парсинг** — `parse_reports.py` извлекает структурированные данные
7. **Валидация** — проверка целостности данных
8. **Анализ** — запросы через `query_reports.py`

### Переходы статусов

```text
raw → processing → parsed
  ↓       ↓         ↓
error  error    error
```

### Парсинг HTML

- **BeautifulSoup4** — основной парсер HTML
- **lxml** — быстрый XML/HTML парсер
- **SberHtmlParser** — специализированный парсер для Сбербанка
- **JSON v2.0** — стандартизированный формат вывода

## CLI Команды

### Инициализация

```bash
# Создание таблиц и индексов
python core/scripts/init_db.py

# Проверка настройки
python core/scripts/verify/verify_setup.py
```

### Импорт отчётов

```bash
# Импорт всех файлов из inbox
python core/scripts/import/import_reports.py

# Импорт только отчётов Сбербанка
python core/scripts/import/import_reports.py --broker sber

# Просмотр что будет импортировано (без изменений)
python core/scripts/import/import_reports.py --dry-run

# Статистика базы данных
python core/scripts/import/import_reports.py --stats
```

### Парсинг отчётов

```bash
# Парсинг всех raw отчётов
python core/scripts/parse/parse_reports.py

# Парсинг отчётов конкретного брокера
python core/scripts/parse/parse_reports.py --filter broker=sber

# Просмотр что будет спарсено (без изменений)
python core/scripts/parse/parse_reports.py --dry-run
```

### Запросы к данным

```bash
# Просмотр всех отчётов
python core/scripts/query/query_reports.py

# Фильтрация по брокеру и периоду
python core/scripts/query/query_reports.py --filter broker=sber --filter period=2023-07

# Показать баланс конкретного отчёта
python core/scripts/query/query_reports.py --filter account=4000T49 --show balance_ending

# Показать инструменты портфеля
python core/scripts/query/query_reports.py --filter broker=sber --show instruments

# Показать финансовый результат
python core/scripts/query/query_reports.py --filter period=2023-07 --show result

# Поиск по содержимому
python core/scripts/query/query_reports.py --search "ТГК-1"
```

### Верификация системы

```bash
# Полная проверка системы
python core/scripts/verify/verify_setup.py

# Проверка целостности импорта
python core/scripts/verify/verify_import.py

# Проверка целостности базы данных
python core/scripts/verify/verify_db_integrity.py

# Проверка данных отчётов
python core/scripts/verify/verify_report_data.py
```

### Утилиты

```bash
# Обновление хешей файлов
python core/scripts/import/backfill_hashes.py --all

# Обновление только существующих хешей
python core/scripts/import/backfill_hashes.py --update-existing

# Просмотр что будет обновлено (без изменений)
python core/scripts/import/backfill_hashes.py --all --dry-run
```

## Smoke Test

Комплексная система валидации BrokerCursor с 29 проверками для диагностики целостности БД, парсера, CLI команд и аудита.

### Назначение

Smoke test выполняет полную проверку системы:

- **Целостность БД** — соответствие записей количеству файлов, наличие хешей, статус парсинга
- **Структура данных** — валидация `parsed_data`, обязательные поля, корректность значений
- **CLI команды** — тестирование `--show`, `--filter`, `--search` с различными параметрами
- **Аудит логи** — проверка `import_log`, диагностических отчётов, логов дубликатов
- **Стабильность** — обработка новых данных, тестирование полного цикла импорт→парсинг
- **SQL запросы** — извлечение данных из JSONB, валидация балансов

### Запуск

```bash
python core/scripts/verify/smoke_test.py
```

### Особенности

- **Идемпотентность** — можно запускать многократно без побочных эффектов
- **SKIP статусы** — корректная обработка ожидаемых ситуаций (дубликаты, отсутствие данных)
- **CI/CD готовность** — возвращает exit code 0 при успехе, 1 при ошибках
- **Кросс-платформенность** — работает на Windows и Linux

### Результаты

Отчёт сохраняется в `diagnostics/smoke_test_report.md`:

- Заголовок с датой и временем генерации
- Сводка: общее количество, успешные, проваленные проверки
- Детальные результаты по категориям
- Рекомендации при обнаружении проблем

**Ожидаемый результат:** 29/29 проверок (28 PASS + 1 SKIP для ожидаемого поведения)

## Диагностика и верификация

### Диагностические отчёты

Результаты проверки сохраняются в `diagnostics/`:

- `import_verification.md` — проверка целостности импорта
- `db_verification_report.md` — проверка базы данных
- `import_recovery_report.md` — процедуры восстановления
- `import_integrity_report.md` — анализ целостности данных

### Скрипты верификации

- **`verify_setup.py`** — начальная проверка настройки системы
- **`verify_import.py`** — анализ целостности импорта
- **`verify_db_integrity.py`** — проверка консистентности БД
- **`verify_report_data.py`** — валидация спарсенных данных

### Статистика базы данных

```bash
python core/scripts/import/import_reports.py --stats
```

## Поддерживаемые брокеры

- ✅ **Сбербанк** (sber) — HTML отчёты
- 🔜 **Тинькофф** (tinkoff) — HTML отчёты
- 🔜 **ВТБ** (vtb) — HTML отчёты
- 🔜 **Газпромбанк** (gazprombank) — HTML отчёты
- 🔜 **Альфа-Банк** (alpha) — HTML отчёты

## Конфигурация

### Переменные окружения (.env)

```env
# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=brokercursor
DB_USER=brokercursor_user
DB_PASSWORD=your_password

# Пути к файлам
INBOX_PATH=modules/broker-reports/inbox
ARCHIVE_PATH=modules/broker-reports/archive
PARSED_PATH=modules/broker-reports/parsed

# Настройки обработки
MAX_FILE_SIZE_MB=50
SUPPORTED_EXTENSIONS=.html,.txt,.pdf,.md
```

## Troubleshooting

### Проблемы с подключением к БД

1. Проверьте настройки в `.env`
2. Убедитесь что PostgreSQL запущен
3. Проверьте права пользователя БД

### Проблемы с импортом

1. Проверьте права на директории `inbox/` и `archive/`
2. Убедитесь что файлы в поддерживаемых форматах
3. Проверьте размер файлов (лимит 50MB)

### Диагностика

```bash
# Полная проверка системы
python core/scripts/verify/verify_setup.py

# Просмотр логов
tail -f logs/brokercursor.log
```

## Формат данных JSONB

### Эталонная структура parsed_data (версия 2.0)

Для извлечённых из HTML данных используется следующий формат JSON:

```json
{
  "version": "2.0",
  "broker": "Сбер",
  "account": "4000T49",
  "period": "2023-07",
  "created": "2023-08-03",
  "client": "Пузанов В.А.",
  "assets": [
    {
      "name": "ТГК-1",
      "isin": "RU000A0JNUD0",
      "currency": "RUB",
      "start_qty": 4000000,
      "end_qty": 4000000,
      "price_start": 0.009082,
      "price_end": 0.011112,
      "value_start": 36328.00,
      "value_end": 44448.00,
      "nkd_start": 0.00,
      "nkd_end": 0.00,
      "delta_value": 8120.00
    }
  ],
  "cash": [
    {
      "market": "Основной рынок",
      "currency": "RUB",
      "rate": null,
      "start": 18873.87,
      "delta": -18873.87,
      "end": 0.00
    }
  ],
  "cashflow": [
    {
      "date": "2023-07-07",
      "market": "Основной рынок",
      "description": "Списание д/с",
      "currency": "RUB",
      "in": 0.00,
      "out": 18873.87
    }
  ],
  "tax": {
    "raw": {
      "income_code": "1530",
      "income": 80805.20,
      "expense_code": "201",
      "expense": 107027.36,
      "taxable": -26222.16,
      "standard_deduction": 0.00
    },
    "final": {
      "income": 80805.20,
      "expense": 107027.36,
      "taxable": -26222.16,
      "calculated_tax": null,
      "withheld_tax": null,
      "to_withhold": null
    }
  },
  "securities_dict": [
    {
      "name": "ТГК-1",
      "code": "TGKA",
      "isin": "RU000A0JNUD0",
      "issuer": "ПАО \"ТГК-1\"",
      "type": "Акция обыкновенная",
      "series": "1-01-03388-D"
    }
  ]
}
```

**Особенности формата:**

- Все блоки опциональны
- Формат адаптируется под разные брокеры
- Используется для построения аналитики и отчётов

## Планируемые модули

В будущих версиях планируется расширение функциональности:

### modules/securities/

Хранение информации о ценных бумагах:

- Финансовые отчёты компаний (PDF)
- Исторические данные котировок
- Дивидендная политика
- Аналитические материалы

### modules/accumulation-accounts/

Накопительные счета и ИИС:

- История пополнений и снятий
- Налоговые вычеты
- Доходность по периодам

### modules/user-profiles/

Профили пользователей:

- Персональные настройки
- Портфели по брокерам
- Инвестиционные стратегии

---

## AI-интеграция (опционально)

### Текущая позиция

- **Основная архитектура:** PostgreSQL + JSONB без обязательных AI-зависимостей
- **Cursor AI:** основной инструмент для разработки и помощи
- **AI-обработка:** опциональная, только при необходимости

### Возможные интеграции

- **Ollama + llama3.2** — лёгкая локальная LLM (3B параметров)
- **HuggingFace API** — бесплатные облачные модели
- **LocalAI** — локальная альтернатива OpenAI API

### Формат данных

- **JSON v2.0** — эталонная структура для `parsed_data`
- **Автономность** — система работает без внешних AI-сервисов
- **Надёжность** — приоритет стабильности над AI-функциями

---

**Статус:** ✅ Готов к использованию  
**Версия:** 0.9.0  
**Архитектура:** PostgreSQL + JSONB + BeautifulSoup  
**Обновлено:** 2025-10-24
