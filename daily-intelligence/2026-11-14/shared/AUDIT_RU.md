# Аудит выпуска 14 ноября 2026

**Gate: PASS с раскрытыми предупреждениями.**

- Независимый расчётный путь: **690 PASS, 0 FAIL**.
- Скрипт аудита заново читает первичные записи и не импортирует основной `analyze.py`.
- Проверены JSON-stat ячейки SSB, SEC accession/tag/value, NBIM country–industry cells, Eurostat paired cells, power workbook, фискальные тождества, ошибки backtest и структура шести dashboards.
- Это автоматизированная проверка в той же исследовательской сессии, **не внешняя человеческая рецензия**.

## Статусы

| Исследование | Статус | Существенная граница |
|---|---|---|
| Credit Risk | WARNING | 8 годовых origin; интервал преимущества пересекает ноль; это не PD. |
| Financial | NOT VERIFIED | Временные метки, часовой пояс и DST power workbook не аутентифицированы; executable hedge не заявлен. |
| Accounting & Audit | WARNING | Сглаживание проигрывает last value; только шесть эмитентов. |
| Risk & Governance | WARNING | Snapshot cells — аналитическая группировка, не legal control и не risk contribution. |
| Business & Economic | NOT VERIFIED | Нет microdata, sampling errors и подтверждения nested populations; conversion rate не рассчитывается. |
| Public Finance | WARNING | Component rule проигрывает persistence; nominal latest-vintage данные заканчиваются 2024 годом. |
| External peer review | NOT VERIFIED | Внешняя рецензия не проводилась. |
| Physical mobile device | NOT VERIFIED | Требуется отдельная проверка на физическом устройстве. |

## Материалы

- [Полный журнал](calculation_audit.json)
- [Независимый код аудита](audit_research.py)
- [Основной код](analyze.py)
- [Результаты](results.json)
- [Контрольные суммы](source_manifest.json)
