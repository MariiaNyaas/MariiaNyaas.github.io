#!/usr/bin/env python3
"""Build observed market inputs for the practical currency decision dashboard.

The research v2 forecast outputs are deliberately untouched. This separate data
layer supplies reference FX quotes, exact historical FX-only replays and dated
primary-source facts. It never invents holdings, asset returns or OIS curves.
"""
from __future__ import annotations

import argparse
import concurrent.futures
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT.parent
RAW = ROOT / "raw"
DATA = ROOT / "data"
CURRENCIES = ["EUR", "USD", "GBP", "SEK", "CHF", "JPY"]
FX_REFERENCE = "https://www.norges-bank.no/en/topics/Statistics/exchange_rates/"
NB_POLICY_REFERENCE = "https://www.norges-bank.no/en/topics/Monetary-policy/Policy-rate/"
ECB_POLICY_REFERENCE = "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html"
UA = "NordVeritasResearch/3.0 (public statistical data; reproducibility audit)"


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def definitions(end):
    return {
        "fx_all": {
            "url": "https://data.norges-bank.no/api/data/EXR/B."
            + "+".join(CURRENCIES)
            + f".NOK.SP?format=csv&startPeriod=2000-01-01&endPeriod={end}&locale=en",
            "publisher": "Norges Bank",
            "seriesIds": [f"EXR/B.{ccy}.NOK.SP" for ccy in CURRENCIES],
            "referenceUrl": FX_REFERENCE,
        },
        "nb_policy": {
            "url": "https://data.norges-bank.no/api/data/IR/B.KPRA.SD.R"
            f"?format=csv&startPeriod=2026-01-01&endPeriod={end}&locale=en",
            "publisher": "Norges Bank", "seriesIds": ["IR/B.KPRA.SD.R"],
            "referenceUrl": NB_POLICY_REFERENCE,
        },
        "ecb_policy": {
            "url": "https://data-api.ecb.europa.eu/service/data/FM/"
            "D.U2.EUR.4F.KR.DFR+MRR_FR+MRR_RT.LEV"
            f"?startPeriod=2026-01-01&endPeriod={end}&format=csvdata",
            "publisher": "European Central Bank",
            "seriesIds": ["FM.D.U2.EUR.4F.KR.DFR.LEV", "FM.D.U2.EUR.4F.KR.MRR_FR.LEV", "FM.D.U2.EUR.4F.KR.MRR_RT.LEV"],
            "referenceUrl": ECB_POLICY_REFERENCE,
        },
    }


