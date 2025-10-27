<!-- ccb05485-727d-4cc2-a74e-0a0c7424503b 7617571f-192c-4cf5-bf01-2387217ceed7 -->
# AI Processing Policy Clarification

## Overview

Уточнить и задокументировать подход к AI-обработке в проекте. Система построена на PostgreSQL + JSONB без обязательной зависимости от внешних LLM сервисов.

## Detect Hardware Profile

Определить характеристики текущей системы:

- CPU (модель, ядра, частота)
- RAM (объём, тип)
- OS и версия
- Доступное дисковое пространство
- Python версия

Команда: `python3 -c "import platform, psutil, sys; ..."`

Сохранить в: `diagnostics/hardware_profile.md`

## Update Documentation - Remove GPT References

Обновить `README.md`:

- Убрать упоминания "GPT" из заголовков и описаний
- Изменить "PostgreSQL + JSONB + GPT" на "PostgreSQL + JSONB"
- Уточнить что AI-обработка опциональна
- Добавить раздел о возможных AI-интеграциях (будущее)

## Update modules/broker-reports/README.md

Аналогично убрать упоминания GPT и уточнить:

- Текущая архитектура: PostgreSQL + JSONB
- AI-обработка: опциональная, через CLI
- Парсинг HTML: вручную или через Cursor

## Create AI Processing Guidelines Document

Создать документ `docs/ai_processing_policy.md`:

- Текущая позиция: нет обязательной LLM-зависимости
- Возможные интеграции:
- Ollama (локальная LLM) - если бесплатно
- Облачные терминалы - только бесплатные
- Cursor AI - основной инструмент
- Формат вывода: JSON v2.0
- Приоритеты: автономность, надёжность, простота

## Update Plan File

Обновить `.plan.md` файл:

- Убрать "GPT" из описаний
- Уточнить что AI-интеграция опциональна
- Отразить реальную реализованную архитектуру

## Optional: Research Lightweight LLM Options

Если есть интерес, задокументировать возможности:

- Ollama + llama3.2 (3B параметров) для слабых ПК
- Бесплатные облачные API (HuggingFace Inference API)
- LocalAI (альтернатива OpenAI API)

Сохранить в: `docs/lightweight_llm_options.md`

## Key Points

1. **Текущая реализация**: PostgreSQL + JSONB, без обязательных LLM
2. **Cursor AI**: основной инструмент для разработки и помощи
3. **Будущие опции**: легковесные LLM только при необходимости
4. **Формат данных**: JSON v2.0 в JSONB полях
5. **Приоритет**: работоспособность на слабом железе

### To-dos

- [ ] Detect system hardware profile (CPU, RAM, OS) and save to diagnostics/hardware_profile.md
- [ ] Remove GPT references from README.md and clarify AI-optional architecture
- [ ] Remove GPT references from modules/broker-reports/README.md
- [ ] Create AI processing policy document at docs/ai_processing_policy.md
- [ ] Update plan file to remove GPT mentions and reflect actual implementation