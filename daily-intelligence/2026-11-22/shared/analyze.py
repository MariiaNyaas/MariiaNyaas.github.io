#!/usr/bin/env python3
"""Reproducible analysis for the 22 November 2026 weekly release."""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import pathlib
import sys

import numpy as np
import pandas as pd

S = pathlib.Path(sys.argv[1]).resolve()
O = pathlib.Path(sys.argv[2]).resolve()
O.mkdir(parents=True, exist_ok=True)
CUTOFF = "2026-11-21"
RNG = np.random.default_rng(20261122)
R = {"status": "PUBLICATION CANDIDATE", "release": "2026-11-22", "cutoff": CUTOFF, "studies": {}}


def scalar(value):
    if isinstance(value, dict):
        return {str(k): scalar(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [scalar(v) for v in value]
    if isinstance(value, np.ndarray):
        return scalar(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def jsonstat_rows(path: pathlib.Path):
    data = json.loads(path.read_text())
    ids, sizes = data["id"], data["size"]
    categories = []
    for key in ids:
        category = data["dimension"][key]["category"]
        order = category.get("index", {})
        if isinstance(order, dict):
            codes = [k for k, _ in sorted(order.items(), key=lambda pair: pair[1])]
        else:
            codes = list(category.get("label", {}))
        categories.append([(code, category.get("label", {}).get(code, code)) for code in codes])
    raw = data.get("value", {})
    values = {int(k): v for k, v in raw.items()} if isinstance(raw, dict) else {i: v for i, v in enumerate(raw)}
    rows = []
    for flat, value in values.items():
        remainder = flat
        coordinates = [0] * len(sizes)
        for column in range(len(sizes) - 1, -1, -1):
            coordinates[column], remainder = remainder % sizes[column], remainder // sizes[column]
        row = {ids[j]: categories[j][coordinates[j]][0] for j in range(len(ids))}
        row.update({ids[j] + "_label": categories[j][coordinates[j]][1] for j in range(len(ids))})
        row["value"] = value
        rows.append(row)
    return rows, data


def block_ci(values, block=2, draws=5000):
    array = np.asarray(values, float)
    if not len(array):
        return [None, None]
    means = []
    for _ in range(draws):
        starts = RNG.integers(0, len(array), size=math.ceil(len(array) / block))
        indices = np.concatenate([(start + np.arange(block)) % len(array) for start in starts])[: len(array)]
        means.append(float(array[indices].mean()))
    return [float(v) for v in np.quantile(means, [0.025, 0.975])]


def cluster_ci(rows, cluster, improvement, draws=5000):
    clusters = sorted({row[cluster] for row in rows})
    means = []
    for _ in range(draws):
        selected = RNG.choice(clusters, len(clusters), replace=True)
        values = [row[improvement] for key in selected for row in rows if row[cluster] == key]
        means.append(float(np.mean(values)))
    return [float(v) for v in np.quantile(means, [0.025, 0.975])]


def ridge_fit(x, y, ridge=1e-5):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    penalty = np.eye(x.shape[1]) * ridge
    penalty[0, 0] = 0
    return np.linalg.solve(x.T @ x + penalty, x.T @ y)


# 1. Credit risk: high interest burden as a forward signal of housing-payment strain.
burden_rows, _ = jsonstat_rows(S / "ssb_08727_response.json")
strain_rows, _ = jsonstat_rows(S / "ssb_12128_response.json")
burden = pd.DataFrame(burden_rows)
burden["value"] = pd.to_numeric(burden["value"], errors="coerce")
burden["year"] = burden["Tid"].astype(int)
burden["threshold"] = burden["RenteUtgift"].map({"15-20": 15, "20-30": 20, "30-40": 30, "40+": 40})
burden_15 = burden.groupby(["year", "Hushaldstype", "Hushaldstype_label"], as_index=False)["value"].sum().rename(columns={"value": "interest_burden_15plus_pct"})
all_burden = burden_15[burden_15.Hushaldstype == "50"][["year", "interest_burden_15plus_pct"]]
strain = pd.DataFrame(strain_rows)
strain["value"] = pd.to_numeric(strain["value"], errors="coerce")
strain["year"] = strain["Tid"].astype(int)
housing = strain[(strain.OkonomiskRomslig == "05") & (strain.Inntekstgruppe == "000")][["year", "value"]].rename(columns={"value": "housing_payment_problem_pct"})
credit = all_burden.merge(housing, on="year", how="inner").sort_values("year")
credit_bt = []
for i in range(6, len(credit)):
    train = credit.iloc[:i].copy()
    target = credit.iloc[i]
    supervised = pd.DataFrame({
        "y": train.housing_payment_problem_pct.shift(-1),
        "lag": train.housing_payment_problem_pct,
        "burden": train.interest_burden_15plus_pct,
    }).dropna()
    if len(supervised) < 5:
        continue
    beta = ridge_fit(np.column_stack([np.ones(len(supervised)), supervised["lag"], supervised["burden"]]), supervised["y"], 1e-4)
    previous = credit.iloc[i - 1]
    prediction = float(np.array([1, previous.housing_payment_problem_pct, previous.interest_burden_15plus_pct]) @ beta)
    credit_bt.append({
        "year": int(target.year),
        "actual": float(target.housing_payment_problem_pct),
        "model": prediction,
        "persistence": float(previous.housing_payment_problem_pct),
    })
credit_bt = credit_bt[-10:]
for row in credit_bt:
    row["improvement"] = abs(row["actual"] - row["persistence"]) - abs(row["actual"] - row["model"])
latest_burden = burden_15[burden_15.year == burden_15.year.max()].sort_values("interest_burden_15plus_pct", ascending=False)
R["studies"]["credit"] = {
    "title": "The Interest-Burden Threshold Test",
    "question": "Does the share of households paying at least 15% of income in interest improve next-year housing-payment-strain forecasts beyond persistence?",
    "history": credit.to_dict("records"),
    "segments": latest_burden.to_dict("records"),
    "backtest": credit_bt,
    "model_mae": float(np.mean([abs(x["actual"] - x["model"]) for x in credit_bt])),
    "baseline_mae": float(np.mean([abs(x["actual"] - x["persistence"]) for x in credit_bt])),
    "improvement_ci": block_ci([x["improvement"] for x in credit_bt]),
    "latest_year": int(credit.year.max()),
    "latest_burden": float(credit.iloc[-1].interest_burden_15plus_pct),
    "latest_problem": float(credit.iloc[-1].housing_payment_problem_pct),
    "limits": "Household percentages are survey/distribution measures, not exposure-weighted arrears, PD or loss. The interest-burden table ends in 2024 and the housing-payment series in 2025; the forward test is latest-vintage, not an archived real-time backtest. Household categories are not borrower records.",
}


# 2. Financial intelligence: policy-rate signal for EUR/NOK monthly changes.
fx = pd.read_csv(S / "norges_eurnok_monthly.csv", sep=";")[["TIME_PERIOD", "OBS_VALUE"]]
fx.columns = ["month", "eurnok"]
fx["date"] = pd.PeriodIndex(fx.month, freq="M").to_timestamp("M")
fx["return_pct"] = 100 * np.log(fx.eurnok).diff()
rates = pd.read_csv(S / "norges_policy_rate.csv", sep=";")
rates = rates[rates.TENOR == "SD"][["TIME_PERIOD", "OBS_VALUE"]].copy()
rates["date"] = pd.to_datetime(rates.TIME_PERIOD)
rates["month"] = rates.date.dt.to_period("M").dt.to_timestamp("M")
monthly_rate = rates.groupby("month", as_index=False).OBS_VALUE.mean().rename(columns={"OBS_VALUE": "policy_rate"})
financial = fx.merge(monthly_rate, left_on="date", right_on="month", how="inner").sort_values("date")
financial["rate_change"] = financial.policy_rate.diff()
financial["target"] = financial.return_pct.shift(-1)
financial_bt = []
start = max(72, len(financial) - 72)
for i in range(start, len(financial) - 1):
    train = financial.iloc[:i].dropna(subset=["target", "return_pct", "rate_change"])
    origin = financial.iloc[i]
    target = financial.iloc[i + 1]
    x = np.column_stack([np.ones(len(train)), train.return_pct, train.rate_change, train.policy_rate])
    beta = ridge_fit(x, train.target, 1e-3)
    prediction = float(np.array([1, origin.return_pct, origin.rate_change, origin.policy_rate]) @ beta)
    financial_bt.append({
        "month": str(target.date)[:7],
        "actual_return_pct": float(target.return_pct),
        "model_return_pct": prediction,
        "random_walk_return_pct": 0.0,
        "origin_rate": float(origin.policy_rate),
    })
for row in financial_bt:
    row["improvement"] = abs(row["actual_return_pct"]) - abs(row["actual_return_pct"] - row["model_return_pct"])
financial_history = financial.tail(144)[["date", "eurnok", "policy_rate", "return_pct", "rate_change"]].copy()
financial_history["date"] = financial_history.date.dt.strftime("%Y-%m")
R["studies"]["financial"] = {
    "title": "The Policy-Rate Signal Test",
    "question": "Does the Norwegian policy-rate signal improve next-month EUR/NOK changes relative to a random-walk baseline?",
    "history": financial_history.to_dict("records"),
    "backtest": financial_bt,
    "model_mae": float(np.mean([abs(x["actual_return_pct"] - x["model_return_pct"]) for x in financial_bt])),
    "baseline_mae": float(np.mean([abs(x["actual_return_pct"]) for x in financial_bt])),
    "direction_accuracy": float(np.mean([np.sign(x["actual_return_pct"]) == np.sign(x["model_return_pct"]) for x in financial_bt])),
    "improvement_ci": block_ci([x["improvement"] for x in financial_bt], block=3),
    "latest": financial_history.iloc[-1].to_dict(),
    "limits": "Monthly Norges Bank middle rates are indicative, not executable returns. The model omits foreign rates, risk appetite, energy prices and intervention expectations. The 72-month evaluation is latest-vintage and repeatedly re-estimated; it is not a trading strategy and includes no transaction costs.",
}


# 3. Accounting and audit: working-capital absorption and next-year cash conversion.
flow_tags = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities"],
}
instant_tags = {
    "ar": ["AccountsReceivableNetCurrent", "AccountsNotesAndLoansReceivableNetCurrent"],
    "inventory": ["InventoryNet"],
    "ap": ["AccountsPayableCurrent"],
}
accounting_records = []
for path in sorted(S.glob("sec_companyfacts_*.json")):
    data = json.loads(path.read_text())
    facts = data.get("facts", {}).get("us-gaap", {})
    periods = {}
    for metric, tags in flow_tags.items():
        candidates = []
        for priority, tag in enumerate(tags):
            for item in facts.get(tag, {}).get("units", {}).get("USD", []):
                if item.get("form") != "10-K" or item.get("filed", "9999") > CUTOFF or not item.get("start"):
                    continue
                duration = (pd.Timestamp(item["end"]) - pd.Timestamp(item["start"])).days
                if 330 <= duration <= 380 and item["end"] >= "2014-01-01":
                    candidates.append((item["end"], priority, item.get("filed", ""), tag, item))
        for end, priority, filed, tag, item in sorted(candidates, key=lambda x: (x[0], -x[1], x[2])):
            periods.setdefault(end, {})[metric] = {"value": item["val"], "tag": tag, "filed": filed, "accn": item.get("accn")}
    for metric, tags in instant_tags.items():
        candidates = []
        for priority, tag in enumerate(tags):
            for item in facts.get(tag, {}).get("units", {}).get("USD", []):
                if item.get("form") != "10-K" or item.get("filed", "9999") > CUTOFF or item.get("end", "") < "2014-01-01":
                    continue
                candidates.append((item["end"], priority, item.get("filed", ""), tag, item))
        for end, priority, filed, tag, item in sorted(candidates, key=lambda x: (x[0], -x[1], x[2])):
            periods.setdefault(end, {})[metric] = {"value": item["val"], "tag": tag, "filed": filed, "accn": item.get("accn")}
    rows = []
    for end, metrics in sorted(periods.items()):
        if all(metric in metrics for metric in ["revenue", "cfo", "ar", "inventory", "ap"]) and metrics["revenue"]["value"] > 0:
            rows.append({
                "company": data["entityName"],
                "cik": data["cik"],
                "end": end,
                "revenue_usd": metrics["revenue"]["value"],
                "cfo_usd": metrics["cfo"]["value"],
                "ar_usd": metrics["ar"]["value"],
                "inventory_usd": metrics["inventory"]["value"],
                "ap_usd": metrics["ap"]["value"],
                "metrics": metrics,
            })
    for index, row in enumerate(rows):
        row["cfo_margin_pct"] = 100 * row["cfo_usd"] / row["revenue_usd"]
        if index:
            previous = rows[index - 1]
            row["wc_absorption_pct"] = 100 * ((row["ar_usd"] - previous["ar_usd"]) + (row["inventory_usd"] - previous["inventory_usd"]) - (row["ap_usd"] - previous["ap_usd"])) / row["revenue_usd"]
        else:
            row["wc_absorption_pct"] = None
        accounting_records.append(row)

model_rows = []
for company in sorted({row["company"] for row in accounting_records}):
    rows = sorted([row for row in accounting_records if row["company"] == company], key=lambda row: row["end"])
    for index in range(2, len(rows)):
        if rows[index - 1]["wc_absorption_pct"] is None:
            continue
        model_rows.append({
            "company": company,
            "end": rows[index]["end"],
            "actual": rows[index]["cfo_margin_pct"],
            "lag_margin": rows[index - 1]["cfo_margin_pct"],
            "lag_wc": rows[index - 1]["wc_absorption_pct"],
        })
holdout_keys = {(company, row["end"]) for company in sorted({r["company"] for r in model_rows}) for row in sorted([r for r in model_rows if r["company"] == company], key=lambda r: r["end"])[-3:]}
accounting_bt = []
for row in sorted([r for r in model_rows if (r["company"], r["end"]) in holdout_keys], key=lambda r: r["end"]):
    train = [r for r in model_rows if r["end"] < row["end"] and (r["company"], r["end"]) not in holdout_keys]
    if len(train) < 12:
        continue
    x = np.array([[1, r["lag_margin"], r["lag_wc"]] for r in train])
    y = np.array([r["actual"] for r in train])
    beta = ridge_fit(x, y, 0.1)
    prediction = float(np.array([1, row["lag_margin"], row["lag_wc"]]) @ beta)
    output = {**row, "model": prediction, "persistence": row["lag_margin"]}
    output["improvement"] = abs(output["actual"] - output["persistence"]) - abs(output["actual"] - output["model"])
    accounting_bt.append(output)
R["studies"]["accounting"] = {
    "title": "The Working-Capital Warning Test",
    "question": "Does prior working-capital absorption improve next-year operating cash-flow margin forecasts beyond persistence?",
    "annual": accounting_records,
    "backtest": accounting_bt,
    "model_mae": float(np.mean([abs(x["actual"] - x["model"]) for x in accounting_bt])),
    "baseline_mae": float(np.mean([abs(x["actual"] - x["persistence"]) for x in accounting_bt])),
    "cluster_ci": cluster_ci(accounting_bt, "company", "improvement"),
    "issuers": len({x["company"] for x in accounting_records}),
    "limits": "Six technology issuers are not a representative economy-wide panel. Company Facts tags, fiscal calendars and restatements differ. Working-capital absorption covers receivables, inventory and current payables only; it excludes deferred revenue, contract assets and other accruals. Latest-vintage SEC facts are not an archived real-time backtest.",
}


# 4. Governance: ownership percentage versus voting percentage in NBIM equity holdings.
holdings = pd.read_csv(S / "nbim_equity_20260630.csv", sep=";", encoding="utf-16")
for column in ["Market Value(NOK)", "Voting", "Ownership"]:
    if column in ["Voting", "Ownership"]:
        holdings[column] = pd.to_numeric(holdings[column].astype(str).str.replace("%", "", regex=False), errors="coerce")
    else:
        holdings[column] = pd.to_numeric(holdings[column], errors="coerce")
holdings = holdings.dropna(subset=["Market Value(NOK)", "Voting", "Ownership", "Name", "Country"]).copy()
holdings["voice_gap_pp"] = holdings.Voting - holdings.Ownership
holdings["abs_voice_gap_pp"] = holdings.voice_gap_pp.abs()
total_value = holdings["Market Value(NOK)"].sum()
governance_rows = holdings[["Country", "Name", "Industry", "Market Value(NOK)", "Voting", "Ownership", "voice_gap_pp", "abs_voice_gap_pp"]].rename(columns={"Country": "country", "Name": "name", "Industry": "industry", "Market Value(NOK)": "market_value_nok", "Voting": "voting_pct", "Ownership": "ownership_pct"}).sort_values("market_value_nok", ascending=False).to_dict("records")
sensitivity = []
for threshold in [0.1, 0.25, 0.5, 1.0, 2.0]:
    selected = holdings[holdings.abs_voice_gap_pp >= threshold]
    sensitivity.append({"threshold_pp": threshold, "holdings": int(len(selected)), "value_share_pct": float(100 * selected["Market Value(NOK)"].sum() / total_value)})
R["studies"]["governance"] = {
    "title": "The Voice-to-Capital Mismatch",
    "question": "How often do reported voting rights diverge from economic ownership in the fund's listed-equity snapshot?",
    "rows": governance_rows,
    "holdings": int(len(holdings)),
    "market_value_nok": float(total_value),
    "weighted_abs_gap_pp": float(np.average(holdings.abs_voice_gap_pp, weights=holdings["Market Value(NOK)"])),
    "correlation": float(holdings[["Voting", "Ownership"]].corr().iloc[0, 1]),
    "vote_discount_value_pct": float(100 * holdings.loc[holdings.voice_gap_pp < -0.1, "Market Value(NOK)"].sum() / total_value),
    "vote_premium_value_pct": float(100 * holdings.loc[holdings.voice_gap_pp > 0.1, "Market Value(NOK)"].sum() / total_value),
    "sensitivity": sensitivity,
    "limits": "One 30 June 2026 holdings snapshot. Reported voting and ownership percentages are not legal opinions, expected influence, engagement intensity or realised governance outcomes. Share classes, lending, local rules and meeting-specific eligibility may matter; no time-series persistence test is possible from this extract.",
}


# 5. Business economics: digital readiness and next-year AI adoption.
countries = ["NO", "DK", "SE", "FI", "DE", "FR", "NL", "BE", "IE", "PL"]
business_rows = []
for country in countries:
    dii_rows, _ = jsonstat_rows(S / f"eurostat_isoc_e_dii_{country}.json")
    ai_rows, _ = jsonstat_rows(S / f"eurostat_isoc_eb_ain2_{country}.json")
    dii = pd.DataFrame(dii_rows)
    ai = pd.DataFrame(ai_rows)
    if dii.empty or ai.empty:
        continue
    dii = dii[(dii.size_emp == "GE10") & (dii.nace_r2 == "C10-S951_X_K") & (dii.indic_is == "E_DI4_GELO") & (dii.unit == "PC_ENT")][["time", "value", "geo_label"]]
    ai = ai[(ai.size_emp == "GE10") & (ai.nace_r2 == "C10-S951_X_K") & (ai.indic_is == "E_AI_TANY") & (ai.unit == "PC_ENT")][["time", "value"]]
    d2024 = dii[dii.time == "2024"]
    a2024 = ai[ai.time == "2024"]
    a2025 = ai[ai.time == "2025"]
    if d2024.empty or a2024.empty or a2025.empty:
        continue
    business_rows.append({
        "country_code": country,
        "country": str(d2024.iloc[0].geo_label),
        "digital_basic_2024_pct": float(d2024.iloc[0].value),
        "ai_use_2024_pct": float(a2024.iloc[0].value),
        "ai_use_2025_pct": float(a2025.iloc[0].value),
        "ai_change_pp": float(a2025.iloc[0].value - a2024.iloc[0].value),
    })
business = pd.DataFrame(business_rows).sort_values("country_code")
business_bt = []
for _, target in business.iterrows():
    train = business[business.country_code != target.country_code]
    x = np.column_stack([np.ones(len(train)), train.digital_basic_2024_pct, train.ai_use_2024_pct])
    y = train.ai_use_2025_pct.to_numpy()
    beta = ridge_fit(x, y, 0.1)
    prediction = float(np.clip(np.array([1, target.digital_basic_2024_pct, target.ai_use_2024_pct]) @ beta, 0, 100))
    output = {"country_code": target.country_code, "country": target.country, "year": 2025, "actual": float(target.ai_use_2025_pct), "model": prediction, "persistence": float(target.ai_use_2024_pct), "origin_digital_basic": float(target.digital_basic_2024_pct)}
    output["improvement"] = abs(output["actual"] - output["persistence"]) - abs(output["actual"] - output["model"])
    business_bt.append(output)
R["studies"]["business"] = {
    "title": "The Digital-Readiness Conversion Test",
    "question": "Does a basic digital-intensity measure improve next-year AI-adoption forecasts beyond adoption persistence?",
    "history": business_rows,
    "backtest": business_bt,
    "model_mae": float(np.mean([abs(x["actual"] - x["model"]) for x in business_bt])),
    "baseline_mae": float(np.mean([abs(x["actual"] - x["persistence"]) for x in business_bt])),
    "country_ci": block_ci([x["improvement"] for x in business_bt], block=1),
    "latest_correlation": float(business[["digital_basic_2024_pct", "ai_use_2025_pct"]].corr().iloc[0, 1]),
    "limits": "Ten-country leave-one-country-out validation, using 2024 DII version 4 and 2024 AI use to estimate 2025 AI use. This is cross-country validation, not a new-year temporal backtest. Repeated enterprise surveys are not firm-level transitions, and supplied dissemination data do not include microdata or sampling standard errors. The interval is descriptive, not a design-based survey interval.",
}


# 6. Public finance: net government interest position and policy-rate pass-through.
fiscal_rows, _ = jsonstat_rows(S / "ssb_10721_response.json")
fiscal = pd.DataFrame(fiscal_rows)
fiscal["value"] = pd.to_numeric(fiscal.value, errors="coerce")
fiscal["year"] = fiscal.Tid.astype(int)
fiscal = fiscal[fiscal.Sektor == "C_OFF"]
fiscal_wide = fiscal.pivot(index="year", columns="Art", values="value").reset_index().rename(columns={"A51": "interest_income_nok_million", "B41": "interest_expense_nok_million"})
annual_policy = rates.groupby(rates.date.dt.year).OBS_VALUE.mean().rename("policy_rate").reset_index().rename(columns={"date": "year"})
annual_policy.columns = ["year", "policy_rate"]
public = fiscal_wide.merge(annual_policy, on="year", how="inner").sort_values("year")
public["net_interest_nok_million"] = public.interest_income_nok_million - public.interest_expense_nok_million
public["rate_change"] = public.policy_rate.diff()
public_bt = []
for i in range(7, len(public)):
    train = public.iloc[:i].copy()
    supervised = pd.DataFrame({"y": train.net_interest_nok_million.shift(-1), "lag": train.net_interest_nok_million, "rate": train.policy_rate, "rate_change": train.rate_change}).dropna()
    if len(supervised) < 6:
        continue
    beta = ridge_fit(np.column_stack([np.ones(len(supervised)), supervised.lag / 1000, supervised.rate, supervised.rate_change]), supervised.y / 1000, 0.1)
    origin = public.iloc[i - 1]
    target = public.iloc[i]
    prediction = 1000 * float(np.array([1, origin.net_interest_nok_million / 1000, origin.policy_rate, origin.rate_change]) @ beta)
    output = {"year": int(target.year), "actual": float(target.net_interest_nok_million), "model": prediction, "persistence": float(origin.net_interest_nok_million), "origin_rate": float(origin.policy_rate)}
    output["improvement"] = abs(output["actual"] - output["persistence"]) - abs(output["actual"] - output["model"])
    public_bt.append(output)
public_bt = public_bt[-10:]
R["studies"]["public_finance"] = {
    "title": "The Sovereign Interest-Pass-Through Test",
    "question": "Does the policy-rate signal improve next-year forecasts of Norway's consolidated government net interest position beyond persistence?",
    "history": public.to_dict("records"),
    "backtest": public_bt,
    "model_mae_nok_million": float(np.mean([abs(x["actual"] - x["model"]) for x in public_bt])),
    "baseline_mae_nok_million": float(np.mean([abs(x["actual"] - x["persistence"]) for x in public_bt])),
    "improvement_ci_nok_million": block_ci([x["improvement"] for x in public_bt]),
    "latest": public.iloc[-1].to_dict(),
    "limits": "Nominal consolidated general-government interest flows are not the structural non-oil balance, fiscal-rule headroom, debt duration or sovereign solvency. Annual average policy rates are a coarse signal; asset composition, currency, maturity, GPFG income and accounting classifications are omitted. Latest-vintage, not real-time-vintage validation.",
}


# 7. Art and capital: public subsidy share and museum attendance resilience.
museum_fin_rows, _ = jsonstat_rows(S / "ssb_09542_response.json")
museum_visit_rows, _ = jsonstat_rows(S / "ssb_09539_response.json")
museum_fin = pd.DataFrame(museum_fin_rows)
museum_fin["value"] = pd.to_numeric(museum_fin.value, errors="coerce")
museum_fin["year"] = museum_fin.Tid.astype(int)
museum_fin = museum_fin.pivot(index="year", columns="ContentsCode", values="value").reset_index().rename(columns={"Inntekter": "revenue_nok_million", "Utgifter": "expenditure_nok_million", "Loyvingar": "public_contributions_nok_million"})
museum_vis = pd.DataFrame(museum_visit_rows)
museum_vis["value"] = pd.to_numeric(museum_vis.value, errors="coerce")
museum_vis["year"] = museum_vis.Tid.astype(int)
museum_vis = museum_vis.pivot(index="year", columns="MuseBesok", values="value").reset_index().rename(columns={"01": "individual_visits", "02": "group_visits", "03": "paying_visits"})
art = museum_fin.merge(museum_vis, on="year", how="inner").sort_values("year")
art["total_visits"] = art.individual_visits + art.group_visits
art["subsidy_share_pct"] = 100 * art.public_contributions_nok_million / art.revenue_nok_million
art["own_revenue_nok_million"] = art.revenue_nok_million - art.public_contributions_nok_million
art["own_revenue_per_visit_nok"] = 1_000_000 * art.own_revenue_nok_million / art.total_visits
art_bt = []
for i in range(7, len(art)):
    train = art.iloc[:i].copy()
    supervised = pd.DataFrame({"y": train.total_visits.shift(-1), "lag": train.total_visits, "subsidy": train.subsidy_share_pct}).dropna()
    if len(supervised) < 6:
        continue
    beta = ridge_fit(np.column_stack([np.ones(len(supervised)), supervised.lag / 1e6, supervised.subsidy]), supervised.y / 1e6, 0.1)
    origin = art.iloc[i - 1]
    target = art.iloc[i]
    prediction = 1e6 * float(np.array([1, origin.total_visits / 1e6, origin.subsidy_share_pct]) @ beta)
    output = {"year": int(target.year), "actual": float(target.total_visits), "model": prediction, "persistence": float(origin.total_visits), "origin_subsidy_share_pct": float(origin.subsidy_share_pct)}
    output["improvement"] = abs(output["actual"] - output["persistence"]) - abs(output["actual"] - output["model"])
    art_bt.append(output)
art_bt = art_bt[-10:]
nonpandemic = [x for x in art_bt if x["year"] not in [2020, 2021]]
R["studies"]["art"] = {
    "title": "The Museum Subsidy Resilience Test",
    "question": "Does the public-contribution share improve next-year museum-attendance forecasts beyond persistence?",
    "history": art.to_dict("records"),
    "backtest": art_bt,
    "model_mae_visits": float(np.mean([abs(x["actual"] - x["model"]) for x in art_bt])),
    "baseline_mae_visits": float(np.mean([abs(x["actual"] - x["persistence"]) for x in art_bt])),
    "improvement_ci_visits": block_ci([x["improvement"] for x in art_bt]),
    "nonpandemic_model_mae": float(np.mean([abs(x["actual"] - x["model"]) for x in nonpandemic])),
    "nonpandemic_baseline_mae": float(np.mean([abs(x["actual"] - x["persistence"]) for x in nonpandemic])),
    "latest": art.iloc[-1].to_dict(),
    "limits": "National museum aggregates combine institutions and changing populations. Individual and group visits are summed as disjoint categories; paying visits overlap and are not added. Nominal revenue is not deflated. Public contributions may respond to need, creating endogeneity; the exercise is predictive, not causal. The 2025 questionnaire revision prevents extending the same visit definition without a documented bridge.",
}


manifest = []
for path in sorted(S.iterdir()):
    if path.is_file():
        manifest.append({"file": path.name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "extracted": CUTOFF})
(O / "extraction_manifest.json").write_text(json.dumps(manifest, indent=2))
(O / "results.json").write_text(json.dumps(scalar(R), indent=2, ensure_ascii=False, allow_nan=False))
summary = {
    key: {
        metric: value
        for metric, value in study.items()
        if metric in {"model_mae", "baseline_mae", "model_mae_nok_million", "baseline_mae_nok_million", "model_mae_visits", "baseline_mae_visits", "holdings", "weighted_abs_gap_pp", "latest_correlation"}
    }
    for key, study in R["studies"].items()
}
print(json.dumps(scalar(summary), indent=2))
