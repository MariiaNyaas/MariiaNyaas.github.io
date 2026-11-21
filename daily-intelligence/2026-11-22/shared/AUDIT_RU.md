# Аудит выпуска от 22 ноября 2026 года

## Итог

- Расчётный аудит: **PASS** — 593 PASS, 0 FAIL.
- Технический аудит: **PASS**.
- Публикационный gate: **PASS** для семи исследований при раскрытых ограничениях.

## Фактическая независимость

Отдельный скрипт повторно читает сохранённые первичные записи, пересчитывает ключевые агрегаты, знаменатели, балансовые тождества и показатели ошибок. Для SEC проверяются accession/value против Company Facts. Это автоматизированный аудит, выполненный в той же исследовательской сессии. Он не является внешней человеческой рецензией, независимым внешним аудитом или peer review.

## Статусы

| Исследование | Gate | Интерпретация |
|---|---:|---|
| Interest-Burden Threshold | PASS | WARNING: модель не превзошла persistence; интервал пересекает ноль. |
| Policy-Rate Signal | PASS | WARNING: небольшое точечное улучшение; интервал пересекает ноль. |
| Working-Capital Warning | PASS | WARNING: persistence лучше по point estimate. |
| Voice-to-Capital Mismatch | PASS | Snapshot; backtesting неприменим. |
| Digital-Readiness Conversion | PASS | WARNING: cross-country holdout, не future-year backtest. |
| Sovereign Interest Pass-Through | PASS | WARNING: модель не превзошла persistence. |
| Museum Subsidy Resilience | PASS | WARNING: predictive association не является причинностью. |

## NOT VERIFIED

- Внешняя человеческая рецензия.
- Тестирование на физических мобильных устройствах.
- Sampling errors для распространённых таблиц Eurostat/SSB.
- Настоящие real-time vintages SEC и государственных финансов.
- Сопоставимость музейных посещений после изменения анкеты в 2025 году.

## Файлы

- `analyze.py` — основной расчёт.
- `audit_research.py` — независимый расчётный путь.
- `calculation_audit.json` — подробный журнал проверок.
- `technical_audit.json` — технический журнал.
- `extraction_manifest.json` — контрольные суммы.
- `source_metadata.json` — происхождение, периоды, единицы и ревизии.
