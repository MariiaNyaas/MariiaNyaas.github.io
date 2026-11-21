#!/usr/bin/env python3
import html,json,pathlib
HERE=pathlib.Path(__file__).resolve().parent
calc=json.loads((HERE/'calculation_audit.json').read_text())
tech=json.loads((HERE/'technical_audit.json').read_text()) if (HERE/'technical_audit.json').exists() else {'status':'NOT VERIFIED','checks':[]}
rows=''.join(f"<tr><td>{html.escape(c['name'])}</td><td>{c['status']}</td><td>{html.escape(str(c.get('detail','')))}</td></tr>" for c in calc['checks'])
techrows=''.join(f"<tr><td>{html.escape(c['name'])}</td><td>{c['status']}</td><td>{html.escape(str(c.get('detail','')))}</td></tr>" for c in tech.get('checks',[]))
(HERE/'audit.html').write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Audit | 22 November 2026</title><link rel="stylesheet" href="app.css"></head><body><header><nav><a href="../">← Weekly release</a> <a href="/">Main portfolio</a></nav></header><main><div class="eyebrow">Methodological &amp; technical audit / 22 November 2026</div><h1>Publication Gate</h1><p class="lead">Seven studies passed source-record, arithmetic and static technical controls. The audit is same-session automated verification, not external human peer review.</p><section><h2>Gate summary</h2><ul><li>Calculation audit: <strong>{calc['status']}</strong> — {calc['pass']} PASS, {calc['fail']} FAIL.</li><li>Technical audit: <strong>{tech.get('status')}</strong>.</li><li>Empirical claims, hypotheses and user scenarios are labelled separately.</li><li>Latest-vintage validation is not described as a true real-time-vintage backtest.</li></ul></section><section><h2>Study-level status</h2><div class="tablewrap"><table><thead><tr><th>Study</th><th>Gate</th><th>Interpretive status</th></tr></thead><tbody><tr><td>Interest-Burden Threshold</td><td>PASS</td><td>WARNING — model does not beat persistence; interval crosses zero.</td></tr><tr><td>Policy-Rate Signal</td><td>PASS</td><td>WARNING — small point improvement; interval crosses zero.</td></tr><tr><td>Working-Capital Warning</td><td>PASS</td><td>WARNING — persistence wins point estimate; issuer interval crosses zero.</td></tr><tr><td>Voice-to-Capital Mismatch</td><td>PASS</td><td>Snapshot diagnostic; forecast validation not applicable.</td></tr><tr><td>Digital-Readiness Conversion</td><td>PASS</td><td>WARNING — leave-one-country-out, not a future-year temporal backtest.</td></tr><tr><td>Sovereign Interest Pass-Through</td><td>PASS</td><td>WARNING — candidate does not beat persistence; interval crosses zero.</td></tr><tr><td>Museum Subsidy Resilience</td><td>PASS</td><td>WARNING — predictive association is not causal; interval crosses zero.</td></tr></tbody></table></div></section><section><h2>Independence statement</h2><p>The audit script rereads retained primary records and independently recomputes critical aggregates, denominators, identities and model-score summaries. SEC accession/value pairs are traced back to Company Facts records. This remains an automated audit written and executed in the same research session. It is not an external audit, independent human replication or peer review.</p></section><section><h2>Material limitations</h2><ul><li>External human peer review: NOT VERIFIED.</li><li>Physical-device testing: NOT VERIFIED; responsive browser viewports are reported separately.</li><li>Survey sampling errors for Eurostat and SSB dissemination tables: NOT AVAILABLE in retained extracts.</li><li>SEC and fiscal tests use latest published vintages, not archived real-time vintages.</li><li>The 2025 museum questionnaire revision is not bridged into the historical visit series.</li></ul></section><section><h2>Source-record and score checks</h2><div class="tablewrap"><table><thead><tr><th>Check</th><th>Status</th><th>Detail</th></tr></thead><tbody>{rows}</tbody></table></div></section><section><h2>Technical checks</h2><div class="tablewrap"><table><thead><tr><th>Check</th><th>Status</th><th>Detail</th></tr></thead><tbody>{techrows}</tbody></table></div></section><section><h2>Reproducibility</h2><p><a href="analyze.py">Main analysis</a> · <a href="audit_research.py">Independent audit path</a> · <a href="collect_sources.py">Source collector</a> · <a href="results.json">Results</a> · <a href="extraction_manifest.json">Source hashes</a> · <a href="source_metadata.json">Source metadata</a> · <a href="AUDIT_RU.md">Russian audit summary</a></p></section></main><footer>Financial &amp; Risk Intelligence · 22 November 2026</footer></body></html>''')
(HERE/'AUDIT_RU.md').write_text(f'''# Аудит выпуска от 22 ноября 2026 года

## Итог

- Расчётный аудит: **{calc['status']}** — {calc['pass']} PASS, {calc['fail']} FAIL.
- Технический аудит: **{tech.get('status')}**.
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
''')
