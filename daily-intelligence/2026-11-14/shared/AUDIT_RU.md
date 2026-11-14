# Аудит выпуска 14 ноября 2026

**Gate: PASS с раскрытыми предупреждениями.**

- Независимый расчётный путь: **690 PASS, 0 FAIL**.
- Скрипт аудита заново читает первичные записи и не импортирует основной `analyze.py`.
- Проверены JSON-stat ячейки SSB, SEC accession/tag/value, NBIM country–industry cells, Eurostat paired cells, power workbook, фискальные тождества, ошибки backtest и структура шести dashboards.
- Это автоматизированная проверка в той же исследовательской сессии, **не внешняя человеческая рецензия**.
- GitHub Actions run `43556512140` завершён успешно для проверенного content commit `828de9c`.
- На опубликованном сайте проверены 18 контролов, 6 reset, 128 вариантов селекторов, 6 CSV-экспортов, 6 переходов Methodology, Latest Research и 6 тематических каталогов.
- При ширине 539 CSS px горизонтального переполнения body не обнаружено; физическое мобильное устройство остаётся **NOT VERIFIED**.

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
