#!/usr/bin/env python3
"""Download Eurostat macro inputs and retain an optional ECB event-study extract.

The panel is observation-dated, not availability-dated. Forecast code MUST apply
the stated publication lags. All extracts are latest vintage; no real-time
historical database is implied. Cached raw files make the packaged snapshot
reproducible. Use --refresh to download a new vintage deliberately.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
DATA = ROOT / "data"
END_MONTH = "2026-10"
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
HEADERS = {"User-Agent": "Nord Veritas public-source EUR/NOK research"}


def eurostat_url(dataset: str, **filters: str) -> str:
    return API + dataset + "?" + urllib.parse.urlencode({"lang": "en", **filters})


SPECS = {
    "no_hicp_yoy": {
        "file": "macro_no_hicp.json", "dataset": "prc_hicp_minr",
        "filters": {"freq": "M", "unit": "RCH_A", "coicop18": "TOTAL", "geo": "NO", "sinceTimePeriod": "2000-01"},
        "label": "Norway all-items HICP, annual rate of change", "unit": "percent year-on-year", "release_lag_months": 2,
    },
    "ea_hicp_yoy": {
        "file": "macro_ea_hicp.json", "dataset": "prc_hicp_minr",
        "filters": {"freq": "M", "unit": "RCH_A", "coicop18": "TOTAL", "geo": "EA20", "sinceTimePeriod": "2000-01"},
        "label": "Euro area 20-country fixed-composition all-items HICP, annual rate of change", "unit": "percent year-on-year", "release_lag_months": 2,
    },
    "no_ip_yoy": {
        "file": "macro_no_ip.json", "dataset": "sts_inpr_m",
        "filters": {"freq": "M", "nace_r2": "B-D", "unit": "I21", "s_adj": "SCA", "geo": "NO", "sinceTimePeriod": "1999-01"},
        "label": "Norway industrial production, NACE B-D, seasonally and calendar adjusted", "unit": "percent year-on-year, derived from 2021=100 index", "release_lag_months": 2,
    },
    "ea_ip_yoy": {
        "file": "macro_ea_ip.json", "dataset": "sts_inpr_m",
        "filters": {"freq": "M", "nace_r2": "B-D", "unit": "I21", "s_adj": "SCA", "geo": "EA20", "sinceTimePeriod": "1999-01"},
        "label": "Euro area 20-country fixed-composition industrial production, NACE B-D, seasonally and calendar adjusted", "unit": "percent year-on-year, derived from 2021=100 index", "release_lag_months": 2,
    },
}


def read_bytes(url: str, path: Path, refresh: bool = False) -> tuple[bytes, str, dict]:
    sidecar = path.with_suffix(path.suffix + ".retrieval.json")
    if path.exists() and not refresh:
        result = path.read_bytes()
        fetched_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        mode = "retained_snapshot"
    else:
        request = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(request, timeout=50) as response:
            result = response.read()
        path.write_bytes(result)
        fetched_at = datetime.now(timezone.utc).isoformat()
        mode = "downloaded"
    digest = hashlib.sha256(result).hexdigest()
    if sidecar.exists() and not refresh:
        provenance = json.loads(sidecar.read_text())
        if provenance["url"] != url or provenance["sha256"] != digest:
            raise ValueError("Cached extract differs from its retained source provenance")
    else:
        provenance = {"url": url, "retrieved_utc": fetched_at, "bytes": len(result), "sha256": digest}
        sidecar.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return result, mode, provenance


def single_series(payload: dict) -> pd.Series:
    dimensions = payload["id"]
    if any(payload["size"][i] != 1 for i, name in enumerate(dimensions) if name != "time"):
        raise ValueError("Query does not resolve to exactly one non-time series")
    times = payload["dimension"]["time"]["category"]["index"]
    if not isinstance(times, dict):
        times = {date: i for i, date in enumerate(times)}
    values = payload.get("value", {})
    if isinstance(values, list):
        values = {str(i): value for i, value in enumerate(values)}
    result = pd.Series({date: values.get(str(i), np.nan) for date, i in times.items()}, dtype=float)
    result.index = pd.PeriodIndex(result.index, freq="M")
    return result.sort_index()


def collect_one(item: tuple[str, dict], refresh: bool) -> tuple[str, pd.Series, dict]:
    key, spec = item
    url = eurostat_url(spec["dataset"], **spec["filters"])
    path = RAW / spec["file"]
    body, fetch_mode, provenance = read_bytes(url, path, refresh)
    payload = json.loads(body)
    series = single_series(payload)
    if key.endswith("_ip_yoy"):
        if (series.dropna() <= 0).any():
            raise ValueError("Industrial-production index must be strictly positive")
        # Reindex explicitly so shift(12) is twelve CALENDAR months, not twelve rows.
        series = series.reindex(pd.period_range(series.index.min(), series.index.max(), freq="M"))
        series = 100.0 * (series / series.shift(12) - 1.0)
    series = series.loc["2000-01":END_MONTH]
    observed = series.dropna()
    metadata = {
        "column": key, "source": "Eurostat", "dataset": spec["dataset"],
        "label": spec["label"], "unit": spec["unit"], "filters": spec["filters"],
        "resolved_dimensions": {name: payload["dimension"][name]["category"].get("index", {}) for name in payload["id"] if name != "time"},
        "url": url, "source_page": "https://ec.europa.eu/eurostat/databrowser/view/" + spec["dataset"] + "/default/table?lang=en",
        "raw_file": str(path.relative_to(ROOT)), "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(), "retrieved_utc": provenance["retrieved_utc"],
        "fetch_mode": fetch_mode, "source_updated": payload.get("updated"),
        "first_observation": str(observed.index.min()), "last_observation": str(observed.index.max()),
        "observations": int(observed.size), "release_lag_months": spec["release_lag_months"],
        "lag_policy": "Conservative uniform two-calendar-month publication lag in forecasting; raw panel remains observation-dated.",
        "vintage": "Latest downloaded vintage; publication lags do not eliminate historical revisions.",
        "geography_note": "EA20 is a fixed 20-country aggregate, including historical backcasts; it is not the changing-membership euro area. Norway is NO.",
        "missing_value_policy": "Preserved as missing. No interpolation, forward fill or invented observations.",
        "observation_flags": payload.get("status", {}),
    }
    if "hicp" in key:
        metadata["definition_note"] = "Current prc_hicp_minr TOTAL series with ECOICOP v2, annual percent change. Replaces discontinued prc_hicp_manr. Eurostat notes possible January 2026 classification/methodology breaks. No manual splice used."
    else:
        metadata["definition_note"] = "100*(I_t/I_(t-12)-1), from seasonally and calendar adjusted index 2021=100; total industry excluding construction. Norway includes extractive industries, so the differential is not mainland GDP growth."
    return key, series, metadata


def collect_ecb_events(refresh: bool = False) -> dict:
    url = "https://www.ecb.europa.eu/pub/pdf/annex/Dataset_EA-MPD.xlsx"
    path = RAW / "macro_ea_mpd.xlsx"
    body, fetch_mode, provenance = read_bytes(url, path, refresh)
    sheets = ["Press Release Window", "Press Conference Window", "Monetary Event Window"]
    rename = {"OIS_1M": "ois_1m_bp", "OIS_3M": "ois_3m_bp", "OIS_6M": "ois_6m_bp", "OIS_1Y": "ois_1y_bp", "OIS_2Y": "ois_2y_bp", "OIS_10Y": "ois_10y_bp"}
    records = []
    for sheet in sheets:
        frame = pd.read_excel(path, sheet_name=sheet)
        frame.columns = [str(x).strip() for x in frame.columns]
        frame["date"] = pd.to_datetime(frame["date"], format="mixed", dayfirst=True, errors="raise")
        frame = frame.loc[:, ["date", *rename]].rename(columns=rename)
        frame["window"] = sheet
        frame["date"] = frame["date"].dt.strftime("%Y-%m-%d")
        records.append(frame)
    events = pd.concat(records, ignore_index=True).sort_values(["date", "window"])
    events.to_csv(DATA / "ea_mpd_events.csv", index=False)
    metadata = {
        "source": "European Central Bank", "dataset": "Euro Area Monetary Policy Event-Study Database (EA-MPD)",
        "url": url, "raw_file": str(path.relative_to(ROOT)), "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(), "retrieved_utc": provenance["retrieved_utc"],
        "fetch_mode": fetch_mode, "first_event": events["date"].min(), "last_event": events["date"].max(),
        "events_per_window": {str(k): int(v) for k, v in events.groupby("window").size().items()},
        "units": "OIS rate changes in basis points, per workbook Notes sheet",
        "workbook_update_note": "4 November 2025, per retained workbook Notes sheet. This observed file vintage takes precedence over newer dates displayed on referring web pages.",
        "missing_value_policy": "Missing event quotes are retained as NaN. No non-event months or unobserved future periods are manufactured or set to zero.",
        "intended_role": "Optional historical event-study extension. Excluded from the current complete-sample forecast block because coverage ends before the current macro panel and Norway counterpart is not acquired.",
        "interpretation": "Observed intraday OIS repricing around ECB events is a market expectations proxy, not an observed pure exogenous policy shock; policy, forward-guidance and information effects may be mixed.",
        "reference": "Altavilla, Brugnolini, Gurkaynak, Motto and Ragusa (2019), Measuring Euro Area Monetary Policy, Journal of Monetary Economics.",
    }
    (DATA / "ea_mpd_manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--skip-events", action="store_true")
    args = parser.parse_args()
    RAW.mkdir(exist_ok=True, parents=True)
    DATA.mkdir(exist_ok=True, parents=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        outputs = list(pool.map(lambda item: collect_one(item, args.refresh), SPECS.items()))
    dates = pd.period_range("2000-01", END_MONTH, freq="M")
    panel = pd.DataFrame(index=dates)
    sources = []
    for key, series, metadata in outputs:
        panel[key] = series
        sources.append(metadata)
    panel.index = panel.index.astype(str)
    panel.index.name = "month"
    panel.to_csv(DATA / "macro.csv", float_format="%.8f")
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "observation_end_cap": END_MONTH,
        "panel_file": "data/macro.csv", "panel_rows": len(panel),
        "publication_lags_applied_here": False, "recommended_model_lag_months": 2,
        "revision_warning": "Latest vintage only; apparent backtests are pseudo out-of-sample, not real-time vintage tests.",
        "sources": sources,
        "unavailable_inputs": [
            {"input": "Norway policy-event OIS/FRA surprises", "status": "Not acquired; no public downloadable replication table located on the inspected official publication pages", "source_page": "https://www.norges-bank.no/en/news-events/publications/Staff-Memo/2025/staff-memo-3-2025/", "note": "Underlying high-frequency market expectations quotes are not replaced by ordinary policy-rate changes."},
            {"input": "Relative Norway/euro-area inflation and monetary news instruments", "status": "Not acquired", "source_page": "https://www.norges-bank.no/en/news-events/publications/Staff-Memo/2026/staff-memo-5-2026-macroeconomic-news/", "note": "Staff Memo 5/2026 uses LSEG Tick History (including NOK1YOIS/EUREON1Y) and Bloomberg survey consensus; official page offers paper but no downloadable source table was found."},
        ],
        "definition_references": [
            "https://webgate.ec.europa.eu/eurostat/cache/metadata/en/prc_hicp_esms.htm",
            "https://ec.europa.eu/eurostat/cache/metadata/en/sts_inpr_esms.htm",
        ],
    }
    (DATA / "macro_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Wrote", DATA / "macro.csv", "with", len(panel), "months")
    print(panel.tail(4).to_string())
    if not args.skip_events:
        try:
            meta = collect_ecb_events(args.refresh)
            print("ECB event-study extract:", meta["first_event"], "to", meta["last_event"])
        except Exception as error:
            # A failure in an optional historical extension cannot silently alter
            # or remove the complete macro panel.
            print("Optional ECB event extract unavailable:", type(error).__name__, str(error))


if __name__ == "__main__":
    main()
