# Database Query Operations

## Broker Report Summary

### Overview
Генерация сводной таблицы всех брокерских отчётов из базы данных PostgreSQL.

### Implementation
- **Script**: `core/scripts/query/fetch_summary.py`
- **Output**: `diagnostics/broker_reports_summary.md`
- **Command**: `python core/scripts/query/fetch_summary.py`

### SQL Query
```sql
SELECT
    id AS report_id,
    broker,
    account,
    period,
    parsed_data ->> 'account_number' AS account_number,
    parsed_data ->> 'period_start' AS period_start,
    parsed_data ->> 'period_end' AS period_end
FROM broker_reports
ORDER BY (parsed_data ->> 'period_start') DESC NULLS LAST;
```

### Key Features
- **JSONB Field Extraction**: Использование `->>` для извлечения полей из JSONB
- **Proper Sorting**: Явное приведение JSONB поля для корректной сортировки
- **NULL Handling**: Отображение NULL значений как "N/A"
- **Markdown Output**: Форматированная таблица с метаданными

### Usage Example
```bash
# Generate summary
python core/scripts/query/fetch_summary.py

# Custom output path
python core/scripts/query/fetch_summary.py --output custom/path/summary.md
```

### Output Format
- **Total Reports**: Количество отчётов в базе
- **Generation Timestamp**: Время создания отчёта
- **Markdown Table**: Структурированная таблица с данными
- **Notes**: Пояснения по NULL значениям и сортировке