def download(name, definition, refresh, timeout):
    path = RAW / f"decision_{name}.csv"
    receipt_path = RAW / f"decision_{name}_download.json"
    if not refresh and path.exists() and receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        payload = path.read_bytes()
        if (receipt.get("requested_url") == definition["url"]
                and receipt.get("sha256") == sha256(payload)
                and receipt.get("bytes") == len(payload)):
            return name, receipt
    request = urllib.request.Request(definition["url"], headers={"User-Agent": UA, "Accept": "text/csv,*/*"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
        if not payload or b"<html" in payload[:500].lower():
            raise ValueError(f"{name}: expected source CSV, not HTML/empty response")
        receipt = {
            "requested_url": definition["url"], "actual_download_url": response.geturl(),
            "retrieved_utc": now(), "bytes": len(payload), "sha256": sha256(payload),
            "content_type": response.headers.get("Content-Type"),
            "last_modified": response.headers.get("Last-Modified"),
        }
    path.write_bytes(payload)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    return name, receipt


def number(value):
    # English-locale source quotes can contain thousands separators, e.g.
    # CHF "1,167.92" NOK per 100 CHF. A comma is not a decimal separator here.
    s = str(value).strip()
    if s in {"", "nan", "NaN", "."}:
        return np.nan
    if not re.fullmatch(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", s):
        raise ValueError(f"Unrecognised English-locale number: {s!r}")
    return float(s.replace(",", ""))


def series(frame):
    result = pd.Series(pd.to_numeric(frame.OBS_VALUE, errors="raise").to_numpy(),
                       index=pd.to_datetime(frame.TIME_PERIOD, errors="raise")).sort_index()
    if result.index.has_duplicates:
        raise ValueError("Duplicate source observations")
    return result.dropna()


def source_facts():
    return [
        {
            "id": "currency-translation", "kind": "source-fact",
            "title": "NOK translation is not investment alpha",
            "text": "NBIM reports returns in NOK and in its benchmark currency basket. Changes in NOK affect the reported NOK result but do not, by themselves, change the fund's international purchasing power.",
            "asOf": "2026-11-24", "source": "Norges Bank Investment Management",
            "url": "https://www.nbim.no/en/investments/returns/methodology-for-the-calculation-of-returns/",
            "dateMeaning": "Source verified on this date; this is a methodological statement, not a market observation.",
        },
        {
            "id": "hedge-liquidity", "kind": "source-fact",
            "title": "A hedge can protect value and demand liquidity",
            "text": "In Norges Bank's survey of 10 Norwegian asset managers, a hypothetical sudden 20% NOK depreciation implied NOK 104 billion of variation margin at 2025 Q1, against approximately NOK 680 billion of hedged assets. This is an industry survey scenario, not NBIM's margin requirement or an observed cash outflow.",
            "asOf": "2025-03-31", "source": "Norges Bank, Financial Stability Report 2025-1",
            "url": "https://www.norges-bank.no/en/news-events/publications/Financial-Stability-report/2025-1-financial-stability/web-report-2025-1-financial-stability/",
            "dateMeaning": "Survey reference quarter end; the stated cash requirement is conditional on a stress scenario.",
            "metrics": {"managerCount": 10, "hedgedAssetsNokBillionApprox": 680, "variationMarginNokBillion": 104, "assumedNokDepreciationPercent": 20},
        },
        {
            "id": "multiple-risk-lenses", "kind": "source-fact",
            "title": "Assess value, concentrations and liquidity together",
            "text": "NBIM's market-risk policy covers absolute and benchmark-relative risk using concentration, volatility and correlation, factor, and liquidity dimensions. Its policy calls for several approaches and regular stress testing.",
            "asOf": "2024-06-12", "source": "Norges Bank Investment Management, Market Risk Management policy",
            "url": "https://www.nbim.no/en/about-us/about-the-fund/governance-structure/policies/market-risk-management/",
            "dateMeaning": "Last-updated date displayed on the policy; verified 24 November 2026.",
        },
    ]


def reported_actuals():
    bridge = {
        "period": "2025", "publishedAt": "2026-01-29",
        "kind": "reported-historical-fund-fact",
        "investmentReturnNokBn": 2362, "investmentReturnLabel": "Accounting return",
        "fxTranslationNokBn": -1155, "netFlowsNokBn": 319,
        "netFlowsLabel": "Inflow after management costs",
        "valueChangeNokBn": 1526, "returnPct": 15.1,
        "closingFundValueNokBn": 21268,
        "source": "Norges Bank Investment Management, Strong return in 2025",
        "url": "https://www.nbim.no/en/news-and-insights/the-press/press-releases/2026/strong-return-in-2025/",
        "verifiedAt": "2026-11-24",
        "note": "Published calendar-2025 fund totals in NOK billions, rounded by the source. Accounting return + FX translation + inflow after management costs = change in fund value. The 15.1% reported return is a return measure, not the percentage change in the NOK fund value. This historical bridge supplies no current portfolio holdings or trading signal.",
    }
    if bridge["investmentReturnNokBn"] + bridge["fxTranslationNokBn"] + bridge["netFlowsNokBn"] != bridge["valueChangeNokBn"]:
        raise ValueError("Reported NBIM bridge fails to reconcile")
    return {"nbimBridge": bridge}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--end-date", default="2026-11-23", help="Frozen latest completed source date; explicit refresh does not silently advance it.")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()
    cap = date.fromisoformat(args.end_date)
    oslo = datetime.now(ZoneInfo("Europe/Oslo"))
    if cap > oslo.date() or (cap == oslo.date() and oslo.hour < 16):
        raise ValueError("Requested reference date is not yet publishable at Norges Bank's approximately 16:00 local publication time")
    RAW.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    specs = definitions(args.end_date)
    receipts = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(download, name, spec, args.refresh, args.timeout) for name, spec in specs.items()]
        for future in concurrent.futures.as_completed(futures):
            name, receipt = future.result()
            receipts[name] = receipt

    raw = pd.read_csv(RAW / "decision_fx_all.csv", sep=";", dtype={"OBS_VALUE": str})
    raw = raw[(raw.FREQ == "B") & (raw.QUOTE_CUR == "NOK") & (raw.TENOR == "SP") & raw.BASE_CUR.isin(CURRENCIES)].copy()
    raw["date"] = pd.to_datetime(raw.TIME_PERIOD, errors="raise")
    if (raw.date.dt.date > cap).any():
        raise ValueError("Source returned an observation later than requested cap")
    raw["quoted"] = raw.OBS_VALUE.map(number)
    raw["multiplier"] = pd.to_numeric(raw.UNIT_MULT, errors="raise")
    if raw.multiplier.isna().any() or not raw.multiplier.isin([0, 2]).all():
        raise ValueError("Unexpected/missing source unit multiplier; manual review required")
    raw["per_one"] = (raw.quoted / (10.0 ** raw.multiplier)).round(12)
    observed = raw.dropna(subset=["per_one"])
    if (observed.per_one <= 0).any() or not np.isfinite(observed.per_one).all():
        raise ValueError("Non-positive or nonfinite observed exchange rate")
    if observed.duplicated(["date", "BASE_CUR"]).any():
        raise ValueError("Duplicate currency/date reference quote")
    if not np.allclose(observed.per_one * 10.0 ** observed.multiplier, observed.quoted, rtol=1e-13, atol=1e-12):
        raise ValueError("Unit normalization does not round-trip")
    daily = observed.pivot(index="date", columns="BASE_CUR", values="per_one").sort_index().reindex(columns=CURRENCIES)
    daily.index.name = "date"
    daily.columns.name = None
    daily_path = DATA / "decision_fx_daily.csv"
    daily.to_csv(daily_path, float_format="%.12g", na_rep="")
    common = daily.dropna(how="any")
    if common.empty:
        raise ValueError("No common observed FX date")
    latest_date = common.index.max()
    if any(daily[c].last_valid_index() != latest_date for c in CURRENCIES):
        raise ValueError("Latest quote dates differ; explicit mixed-date market display required")
    market = {}
    normalizations = {}
    for ccy in CURRENCIES:
        latest_raw = observed[(observed.BASE_CUR == ccy) & (observed.date == latest_date)].iloc[0]
        multipliers = sorted(int(v) for v in observed.loc[observed.BASE_CUR == ccy, "multiplier"].unique())
        market[ccy] = {
            "spot": float(common.loc[latest_date, ccy]), "asOf": latest_date.date().isoformat(),
            "kind": "observed-market", "source": "Norges Bank", "url": FX_REFERENCE,
            "seriesId": f"EXR/B.{ccy}.NOK.SP", "unit": f"NOK per 1 {ccy}",
            "quotedValue": float(latest_raw.quoted), "unitMultiplier": int(latest_raw.multiplier),
            "sourceUnits": int(10 ** latest_raw.multiplier),
            "retrievedAt": receipts["fx_all"]["retrieved_utc"],
        }
        normalizations[ccy] = {"observedUnitMultipliers": multipliers, "formula": "NOK per one foreign unit = OBS_VALUE / 10**UNIT_MULT", "latestRawQuote": float(latest_raw.quoted), "latestPerOneQuote": market[ccy]["spot"]}
    market["NOK"] = {"spot": 1, "asOf": latest_date.date().isoformat(), "kind": "currency-identity", "source": "Currency identity (NOK/NOK = 1)", "url": FX_REFERENCE, "unit": "NOK per 1 NOK", "quotedValue": 1, "unitMultiplier": 0, "sourceUnits": 1, "note": "Arithmetic identity for the base currency; not a seventh observed exchange-rate series."}

    # A compact display series: actual last common fixing within each calendar
    # month, plus the most recent 120 common daily fixings. No resampled dates.
    month_dates = common.groupby(common.index.to_period("M")).tail(1).index
    history_dates = month_dates.union(common.tail(120).index).sort_values()
    history = [{"date": stamp.date().isoformat(), **{ccy: float(common.loc[stamp, ccy]) for ccy in CURRENCIES}} for stamp in history_dates]
    windows = [
        ("covid-2020", "February–March 2020", "2020-02-19", "2020-03-20"),
        ("energy-2022", "February–March 2022", "2022-02-23", "2022-03-08"),
        ("april-2025", "April 2025", "2025-04-01", "2025-04-09"),
    ]
    scenarios = []
    for key, label, start, end in windows:
        if pd.Timestamp(start) not in common.index or pd.Timestamp(end) not in common.index:
            raise ValueError(f"Historical endpoint is not an actual common fixing: {start} / {end}")
        start_values = {ccy: float(common.loc[start, ccy]) for ccy in CURRENCIES}
        end_values = {ccy: float(common.loc[end, ccy]) for ccy in CURRENCIES}
        shocks = {ccy: (end_values[ccy] / start_values[ccy] - 1) * 100 for ccy in CURRENCIES}
        for ccy in CURRENCIES:
            if not np.isclose(start_values[ccy] * (1 + shocks[ccy] / 100), end_values[ccy], rtol=1e-13):
                raise ValueError("Historical shock back-calculation failed")
        start_values["NOK"], end_values["NOK"], shocks["NOK"] = 1, 1, 0
        scenarios.append({
            "id": key, "label": label, "kind": "observed-fx-replay", "unit": "percent",
            "startDate": start, "endDate": end, "fxShocks": shocks,
            "startSpots": start_values, "endSpots": end_values,
            "source": "Norges Bank", "url": FX_REFERENCE,
            "note": "Observed endpoint-to-endpoint FX changes only. Asset-price returns, cash flows and collateral conditions are not supplied by this replay. These deliberately selected historical windows are not probabilities or causal estimates.",
        })

    nb = pd.read_csv(RAW / "decision_nb_policy.csv", sep=";")
    nb = nb[(nb.INSTRUMENT_TYPE == "KPRA") & (nb.TENOR == "SD")]
    nb_series = series(nb)
    ecb = pd.read_csv(RAW / "decision_ecb_policy.csv")
    ecb_series = {key: series(group) for key, group in ecb.groupby("PROVIDER_FM_ID")}
    mro_overlap = pd.concat([ecb_series["MRR_FR"], ecb_series["MRR_RT"]], axis=1).dropna()
    if not np.allclose(mro_overlap.iloc[:, 0], mro_overlap.iloc[:, 1], rtol=0, atol=1e-12):
        raise ValueError("Conflicting ECB MRO source observations")
    mro = ecb_series["MRR_FR"].combine_first(ecb_series["MRR_RT"]).sort_index()
    rate_sets = {"NB_POLICY": (nb_series, "Norges Bank", NB_POLICY_REFERENCE, "nb_policy"), "ECB_DFR": (ecb_series["DFR"], "European Central Bank", ECB_POLICY_REFERENCE, "ecb_policy"), "ECB_MRO": (mro, "European Central Bank", ECB_POLICY_REFERENCE, "ecb_policy")}
    policy_rates = {}
    for key, (values, publisher, url, source_key) in rate_sets.items():
        if values.empty or values.index.max().date() > cap:
            raise ValueError("Empty or future policy rate observations")
        policy_rates[key] = {"value": float(values.iloc[-1]), "asOf": values.index.max().date().isoformat(), "unit": "percent per annum", "source": publisher, "url": url, "kind": "observed-policy-rate", "retrievedAt": receipts[source_key]["retrieved_utc"], "note": "Observed effective policy rate. Not an OIS curve, policy expectation or executable funding quote."}
    generated = now()
    manifest = {
        "version": "3.0", "dataset": "Observed currency reference data for the decision dashboard",
        "generatedAt": generated, "requestedStart": "2000-01-01", "requestedEnd": args.end_date,
        "baseCurrency": "NOK", "normalizedUnit": "NOK per one foreign currency unit",
        "normalization": normalizations,
        "missingValuePolicy": "Missing source observations remain empty. No interpolation, forward-fill, backward-fill or synthetic cross-rate construction.",
        "vintage": "Latest source vintage on the recorded retrieval dates. Historical corrections may revise a later download; this is not an archived point-in-time data set.",
        "quoteMeaning": "Indicative reference middle rates, not executable bid/ask quotes. Source collection field refers to the ECB concertation time of 14:15; Norges Bank daily publication is approximately 16:00 local time. Observation date and download time are distinct.",
        "quoteReference": FX_REFERENCE,
        "sources": {name: {**spec, **receipts[name], "rawCache": f"raw/decision_{name}.csv"} for name, spec in specs.items()},
        "dailyFile": {"path": "model/data/decision_fx_daily.csv", "sha256": sha256(daily_path.read_bytes()), "bytes": daily_path.stat().st_size, "rows": len(daily), "columns": ["date", *CURRENCIES], "firstDate": daily.index.min().date().isoformat(), "lastDate": daily.index.max().date().isoformat(), "commonCompleteRows": len(common), "missingByCurrency": {ccy: int(daily[ccy].isna().sum()) for ccy in CURRENCIES}},
        "historicalScenarioFormula": "100 * (observed end quote / observed start quote - 1); positive means more NOK per foreign unit. Exact actual common fixing dates; no asset returns or model forecasts included.",
        "validation": {"positiveFiniteQuotes": True, "duplicateCurrencyDates": 0, "unitNormalizationRoundTrips": int(len(observed)), "historicalShockBackCalculations": len(scenarios) * len(CURRENCIES), "futureObservationsUsed": 0, "latestCurrencyDatesEqual": True, "ecbMroOverlapRowsChecked": int(len(mro_overlap))},
        "sourceFacts": source_facts(), "reportedActuals": reported_actuals(),
        "researchSeparation": "The v2 EUR/NOK model remains frozen through October 2026. Updated reference quotes and historical replays here do not rerun or validate that forecasting model.",
    }
    manifest_path = DATA / "decision_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    dashboard = {
        "version": "3.0", "generatedAt": generated,
        "marketAsOf": latest_date.date().isoformat(), "baseCurrency": "NOK", "baseCurrencyRate": 1,
        "market": market, "policyRates": policy_rates,
        "history": history, "historySampling": "Actual last common fixing in each month plus last 120 common daily fixings. The current partial month is an observed latest date, not a projected month end.",
        "historicalScenarios": scenarios, "facts": source_facts(), "actuals": reported_actuals(),
        "provenance": {"manifestUrl": "model/data/decision_manifest.json", "dailyCsvUrl": "model/data/decision_fx_daily.csv", "methodUrl": "model/DECISION_DATA.md", "normalization": "NOK per one foreign currency unit = source OBS_VALUE / 10**UNIT_MULT", "referenceQuoteNote": manifest["quoteMeaning"], "sourceVintage": manifest["vintage"], "researchSeparation": manifest["researchSeparation"], "holdingsNote": "This file supplies no portfolio holdings. Any dashboard demo holdings and contract terms are illustrative user assumptions, never observed exposures.", "manifestSha256": sha256(manifest_path.read_bytes()), "dailySha256": sha256(daily_path.read_bytes())},
    }
    (PAGE / "decision-data.json").write_text(json.dumps(dashboard, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")
    print(json.dumps({"marketAsOf": dashboard["marketAsOf"], "market": market, "policyRates": policy_rates, "dailyRows": len(daily), "historyRows": len(history), "historicalScenarios": scenarios, "validation": manifest["validation"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
