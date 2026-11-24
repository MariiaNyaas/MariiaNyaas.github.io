#!/usr/bin/env python3
"""Download and normalize public daily market series for the EUR/NOK study.

Run without arguments to reuse checksum-verified raw downloads for 2000-01 to
2026-10.  Pass --refresh to fetch a new latest vintage.  This is NOT an archived
real-time data set.  Predictor publication lags are applied by the model runner,
not silently inside this observation-month file.
"""
from __future__ import annotations

import argparse
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
DATA = ROOT / "data"
UA = "NordVeritasResearch/2.0 (public statistical data; reproducibility audit)"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def source_definitions(start, end):
    start_date = f"{start}-01"
    end_date = str(pd.Period(end, freq="M").end_time.date())
    return {
        "fx": {
            "url": "https://data.norges-bank.no/api/data/EXR/B.EUR.NOK.SP"
            f"?format=csv&startPeriod={start_date}&endPeriod={end_date}&locale=en",
            "publisher": "Norges Bank",
            "series_id": "EXR/B.EUR.NOK.SP",
            "reference_url": "https://www.norges-bank.no/en/topics/Statistics/exchange_rates/",
            "rights": "Norges Bank public statistical data; attribute Norges Bank. Indicative reference rates, not executable quotes.",
        },
        "nb": {
            "url": "https://data.norges-bank.no/api/data/IR/B.KPRA.SD.R"
            f"?format=csv&startPeriod=1999-12-01&endPeriod={end_date}&locale=en",
            "publisher": "Norges Bank",
            "series_id": "IR/B.KPRA.SD.R",
            "reference_url": "https://www.norges-bank.no/en/topics/Monetary-policy/Policy-rate/",
            "rights": "Norges Bank public statistical data; attribute Norges Bank.",
        },
        "ecb": {
            "url": "https://data-api.ecb.europa.eu/service/data/FM/"
            "D.U2.EUR.4F.KR.DFR+MRR_FR+MRR_RT.LEV"
            f"?startPeriod=1999-01-01&endPeriod={end_date}&format=csvdata",
            "publisher": "European Central Bank",
            "series_id": ["FM.D.U2.EUR.4F.KR.DFR.LEV", "FM.D.U2.EUR.4F.KR.MRR_FR.LEV", "FM.D.U2.EUR.4F.KR.MRR_RT.LEV"],
            "reference_url": "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html",
            "rights": "ECB public statistical data; attribute ECB and identify calculations. Source terms apply.",
        },
        "brent": {
            "url": "https://fred.stlouisfed.org/graph/fredgraph.csv"
            f"?id=DCOILBRENTEU&cosd={start_date}&coed={end_date}",
            "publisher": "US Energy Information Administration, distributed by FRED",
            "series_id": "DCOILBRENTEU",
            "reference_url": "https://fred.stlouisfed.org/series/DCOILBRENTEU",
            "primary_reference_url": "https://www.eia.gov/dnav/pet/hist/RBRTED.htm",
            "rights": "EIA federal statistical data distributed by FRED; attribute EIA and FRED. Source and FRED terms apply.",
        },
        "vix": {
            "url": "https://fred.stlouisfed.org/graph/fredgraph.csv"
            f"?id=VIXCLS&cosd={start_date}&coed={end_date}",
            "publisher": "Cboe, distributed by FRED",
            "series_id": "VIXCLS",
            "reference_url": "https://fred.stlouisfed.org/series/VIXCLS",
            "primary_reference_url": "https://www.cboe.com/tradable_products/vix/vix_historical_data/",
            "rights": "Cboe proprietary index data; FRED public accessibility is not a blanket commercial redistribution licence. Attribute Cboe/FRED and observe source terms.",
        },
        "usd": {
            "url": "https://fred.stlouisfed.org/graph/fredgraph.csv"
            f"?id=DTWEXBGS&cosd={start_date}&coed={end_date}",
            "publisher": "Board of Governors of the Federal Reserve System, distributed by FRED",
            "series_id": "DTWEXBGS",
            "reference_url": "https://fred.stlouisfed.org/series/DTWEXBGS",
            "primary_reference_url": "https://www.federalreserve.gov/releases/h10/",
            "rights": "Federal Reserve public statistical data distributed by FRED; attribute Board of Governors/FRED. Source and FRED terms apply.",
        },
    }


