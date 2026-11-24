#!/usr/bin/env python3
"""Run the preregistered EUR/NOK v2 comparison on retained public observations.

No network access and no unobserved target labels are required. All units in
the forecasting layer are cumulative log-return percentage points.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261124
ALPHA = 10.0
MIN_TRAIN = 60
BOOTSTRAPS = 3000
BLOCKS = {
    "rates": ["policy_diff", "diff_change", "ecb_corridor"],
    "energy": ["oil_ret1", "oil_ret3"],
    "risk": ["log_vix", "vix_change", "usd_return", "fx_vol6"],
    "macro": ["inflation_gap", "ip_gap"],
}
FULL = ["return_lag1"] + sum(BLOCKS.values(), [])
MODEL_FEATURES = {
    "rw": [],
    "ar1": ["return_lag1"],
    "domestic": ["return_lag1", "nb_level", "nb_change"],
    "rates": ["return_lag1"] + BLOCKS["rates"],
    "energy": ["return_lag1"] + BLOCKS["rates"] + BLOCKS["energy"],
    "risk": ["return_lag1"] + BLOCKS["rates"] + BLOCKS["energy"] + BLOCKS["risk"],
    "full": FULL,
    "regime": FULL + ["rate_stress", "oil_stress"],
    "ensemble": [],
}
LABELS = {
    "rw": "Random walk",
    "ar1": "Own FX dynamics · AR(1)",
    "domestic": "Domestic rates",
    "rates": "Relative rates",
    "energy": "Rates + energy",
    "risk": "Rates + energy + risk",
    "full": "Full multidimensional model",
    "regime": "Full + stress interactions",
    "ensemble": "Conservative fixed ensemble",
}
FEATURE_INFO = {
    "return_lag1": ("Last monthly EUR/NOK return", "% log return", 0.25),
    "nb_level": ("Norges Bank policy rate", "% per annum", 0.25),
    "nb_change": ("Norwegian policy-rate change", "percentage points", 0.25),
    "policy_diff": ("Norway minus ECB deposit rate", "percentage points", 0.25),
    "diff_change": ("Monthly change in rate differential", "percentage points", 0.25),
    "ecb_corridor": ("ECB MRO minus deposit rate", "percentage points", 0.05),
    "oil_ret1": ("Lagged 1-month Brent change", "% log change", 1.0),
    "oil_ret3": ("Lagged 3-month Brent change", "% log change", 1.0),
    "log_vix": ("Lagged log VIX level", "natural log of index", 0.05),
    "vix_change": ("Lagged VIX monthly change", "index points", 1.0),
    "usd_return": ("Lagged broad-dollar change", "% log change", 0.25),
    "fx_vol6": ("Trailing 6-month FX volatility", "% monthly log-return stdev", 0.25),
    "inflation_gap": ("Lagged Norway minus EA HICP inflation", "percentage points", 0.25),
    "ip_gap": ("Lagged Norway minus EA industry growth", "percentage points", 1.0),
    "rate_stress": ("Rate differential × high-risk regime", "percentage points", 0.25),
    "oil_stress": ("Oil change × high-risk regime", "% log change", 1.0),
}


def clean(x):
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)):
        return [clean(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return float(x) if math.isfinite(float(x)) else None
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def dump(path, obj):
    compact = path.name in {"predictions.json", "ablation_predictions.json", "history.json"}
    path.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=None if compact else 2,
                               separators=(",", ":") if compact else None, allow_nan=False) + "\n")


def load_data():
    market = pd.read_csv(ROOT / "data/market.csv")
    macro = pd.read_csv(ROOT / "data/macro.csv")
    raw = market.merge(macro, on="month", how="outer", validate="one_to_one").sort_values("month")
    raw.index = pd.PeriodIndex(raw.pop("month"), freq="M")
    expected = pd.period_range(raw.index.min(), raw.index.max(), freq="M")
    if not raw.index.equals(expected):
        raise ValueError("The observation calendar must be contiguous; no row-based shifts over gaps.")
    return raw


def generate_features(raw):
    d = raw.copy()
    d["return_lag1"] = 100 * np.log(d.spot_eurnok).diff()
    d["nb_level"] = d.nb_policy
    d["nb_change"] = d.nb_policy.diff()
    d["policy_diff"] = d.nb_policy - d.ecb_dfr
    d["diff_change"] = d.policy_diff.diff()
    d["ecb_corridor"] = d.ecb_mro - d.ecb_dfr
    d["oil_ret1"] = (100 * np.log(d.brent).diff()).shift(1)
    d["oil_ret3"] = (100 * np.log(d.brent).diff(3)).shift(1)
    d["log_vix"] = np.log(d.vix).shift(1)
    d["vix_change"] = d.vix.diff().shift(1)
    d["usd_return"] = (100 * np.log(d.usd_broad).diff()).shift(1)
    d["fx_vol6"] = d.return_lag1.rolling(6, min_periods=6).std(ddof=1)
    d["inflation_gap"] = (d.no_hicp_yoy - d.ea_hicp_yoy).shift(2)
    d["ip_gap"] = (d.no_ip_yoy - d.ea_ip_yoy).shift(2)
    d["stress"] = (d.vix.shift(1) >= 25).where(d.vix.shift(1).notna())
    d["rate_stress"] = d.policy_diff * d.stress.astype(float)
    d["oil_stress"] = d.oil_ret1 * d.stress.astype(float)
    return d


def fit_predict(train, origin, cols, alpha=ALPHA):
    """Return forecast, raw-unit coefficients and intercept; scaling is train-only."""
    x = train[cols].to_numpy(float)
    y = train.target.to_numpy(float)
    mean = x.mean(axis=0)
    std = x.std(axis=0, ddof=0)
    std = np.where(std < 1e-10, 1.0, std)
    z = (x - mean) / std
    ym = float(y.mean())
    if alpha == 0:
        beta = np.linalg.lstsq(z, y - ym, rcond=None)[0]
    else:
        beta = np.linalg.solve(z.T @ z + alpha * np.eye(len(cols)), z.T @ (y - ym))
    coef = beta / std
    intercept = ym - float(mean @ coef)
    prediction = intercept + float(origin[cols].to_numpy(float) @ coef)
    return prediction, coef, intercept


def block_inference(values, horizon, salt=0, draws=BOOTSTRAPS, block=None):
    """Descriptive paired block interval and approximate centred-null p-value."""
    v = np.asarray(values, float)
    n = len(v)
    b = block or max(3, horizon)
    rng = np.random.default_rng(SEED + salt + 100 * horizon + b)
    starts = rng.integers(0, n, size=(draws, math.ceil(n / b)))
    indices = ((starts[:, :, None] + np.arange(b)) % n).reshape(draws, -1)[:, :n]
    means = v[indices].mean(axis=1)
    observed = float(v.mean())
    ci = np.quantile(means, [0.025, 0.975])
    centred = means - observed
    p = (1 + np.count_nonzero(np.abs(centred) >= abs(observed))) / (draws + 1)
    return {"gain": observed, "ci": ci.tolist(), "p_value": float(p), "block_months": b}


def score(rows):
    a = np.array([r["actual"] for r in rows])
    p = np.array([r["predicted"] for r in rows])
    e = a - p
    intervals = [r for r in rows if r.get("lower") is not None and np.isfinite(r["lower"]) and np.isfinite(r["upper"])]
    return {
        "n": len(rows), "mae": float(np.mean(abs(e))),
        "rmse": float(np.sqrt(np.mean(e ** 2))),
        "direction_accuracy": None if np.all(p == 0) else float(np.mean(np.sign(a) == np.sign(p))),
        "win_rate": float(np.mean(abs(e) < abs(a))),
        "bias": float(np.mean(e)),
        "interval_n": len(intervals),
        "interval_coverage": float(np.mean([r["lower"] <= r["actual"] <= r["upper"] for r in intervals])) if intervals else None,
    }


def past_errors(rows, origin):
    return np.array([r["actual"] - r["predicted"] for r in rows if r["target"] <= str(origin)][-60:])


def run_horizon(features, horizon):
    d = features.copy()
    d["target"] = 100 * (np.log(d.spot_eurnok.shift(-horizon)) - np.log(d.spot_eurnok))
    all_cols = sorted(set(sum(MODEL_FEATURES.values(), [])))
    common = d[all_cols].notna().all(axis=1) & d.spot_eurnok.notna()
    origins = [i for i in range(len(d) - horizon) if common.iloc[i] and str(d.index[i]) >= "2015-01"]
    out = {m: [] for m in MODEL_FEATURES}
    ablation_rows = {b: [] for b in BLOCKS}
    for i in origins:
        # Row j is eligible only when j+h <= i; iloc upper bound is exclusive.
        train = d.iloc[: i - horizon + 1].loc[common.iloc[: i - horizon + 1]].dropna(subset=["target"])
        if len(train) < MIN_TRAIN:
            continue
        origin = d.iloc[i]
        pred = {"rw": 0.0}
        for m, cols in MODEL_FEATURES.items():
            if m in ("rw", "ensemble"):
                continue
            pred[m] = fit_predict(train, origin, cols, 0 if m == "ar1" else ALPHA)[0]
        pred["ensemble"] = 0.25 * pred["ar1"] + 0.25 * pred["full"]
        info = {
            "origin": str(d.index[i]), "target": str(d.index[i + horizon]),
            "actual": float(origin.target), "baseline": 0.0,
            "spot_origin": float(origin.spot_eurnok),
            "spot_target": float(d.iloc[i + horizon].spot_eurnok),
            "train_n": len(train), "train_end": str(train.index[-1]),
            "max_train_target": str(train.index[-1] + horizon),
            "stress": bool(origin.stress), "rate_gap": float(origin.policy_diff),
            "oil_change": float(origin.oil_ret1),
        }
        for m, p in pred.items():
            err = past_errors(out[m], d.index[i])
            q = np.quantile(err, [0.05, 0.95]) if len(err) >= 24 else [np.nan, np.nan]
            out[m].append({**info, "predicted": p, "lower": float(p + q[0]), "upper": float(p + q[1]), "calibration_n": len(err)})
        for b, removed in BLOCKS.items():
            cols = [c for c in FULL if c not in removed]
            p = fit_predict(train, origin, cols)[0]
            ablation_rows[b].append({**info, "predicted": p})
    if not out["rw"]:
        raise ValueError("No eligible forecast origins.")
    actual = np.array([r["actual"] for r in out["rw"]])
    rw_loss = abs(actual)
    ar_loss = abs(actual - np.array([r["predicted"] for r in out["ar1"]]))
    models = []
    for k, (m, rows) in enumerate(out.items()):
        s = score(rows)
        loss = abs(actual - np.array([r["predicted"] for r in rows]))
        rw = block_inference(rw_loss - loss, horizon, k)
        ar = block_inference(ar_loss - loss, horizon, k + 50)
        longer = block_inference(rw_loss - loss, horizon, k, block=max(6, 2 * horizon))
        models.append({"id": m, "label": LABELS[m], **s,
                       "improvement_vs_rw": rw["gain"], "improvement_ci": rw["ci"],
                       "improvement_vs_ar1": ar["gain"], "ar1_improvement_ci": ar["ci"],
                       "p_rw": rw["p_value"], "p_ar1": ar["p_value"],
                       "longer_block_ci": longer["ci"], "block_months": rw["block_months"]})
    ablations = []
    full_loss = abs(actual - np.array([r["predicted"] for r in out["full"]]))
    for k, (block, rows) in enumerate(ablation_rows.items()):
        loss = abs(actual - np.array([r["predicted"] for r in rows]))
        stat = block_inference(loss - full_loss, horizon, 100 + k)
        ablations.append({"block": block, "label": block.title(), "full_mae": float(full_loss.mean()),
                          "without_mae": float(loss.mean()), "incremental_gain": stat["gain"],
                          "ci": stat["ci"], "n": len(rows), "exploratory": True})
    regimes = []
    groups = {
        "Risk: VIX below 25": lambda r: not r["stress"],
        "Risk: VIX at least 25": lambda r: r["stress"],
        "Rates: Norway premium": lambda r: r["rate_gap"] >= 0,
        "Rates: Norway discount": lambda r: r["rate_gap"] < 0,
        "Oil: prior month rising": lambda r: r["oil_change"] >= 0,
        "Oil: prior month falling": lambda r: r["oil_change"] < 0,
        "Period: 2015–2019": lambda r: r["origin"] <= "2019-12",
        "Period: 2020–2021": lambda r: "2020-01" <= r["origin"] <= "2021-12",
        "Period: 2022–2023": lambda r: "2022-01" <= r["origin"] <= "2023-12",
        "Period: 2024 onward": lambda r: r["origin"] >= "2024-01",
    }
    for name, selector in groups.items():
        for m in ["ar1", "rates", "full", "regime", "ensemble"]:
            rr = [r for r in out[m] if selector(r)]
            if not rr:
                continue
            s = score(rr)
            base = np.mean([abs(r["actual"]) for r in rr])
            regimes.append({"regime": name, "model_id": m, "label": LABELS[m], "n": len(rr),
                            "mae": s["mae"], "baseline_mae": base, "gain": base - s["mae"],
                            "small_sample": len(rr) < 24})
    # This is a retrospective month-end snapshot generated now, not a claim that
    # the forecast was actually issued before the month-end information cutoff.
    i = len(d) - 1
    if not common.iloc[i]:
        raise ValueError("Latest month lacks the declared information set; do not fabricate a forecast.")
    train = d.iloc[: i - horizon + 1].loc[common.iloc[: i - horizon + 1]].dropna(subset=["target"])
    origin = d.iloc[i]
    latest_predictions = {"rw": (0.0, [], 0.0)}
    for m, cols in MODEL_FEATURES.items():
        if m not in ("rw", "ensemble"):
            latest_predictions[m] = fit_predict(train, origin, cols, 0 if m == "ar1" else ALPHA)
    latest_predictions["ensemble"] = (0.25 * latest_predictions["ar1"][0] + 0.25 * latest_predictions["full"][0], [], 0.0)
    latest = []
    for m, fit in latest_predictions.items():
        err = past_errors(out[m], d.index[i])
        q = np.quantile(err, [0.05, 0.95]) if len(err) >= 24 else np.array([np.nan, np.nan])
        p = fit[0]
        latest.append({"model_id": m, "label": LABELS[m], "prediction": p,
                       "lower": p + q[0], "upper": p + q[1], "target_month": str(d.index[i] + horizon),
                       "prob_nok_depreciation": float(np.mean(p + err > 0)) if len(err) >= 24 else None,
                       "calibration_n": len(err), "origin": str(d.index[i])})
    scenario_features = []
    _, coeffs, intercept = latest_predictions["full"]
    for c, coef in zip(FULL, coeffs):
        label, unit, step = FEATURE_INFO[c]
        hist = train[c]
        low, high = hist.quantile([0.01, 0.99]).values
        v = float(origin[c])
        scenario_features.append({"name": c, "label": label, "value": v, "coefficient": float(coef),
                                  "unit": unit, "min": min(float(low), v), "max": max(float(high), v),
                                  "historical_min": float(hist.min()), "historical_max": float(hist.max()),
                                  "step": step, "block": next((b for b, cs in BLOCKS.items() if c in cs), "own FX dynamics")})
    q = np.quantile(past_errors(out["full"], d.index[i]), [0.05, 0.95])
    scenario = {"model_id": "full", "label": LABELS["full"], "baseline_prediction": latest_predictions["full"][0],
                "intercept": intercept, "features": scenario_features, "residual_quantiles": q.tolist(),
                "origin_spot": float(origin.spot_eurnok), "origin": str(d.index[i]),
                "interpretation": "Conditional fitted association; not an identified causal shock or a guaranteed forecast."}
    return {"models": models, "ablations": ablations, "regimes": regimes, "latest_forecasts": latest,
            "scenario": scenario, "first_origin": out["rw"][0]["origin"], "last_origin": out["rw"][-1]["origin"],
            "last_target": out["rw"][-1]["target"]}, out, ablation_rows


def holm_adjust(results):
    family = []
    for h, d in results["horizons"].items():
        for m in d["models"]:
            for base in ["rw", "ar1"]:
                if m["id"] not in (base, "rw"):
                    family.append((float(m[f"p_{base}"]), h, m, base))
    ordered = sorted(family, key=lambda t: t[0])
    cumulative = 0.0
    for rank, (p, h, model, base) in enumerate(ordered):
        cumulative = max(cumulative, min(1.0, (len(ordered) - rank) * p))
        model[f"p_{base}_holm"] = cumulative
    results["multiplicity"] = {"method": "Holm", "family_size": len(family),
                               "family": "All nontrivial declared model comparisons against random walk and AR(1), across 1/3/6 months.",
                               "p_value_method": "Approximate two-sided centred circular-block bootstrap; not exact small-sample inference."}


def metadata(raw, features):
    market = json.loads((ROOT / "data/market_manifest.json").read_text())
    macro = json.loads((ROOT / "data/macro_manifest.json").read_text())
    sources = []
    for key, s in market["sources"].items():
        sources.append({"id": key, "label": s["publisher"], "url": s.get("primary_reference_url", s.get("reference_url", s["url"])),
                        "series": s["series_id"], "retrieved_utc": s["retrieved_utc"], "status": "Used in core model"})
    for s in macro["sources"]:
        sources.append({"id": s["column"], "label": s["label"], "url": s["source_page"], "series": s["dataset"],
                        "retrieved_utc": s["retrieved_utc"], "status": "Used with two-month lag"})
    sources.extend([
        {"id": "ea_mpd", "label": "ECB public event-study OIS repricing", "url": "https://www.ecb.europa.eu/pub/pdf/annex/Dataset_EA-MPD.xlsx",
         "series": "EA-MPD", "status": "Downloaded; historical extension only (ends October 2025)"},
        {"id": "norway_surprises", "label": "Norway OIS/FRA surprises and consensus inflation surprises", "url": "https://www.norges-bank.no/en/news-events/publications/Staff-Memo/2026/staff-memo-5-2026-macroeconomic-news/",
         "series": "LSEG Tick History / Bloomberg consensus in cited research", "status": "Not acquired; not substituted or simulated"},
    ])
    coverage = []
    for c in raw:
        s = raw[c].dropna()
        lag = 2 if c in ["no_hicp_yoy", "ea_hicp_yoy", "no_ip_yoy", "ea_ip_yoy"] else 1 if c in ["brent", "vix", "usd_broad"] else 0
        coverage.append({"series": c, "start": str(s.index.min()), "end": str(s.index.max()), "count": len(s),
                         "missing": int(raw[c].isna().sum()), "lag_months": lag})
    complete = features.dropna(subset=sorted(set(sum(MODEL_FEATURES.values(), []))))
    return {
        "metadata": {"title": "EUR/NOK Research Lab", "version": "2.0", "as_of": "2026-11-24",
                     "generated_utc": datetime.now(timezone.utc).isoformat(),
                     "sample_start": str(raw.index.min()), "sample_end": str(raw.index.max()),
                     "feature_sample_start": str(complete.index.min()), "latest_spot": float(raw.spot_eurnok.iloc[-1]),
                     "latest_origin": str(raw.index[-1]), "information_cutoff": "2026-10-31",
                     "target_definition": "100 × log(end-of-month EUR/NOK at t+h / end-of-month EUR/NOK at t)",
                     "validation_label": "Latest-vintage, expanding-window pseudo-out-of-sample",
                     "forecast_timestamp_warning": "October snapshot calculated on 24 November; not an October-issued historical live forecast.",
                     "first_prospective_origin": "2026-11-30", "observation_months": len(raw),
                     "core_series": len(raw.columns), "feature_count_full": len(FULL), "horizons": [1, 3, 6],
                     "model_count": len(MODEL_FEATURES), "ridge_alpha": ALPHA, "bootstrap_draws": BOOTSTRAPS,
                     "protocol_sha256": hashlib.sha256((ROOT / "PROTOCOL.md").read_bytes()).hexdigest()},
        "sources": sources, "data_coverage": coverage,
        "limitations": [
            "No robust edge is assumed. Assess paired loss intervals, AR(1) comparisons, block ablations and multiple-testing-adjusted evidence.",
            "Latest-vintage macro and dollar-index records can contain revisions unavailable historically; publication lags do not solve vintage bias.",
            "Reference FX fixings are indicative, not executable quotes. No bid–ask spread, carry, funding, slippage or net trading profitability has been demonstrated.",
            "Norwegian and ECB administered rates are not market-implied OIS paths or announcement surprises. Norwegian high-frequency surprises have not been acquired.",
            "EA-MPD is downloaded through October 2025 only and is excluded from the current complete-sample forecasting block.",
            "Industrial production includes Norwegian extraction; it is not mainland GDP. Euro-area macro data use fixed EA20 composition.",
            "HICP uses the current ECOICOP-v2 series; Eurostat flags possible January 2026 classification/methodology changes.",
            "Three- and six-month targets overlap. Block resampling helps describe dependence but small-sample and model-selection uncertainty remain.",
            "The October month-end snapshot was calculated in November. First genuinely prospective test origin after protocol freeze: 30 November 2026.",
            "Scenario coefficients describe conditional association. A causal monetary-policy conclusion requires identified surprises and a separate event/structural design.",
            "Tail bands use up to 60 matured prior forecast errors, with only 24 required; they are empirical bands without a coverage guarantee.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    raw = load_data()
    features = generate_features(raw)
    results = metadata(raw, features)
    results["horizons"] = {}
    predictions, ablations = {}, {}
    for h in [1, 3, 6]:
        summary, pred, abl = run_horizon(features, h)
        results["horizons"][str(h)] = summary
        predictions[str(h)], ablations[str(h)] = pred, abl
        print(f"h={h}: {len(pred['rw'])} forecasts; full MAE={next(m['mae'] for m in summary['models'] if m['id']=='full'):.4f}")
    holm_adjust(results)
    dump(args.output / "results.json", results)
    dump(args.output / "predictions.json", predictions)
    dump(args.output / "ablation_predictions.json", ablations)
    features.to_csv(ROOT / "data/features.csv", index_label="month", float_format="%.12g")
    history = raw.reset_index(names="month")
    history["month"] = history.month.astype(str)
    dump(args.output / "history.json", history.to_dict("records"))
    flat = [{"horizon_months": h, **row} for h, d in results["horizons"].items() for row in d["models"]]
    pd.DataFrame(flat).to_csv(args.output / "model_comparison.csv", index=False)
    forecast_rows = [{"horizon_months": h, "generated_utc": results["metadata"]["generated_utc"], **row}
                     for h, d in results["horizons"].items() for row in d["latest_forecasts"]]
    pd.DataFrame(forecast_rows).to_csv(args.output / "snapshot_forecasts.csv", index=False)
    print(json.dumps(results["metadata"], indent=2))


if __name__ == "__main__":
    main()
