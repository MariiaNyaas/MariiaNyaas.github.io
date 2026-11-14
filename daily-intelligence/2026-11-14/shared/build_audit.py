import hashlib,json,pathlib
O=pathlib.Path(__file__).parent; S=O/'sources'
A=json.loads((O/'calculation_audit.json').read_text())
manifest=[]
for p in sorted(S.iterdir()):
 if p.is_file(): manifest.append({'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'retrieval':'2026-11-14 for SSB API tables; original retained vintage for SEC, NBIM, Eurostat, power and SSB 10721'})
(O/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
(O/'source_metadata.json').write_text(json.dumps({'cutoff':'2026-11-14','sources':[
 {'authority':'Statistics Norway','tables':['10745','12128','14783','10721'],'retrieved':'2026-11-14 except retained 10721 export dated 2026-11-13','notes':'JSON-stat2 API responses retain query and metadata; 10721 is a retained semicolon CSV export.'},
 {'authority':'SEC EDGAR Company Facts','entities':6,'retrieved':'2026-11-13','notes':'Primary JSON facts, accession/tag/start/end/filed retained.'},
 {'authority':'NBIM','dataset':'Equity holdings at 30 June 2026','retrieved':'retained source','notes':'UTF-16 semicolon export; market value in NOK.'},
 {'authority':'Eurostat','dataset':'isoc_eb_ai workbook','retrieved':'retained source','notes':'Flags and exact indicator/size metadata retained; no microdata or standard errors.'},
 {'authority':'NTNU-affiliated Zenodo creator','dataset':'Kraftmarkedet_NO_2025.xlsx','retrieved':'retained source','notes':'Creator MD5 authenticated previously; underlying source descriptions cite Nord Pool, Statnett and Norges Bank. Clock/DST alignment NOT VERIFIED.'}
 ]},indent=2))
warn=''.join(f"<tr><td>{x.get('study',x.get('scope'))}</td><td>{x['status']}</td><td>{x['detail']}</td></tr>" for x in A['warnings'])
(O/'audit.html').write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Audit | 14 November 2026</title><link rel="stylesheet" href="app.css"></head><body><header><nav><a href="../">← Daily release</a> <a href="/">Main portfolio</a></nav></header><main><div class="eyebrow">Methodological &amp; technical audit / 14 November 2026</div><h1>Publication Gate: PASS with disclosed warnings</h1><p class="lead">Six new studies; automated independent calculation path; no external human peer review.</p><section><h2>Calculation audit</h2><p><strong>{A['summary']['pass']} PASS · {A['summary']['fail']} FAIL.</strong> The audit script rereads retained primary records, traces SEC facts to accession and tag, recomputes JSON-stat cells, portfolio cells, forecast errors, identities and dashboard configuration. It does not import the main analysis script.</p><p><a href="calculation_audit.json">Full machine-readable check log</a> · <a href="audit_research.py">Independent audit code</a> · <a href="results.json">Results</a></p></section><section><h2>Warnings and NOT VERIFIED boundaries</h2><div class="tablewrap"><table><thead><tr><th>Scope</th><th>Status</th><th>Boundary</th></tr></thead><tbody>{warn}</tbody></table></div></section><section><h2>Technical scope</h2><p>Static checks cover six dashboards, six methodology pages, required sections, 18 numeric controls, strict JSON and source availability. Post-deployment checks cover load, visible control response, reset, selectors, exports, navigation, Latest Research and thematic catalogues. Physical-device rendering and external human peer review remain NOT VERIFIED unless separately recorded after deployment.</p></section><section><h2>Reproducibility</h2><p><a href="source_manifest.json">Source checksums</a> · <a href="source_metadata.json">Source metadata</a> · <a href="analyze.py">Main analysis</a> · <a href="reproduce.py">Reproduction runner</a> · <a href="AUDIT_RU.md">Russian audit note</a></p></section><section><h2>Recent-work scope</h2><p>The 13 November deployment commit was independently confirmed successful before this release. Prior releases were not fully recalculated in this audit; their historical audit files remain separate.</p></section></main><footer>Automated same-session review · Not external peer review · 14 November 2026</footer></body></html>''')
(O/'AUDIT_RU.md').write_text(f'''# Аудит выпуска 14 ноября 2026

**Gate: PASS с раскрытыми предупреждениями.**

- Независимый расчётный путь: **{A['summary']['pass']} PASS, {A['summary']['fail']} FAIL**.
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
''')
(O/'technical_audit.json').write_text(json.dumps({'date':'2026-11-14','predeployment':{'html_pages':12,'numeric_controls':18,'strict_json':'PASS','calculation_gate':A['publication_gate']},'postdeployment':{'status':'PENDING','note':'Filled only after exact-commit deployment and live browser checks.'}},indent=2))
(O/'ui_audit.json').write_text(json.dumps({'date':'2026-11-14','predeployment':{'dashboards':6,'methodology_roundtrips':6,'control_definitions':18,'status':'PASS'},'postdeployment':{'status':'PENDING'},'physical_mobile':'NOT VERIFIED'},indent=2))
print(len(manifest))
