<!-- fb57b88f-1658-438e-b899-6a44a3938a35 7df8db89-f34d-4c69-8951-fcd26bfc2d70 -->
# Fix Smoke Test Failures

## Overview

Устранить 10 из 25 failed проверок в smoke test. Основные проблемы: отсутствие поля `trade_count` в parsed_data, Unicode-ошибки в CLI на Windows, проблемы с повторным импортом тестовых файлов.

**Контекст выполнения**: Python 3.10+, Windows 11, PowerShell/cmd.exe (кодировка cp1251)

**Принципы**:

- Smoke test остаётся идемпотентным (безопасен для повторного запуска)
- Все изменения логируются в `diagnostics/smoke_test_fixes.log`
- Обработка ошибок не прерывает выполнение остальных проверок (fail-safe режим)
- Все 6 блоков smoke_test выполняются независимо — ошибки фиксируются, но тест продолжается до конца

**Требования к окружению**:

- Python ≥ 3.10
- ОС: Windows 11 (PowerShell/cmd) или Linux (bash)
- Установлены зависимости из `requirements.txt`

## Root Cause Analysis

**Проблема 1: Missing `trade_count` field (6 failed checks)**

- Парсер возвращает `trades: {count: N, details: [...]}` 
- Smoke test ищет `trade_count` напрямую в корне parsed_data
- **Fix**: добавить `trade_count` в результат парсинга

**Проблема 2: Unicode encoding in CLI (1 failed check)**

- Символ рубля `₽` (\u20bd) не поддерживается в Windows cp1251
- **Fix**: заменить на 'RUB' или настроить UTF-8

**Проблема 3: Test file duplicate detection (2 failed checks)**

- Тестовый файл является копией существующего (идентичный hash)
- Система защиты от дубликатов блокирует повторный импорт
- **Fix**: изменить логику smoke test для обхода защиты

**Проблема 4: Balance validation SQL (1 failed check)**

- SQL извлекает данные, но валидация падает
- **Fix**: проверить тип данных в результате запроса

## Implementation Steps

### 1. Fix Parser - Add trade_count Field

**File**: `core/parsers/sber_html_parser.py`

В методе `parse()` добавить извлечение `trade_count` из `trades`:

```python
result = {
    "version": "2.0",
    "balance_ending": self._extract_balance_ending(),
    "account_open_date": self._extract_account_open_date(),
    "trades": self._extract_trades(),
    "trade_count": self._extract_trades()["count"],  # ADD THIS LINE
    "instruments": self._extract_instruments(),
    "financial_result": self._extract_financial_result(),
    ...
}
```

**Требования к `trade_count`**:

- Должен присутствовать в `parsed_data`
- Тип: целое число (int)
- Значение: ≥ 0
- Если trades не найдены в HTML → сохранять `trade_count = 0` (валидное состояние)

Затем перепарсить все отчёты: `python core/scripts/parse/parse_reports.py`

### 2. Fix CLI Unicode Issues

**File**: `core/scripts/query/query_reports.py`

Варианты решения:

- **A)** Заменить `₽` на `'RUB'` в строках вывода
- **B)** Добавить `sys.stdout.reconfigure(encoding='utf-8')` в начале main()

Предпочтительно вариант A (совместимость):

```python
# Line 39
console.print(f"[green]Balance Ending: {balance:,.2f} RUB[/green]")

# Line 84
console.print(f"[{color}]Financial Result: {sign}{result:,.2f} RUB[/{color}]")
```

### 3. Fix Smoke Test - Handle Duplicates

**File**: `core/scripts/verify/smoke_test.py`

В методе `check_new_data_stability()`:

**Рекомендуемое решение**: Использовать временный каталог и модифицировать файл:

```python
# Create tmp directory for test files
tmp_dir = self.config.INBOX_PATH.parent / 'tmp'
tmp_dir.mkdir(parents=True, exist_ok=True)

# Copy to tmp and modify
test_filename = f"smoke_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
self.test_file_path = tmp_dir / test_filename
shutil.copy2(source_file, self.test_file_path)

# Add unique marker to avoid duplicate hash
with open(self.test_file_path, 'a', encoding='utf-8') as f:
    f.write(f"\n<!-- smoke test marker: {datetime.now().isoformat()} -->")

# Move to inbox for processing
inbox_test_path = self.config.INBOX_PATH / test_filename
shutil.move(self.test_file_path, inbox_test_path)
self.test_file_path = inbox_test_path
```

**Cleanup**: После завершения теста удалить файл из archive и database:

- Удалить по точному `filename` и `file_hash`
- Восстановить исходное состояние БД (rollback)

### 4. Fix Balance Validation in Smoke Test

**File**: `core/scripts/verify/smoke_test.py`

В методе `check_manual_sql_query()` улучшить проверку типов:

```python
balance = row.get('balance')
if balance is not None:
    try:
        balance_float = float(balance)
        if balance_float >= 0:
            valid_balances += 1
    except (ValueError, TypeError):
        pass
```

### 5. Re-run Smoke Test

После всех исправлений:

```bash
make smoke-test
```

Ожидаемый результат: **25/25 PASS** ✅

## Files to Modify

1. `core/parsers/sber_html_parser.py` - добавить trade_count
2. `core/scripts/query/query_reports.py` - заменить ₽ на RUB
3. `core/scripts/verify/smoke_test.py` - исправить логику тестирования дубликатов и валидации balance

## Success Criteria

- Smoke test проходит с 25/25 успешными проверками
- Нет Unicode ошибок в CLI
- Тестовый файл успешно импортируется и парсится
- Все parsed_data содержат требуемые поля

### To-dos

- [ ] Create core/scripts/verify/smoke_test.py with all 6 validation sections
- [ ] Add smoke-test target to Makefile
- [ ] Execute smoke test and verify report generation