def download(name, definition, refresh, timeout):
    path = RAW / f"market_{name}.csv"
    receipt_path = RAW / f"market_{name}_download.json"
    url = definition["url"]
    if not refresh and path.exists() and receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        payload = path.read_bytes()
        if (receipt.get("requested_url") == url
                and receipt.get("sha256") == sha256(payload)
                and receipt.get("bytes") == len(payload)):
            return name, receipt
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/csv,*/*"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
        if not payload or b"<html" in payload[:500].lower():
            raise ValueError(f"{name}: expected CSV, received an empty or HTML response")
        receipt = {
            "name": name, "requested_url": url, "actual_download_url": response.geturl(),
            "retrieved_utc": utc_now(), "bytes": len(payload), "sha256": sha256(payload),
            "content_type": response.headers.get("Content-Type"),
            "last_modified": response.headers.get("Last-Modified"),
        }
    path.write_bytes(payload)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    return name, receipt


def as_series(frame, date_column="TIME_PERIOD", value_column="OBS_VALUE"):
    dates = pd.to_datetime(frame[date_column], errors="raise")
    values = pd.to_numeric(frame[value_column], errors="coerce")
    series = pd.Series(values.to_numpy(), index=dates).sort_index()
    if series.index.has_duplicates:
        raise ValueError("Conflicting or duplicate daily rows; series selection needs review")
    return series.dropna()


def monthly(series, periods, aggregation):
    grouped = series.groupby(series.index.to_period("M"))
    result = grouped.mean() if aggregation == "mean" else grouped.last()
    return result.reindex(periods)


def daily_summary(series, periods):
    valid = series[series.index.to_period("M").isin(periods)]
    groups = valid.groupby(valid.index.to_period("M"))
    return {
        "first_observation": str(valid.index.min().date()) if len(valid) else None,
        "last_observation": str(valid.index.max().date()) if len(valid) else None,
        "valid_daily_observations": int(len(valid)),
        "observations_per_month": {str(k): int(v) for k, v in groups.count().items()},
        "last_observation_date_per_month": {str(k): str(g.index.max().date()) for k, g in groups},
    }


def last_change(series):
    changes = series[series.diff().fillna(0).abs() > 1e-12]
    return str(changes.index.max().date()) if len(changes) else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-month", default="2000-01")
    parser.add_argument("--end-month", default="2026-10")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    periods = pd.period_range(args.start_month, args.end_month, freq="M")
    if not len(periods):
        raise ValueError("Empty monthly period")
    RAW.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    definitions = source_definitions(args.start_month, args.end_month)
    receipts = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(download, name, spec, args.refresh, args.timeout)
                   for name, spec in definitions.items()]
        for future in concurrent.futures.as_completed(futures):
            name, receipt = future.result()  # Fail visibly: do not manufacture an absent source.
            receipts[name] = receipt

    fx_frame = pd.read_csv(RAW / "market_fx.csv", sep=";")
    fx_frame = fx_frame[(fx_frame.BASE_CUR == "EUR") & (fx_frame.QUOTE_CUR == "NOK") & (fx_frame.TENOR == "SP")]
    nb_frame = pd.read_csv(RAW / "market_nb.csv", sep=";")
    nb_frame = nb_frame[(nb_frame.TENOR == "SD") & (nb_frame.INSTRUMENT_TYPE == "KPRA")]
    ecb_frame = pd.read_csv(RAW / "market_ecb.csv")
    ecb = {key: as_series(group) for key, group in ecb_frame.groupby("PROVIDER_FM_ID")}
    overlap = pd.concat([ecb["MRR_FR"].rename("fixed"), ecb["MRR_RT"].rename("minimum_bid")], axis=1).dropna()
    mismatches = overlap[np.abs(overlap.fixed - overlap.minimum_bid) > 1e-10]
    if len(mismatches):
        raise ValueError(f"ECB MRO series disagree on {len(mismatches)} overlapping daily observations")
    # Only combine observations on the same actual calendar day. No ffill, no
    # artificial continuation of discontinued fixed-rate tenders across 2000-08.
    mro = ecb["MRR_FR"].combine_first(ecb["MRR_RT"]).sort_index()
    series = {
        "spot_eurnok": as_series(fx_frame),
        "nb_policy": as_series(nb_frame),
        "ecb_dfr": ecb["DFR"],
        "ecb_mro": mro,
    }
    for name, column, value_column in [("brent", "brent", "DCOILBRENTEU"), ("vix", "vix", "VIXCLS"), ("usd", "usd_broad", "DTWEXBGS")]:
        frame = pd.read_csv(RAW / f"market_{name}.csv", na_values=[".", ""])
        date_column = "observation_date" if "observation_date" in frame.columns else "DATE"
        series[column] = as_series(frame, date_column, value_column)
    aggregations = {column: ("mean" if column in {"brent", "vix"} else "last") for column in series}
    result = pd.DataFrame({column: monthly(values, periods, aggregations[column]) for column, values in series.items()}, index=periods)
    if (result.spot_eurnok.dropna() <= 0).any():
        raise ValueError("Non-positive EUR/NOK spot quote")
    for column in ["spot_eurnok", "nb_policy", "ecb_dfr", "ecb_mro", "brent", "vix"]:
        if result[column].isna().any():
            raise ValueError(f"Unexpected missing month in {column}; investigate source coverage")
    result.index = result.index.astype(str)
    result.index.name = "month"
    output = DATA / "market.csv"
    result.to_csv(output, float_format="%.10g", na_rep="")

    source_keys = {"spot_eurnok": "fx", "nb_policy": "nb", "ecb_dfr": "ecb", "ecb_mro": "ecb", "brent": "brent", "vix": "vix", "usd_broad": "usd"}
    units = {"spot_eurnok": "NOK per EUR", "nb_policy": "% per annum", "ecb_dfr": "% per annum", "ecb_mro": "% per annum", "brent": "USD per barrel", "vix": "VIX index points", "usd_broad": "Index, January 2006 = 100"}
    availability = {
        "spot_eurnok": "Daily indicative reference fixing at 14:15 CET according to source COLLECTION field; use the final observed business day of the month. This is not a closing executable transaction price.",
        "nb_policy": "Official daily effective policy rate; end-of-day collection. End-month observed rate is used, not an announced future rate.",
        "ecb_dfr": "Official daily effective deposit facility rate. Source itself includes calendar-day observations. No rate is carried beyond source coverage.",
        "ecb_mro": "Official daily effective MRO rate, combining fixed-rate and minimum-bid regimes on equal calendar dates. No rate is carried beyond source coverage.",
        "brent": "Underlying EIA daily observations reach FRED after their observation dates; historical release timestamps are not retained here. Use a conservative one-completed-month predictor lag.",
        "vix": "US daily closing VIX arrives after the Norwegian reference fixing; FRED ingestion may be later. Use a conservative one-completed-month predictor lag.",
        "usd_broad": "Board H.10 publishes previous-week daily rates/indexes on Mondays at 16:15 US Eastern (next business day on a federal holiday). Use a conservative one-completed-month predictor lag; observation date is not publication date.",
    }
    columns = {}
    for column, values in series.items():
        columns[column] = {
            "source": source_keys[column], "unit": units[column],
            "monthly_aggregation": "arithmetic mean of nonmissing official daily observations" if aggregations[column] == "mean" else "last nonmissing official daily observation within each calendar month",
            "publication_availability": availability[column],
            "recommended_predictor_lag_months": 1 if column in {"brent", "vix", "usd_broad"} else 0,
            "monthly_valid_count": int(result[column].notna().sum()),
            "monthly_missing_count": int(result[column].isna().sum()),
            "first_valid_month": result[column].first_valid_index(),
            "last_valid_month": result[column].last_valid_index(),
            "daily_coverage": daily_summary(values, periods),
        }
        if column in {"nb_policy", "ecb_dfr", "ecb_mro"}:
            columns[column]["last_observed_rate_change_date"] = last_change(values[values.index <= periods[-1].end_time])
    fallback = ecb["MRR_RT"][~ecb["MRR_RT"].index.isin(ecb["MRR_FR"].index)]
    manifest = {
        "dataset": "EUR/NOK v2 public daily-market observations, normalized by observation month",
        "generated_utc": utc_now(),
        "requested_months": {"start": str(periods[0]), "end": str(periods[-1]), "count": len(periods)},
        "data_file": "data/market.csv", "data_bytes": output.stat().st_size,
        "data_sha256": sha256(output.read_bytes()),
        "schema": ["month", *result.columns],
        "vintage": "Latest source vintage on each recorded retrieval date. Not an ALFRED/archived as-of real-time panel. Later source corrections may change historical observations.",
        "missing_value_policy": "Empty CSV fields are missing observations. No interpolation, backward fill, cross-month fill, synthetic prehistory or splice to a different dollar index. USD broad is unavailable before January 2006.",
        "timing_policy": "market.csv stores observation-month values. The model runner must apply declared source publication lags. In particular, a contemporaneous US-close or subsequently released EIA/H.10 value is not available at the same month's Norwegian 14:15 fixing.",
        "ecb_mro_regime": {
            "rule": "Use observed MRR_FR when present; otherwise use observed MRR_RT for that same day. All overlapping observations are checked for equality. No fill across the 2000-2008 fixed-rate tender gap.",
            "overlap_daily_observations_checked": int(len(overlap)),
            "overlap_value_mismatches": int(len(mismatches)),
            "minimum_bid_fallback_first_date": str(fallback.index.min().date()) if len(fallback) else None,
            "minimum_bid_fallback_last_date": str(fallback.index.max().date()) if len(fallback) else None,
            "minimum_bid_fallback_daily_count": int(len(fallback)),
        },
        "sources": {name: {**definition, **receipts[name], "raw_file": f"raw/market_{name}.csv"} for name, definition in definitions.items()},
        "columns": columns,
        "availability_references": ["https://www.federalreserve.gov/releases/h10/", "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html", "https://www.norges-bank.no/en/topics/Statistics/exchange_rates/"],
    }
    (DATA / "market_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"file": str(output), "months": len(result), "coverage": {column: {"first": result[column].first_valid_index(), "last": result[column].last_valid_index(), "nonmissing": int(result[column].notna().sum())} for column in result}, "latest": result.tail(1).to_dict("index")}, indent=2))


if __name__ == "__main__":
    main()
