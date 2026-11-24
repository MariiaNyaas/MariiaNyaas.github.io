#!/usr/bin/env python3
"""Descriptive historical EUR/NOK response to ECB announcement OIS repricing.

Prespecified predictor: EA-MPD Monetary Event Window / OIS 1Y, in basis points.
The baseline fixing is strictly before the event date. The outcomes use the
1st, 5th and 20th Norges Bank fixings strictly AFTER that date. Thus no same-day
14:15 CET quote is incorrectly treated as capturing a full ECB event window.

This is a contemporaneous event association, not an out-of-sample forecast,
causal identification, executable strategy or current-vintage shock feed.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WINDOW = "Monetary Event Window"
TENOR = "ois_1y_bp"
HORIZONS = (1, 5, 20)
SEED = 20261124
BOOTSTRAP_DRAWS = 3000
BLOCK_EVENTS = 3


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fit_event_regression(x: np.ndarray, y: np.ndarray, horizon: int) -> dict:
    """OLS with intercept, independent HC3 and event-block percentile intervals."""
    n = len(x)
    if n < 30 or np.var(x) == 0:
        raise ValueError("Insufficient usable events or predictor variation")
    design = np.column_stack([np.ones(n), x])
    inverse = np.linalg.inv(design.T @ design)
    beta = inverse @ design.T @ y
    residual = y - design @ beta
    hat_diag = np.sum((design @ inverse) * design, axis=1)
    hc3_weights = residual ** 2 / (1.0 - hat_diag) ** 2
    hc3_cov = inverse @ (design.T @ (hc3_weights[:, None] * design)) @ inverse
    slope_se = float(np.sqrt(hc3_cov[1, 1]))

    # Paired, chronological circular event-block bootstrap. Refit the slope in
    # every draw; preserve within-block predictor/outcome relationships.
    rng = np.random.default_rng(SEED + horizon)
    blocks = int(np.ceil(n / BLOCK_EVENTS))
    starts = rng.integers(0, n, size=(BOOTSTRAP_DRAWS, blocks))
    indices = ((starts[:, :, None] + np.arange(BLOCK_EVENTS)) % n).reshape(BOOTSTRAP_DRAWS, -1)[:, :n]
    xb, yb = x[indices], y[indices]
    xcenter = xb - xb.mean(axis=1, keepdims=True)
    ycenter = yb - yb.mean(axis=1, keepdims=True)
    denominators = np.sum(xcenter ** 2, axis=1)
    slopes = np.sum(xcenter * ycenter, axis=1) / denominators
    slopes = slopes[np.isfinite(slopes)]
    if len(slopes) != BOOTSTRAP_DRAWS:
        raise ValueError("Non-finite event-bootstrap slope")
    block_ci = np.percentile(slopes * 25.0, [2.5, 97.5])
    block_ci10 = np.percentile(slopes * 10.0, [2.5, 97.5])
    family_alpha = 0.05 / len(HORIZONS)
    bonferroni_quantiles = [100.0 * family_alpha / 2.0, 100.0 * (1.0 - family_alpha / 2.0)]
    bonferroni_ci10 = np.percentile(slopes * 10.0, bonferroni_quantiles)
    bonferroni_ci25 = np.percentile(slopes * 25.0, bonferroni_quantiles)
    hc3_ci = (beta[1] + np.array([-1, 1]) * 1.959963984540054 * slope_se) * 25.0
    total_ss = float(np.sum((y - y.mean()) ** 2))
    return {
        "horizon_business_days": horizon,
        "n": n,
        "coefficient_pct_per_25bp": float(beta[1] * 25.0),
        "coefficient_pct_per_10bp": float(beta[1] * 10.0),
        "coefficient_pct_per_predictor_sd": float(beta[1] * x.std(ddof=1)),
        "block_bootstrap_ci95": [float(v) for v in block_ci],
        "block_bootstrap_ci95_per_10bp": [float(v) for v in block_ci10],
        "bonferroni_ci98_333_per_10bp": [float(v) for v in bonferroni_ci10],
        "bonferroni_ci98_333_per_25bp": [float(v) for v in bonferroni_ci25],
        "bonferroni_ci_crosses_zero": bool(bonferroni_ci10[0] <= 0 <= bonferroni_ci10[1]),
        "hc3_ci95": [float(v) for v in hc3_ci],
        "intercept_pct": float(beta[0]),
        "r2": float(1.0 - np.sum(residual ** 2) / total_ss),
        "pearson_correlation": float(np.corrcoef(x, y)[0, 1]),
        "predictor_mean_bp": float(x.mean()),
        "predictor_std_bp": float(x.std(ddof=1)),
        "predictor_min_bp": float(x.min()),
        "predictor_max_bp": float(x.max()),
        "outcome_mean_pct": float(y.mean()),
        "outcome_std_pct": float(y.std(ddof=1)),
        "block_ci_crosses_zero": bool(block_ci[0] <= 0 <= block_ci[1]),
        "interpretation": "Association in percent log EUR/NOK return per 10 bp higher ECB-event OIS1Y repricing; positive means NOK weakens against EUR. A 25 bp coefficient scale is retained for comparison, not labelled as a policy-rate hike.",
    }


def main() -> None:
    fx_path = ROOT / "raw/market_fx.csv"
    events_path = ROOT / "data/ea_mpd_events.csv"
    fx = pd.read_csv(fx_path, sep=";")
    required_dimensions = {"BASE_CUR": "EUR", "QUOTE_CUR": "NOK", "TENOR": "SP", "FREQ": "B"}
    for name, value in required_dimensions.items():
        if not fx[name].eq(value).all():
            raise ValueError(f"Unexpected FX series dimension {name}")
    fx["date"] = pd.to_datetime(fx.TIME_PERIOD)
    fx["spot"] = pd.to_numeric(fx.OBS_VALUE, errors="raise")
    fx = fx.sort_values("date")
    if fx.date.duplicated().any() or fx.spot.isna().any() or (fx.spot <= 0).any():
        raise ValueError("FX observations must be unique, nonmissing and positive")
    dates = fx.date.to_numpy(dtype="datetime64[ns]")
    spots = fx.spot.to_numpy(dtype=float)
    events = pd.read_csv(events_path)
    events = events.loc[events.window.eq(WINDOW)].copy()
    events["date"] = pd.to_datetime(events.date)
    events = events.sort_values("date")
    if events.date.duplicated().any():
        raise ValueError("Duplicated ECB event date in selected window")

    observations = []
    for event in events.itertuples(index=False):
        event_date = np.datetime64(event.date, "ns")
        before = int(np.searchsorted(dates, event_date, side="left")) - 1
        first_after = int(np.searchsorted(dates, event_date, side="right"))
        predictor = float(getattr(event, TENOR))
        for horizon in HORIZONS:
            target = first_after + horizon - 1
            reasons = []
            if not np.isfinite(predictor):
                reasons.append("missing_ois_1y_quote")
            if before < 0:
                reasons.append("no_pre_event_fixing")
            if target >= len(dates):
                reasons.append("insufficient_post_event_fixings")
            valid_dates = before >= 0 and target < len(dates)
            baseline_date = pd.Timestamp(dates[before]).strftime("%Y-%m-%d") if before >= 0 else None
            outcome_date = pd.Timestamp(dates[target]).strftime("%Y-%m-%d") if target < len(dates) else None
            outcome = float(100.0 * np.log(spots[target] / spots[before])) if valid_dates else None
            observations.append({
                "event_date": pd.Timestamp(event_date).strftime("%Y-%m-%d"),
                "window": WINDOW, "ois_1y_bp": predictor,
                "horizon_business_days": horizon,
                "baseline_fixing_date": baseline_date,
                "outcome_fixing_date": outcome_date,
                "baseline_eurnok": float(spots[before]) if before >= 0 else None,
                "outcome_eurnok": float(spots[target]) if target < len(dates) else None,
                "fx_log_return_pct": outcome,
                "included": not reasons,
                "exclusion_reason": ";".join(reasons),
            })

    table = pd.DataFrame(observations)
    output_dir = ROOT / "output"
    output_dir.mkdir(exist_ok=True)
    table.to_csv(output_dir / "event_observations.csv", index=False, float_format="%.10g")
    results = []
    for horizon in HORIZONS:
        rows = table.loc[table.horizon_business_days.eq(horizon) & table.included].sort_values("event_date")
        fit = fit_event_regression(rows.ois_1y_bp.to_numpy(), rows.fx_log_return_pct.to_numpy(), horizon)
        fit["first_event"] = str(rows.event_date.min())
        fit["last_event"] = str(rows.event_date.max())
        fit["first_outcome_fixing"] = str(rows.outcome_fixing_date.min())
        fit["last_outcome_fixing"] = str(rows.outcome_fixing_date.max())
        # Windows may overlap when another ECB event occurs before a prior
        # event's response window is complete. Report the actual count.
        fit["adjacent_outcome_window_overlap_count"] = int(sum(
            rows.baseline_fixing_date.iloc[i] < rows.outcome_fixing_date.iloc[i - 1]
            for i in range(1, len(rows))
        ))
        results.append(fit)

    market_manifest = json.loads((ROOT / "data/market_manifest.json").read_text())
    source_records = market_manifest["sources"]
    if isinstance(source_records, dict):
        source_records = source_records.values()
    fx_source = next(s for s in source_records if s.get("name") == "fx")
    ecb_manifest = json.loads((ROOT / "data/ea_mpd_manifest.json").read_text())
    reasons = Counter(table.loc[table.horizon_business_days.eq(1) & ~table.included, "exclusion_reason"])
    result = {
        "title": "ECB announcement repricing and subsequent EUR/NOK fixings",
        "module": "historical_event_association",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "question": "How is ECB-event one-year OIS repricing associated with EUR/NOK changes through 1, 5 and 20 subsequent Norges Bank business-day fixings?",
        "predictor": {"column": TENOR, "tenor": "1 year", "window": WINDOW, "units": "basis points", "interpretation": "ECB-event market repricing proxy; includes policy, guidance and information components"},
        "outcome": {"formula": "100 * log(S_outcome / S_baseline)", "units": "percent log return", "quote": "NOK per EUR", "positive_means": "NOK weakens", "baseline": "Last Norges Bank fixing strictly before the event date", "target": "Nth Norges Bank fixing strictly after the event date, N=1,5,20", "same_day_fixing_used": False},
        "coverage": {
            "fx_first_fixing": str(fx.date.min().date()), "fx_last_fixing": str(fx.date.max().date()),
            "fx_fixings": len(fx), "ecb_first_event": str(events.date.min().date()),
            "ecb_last_event": str(events.date.max().date()), "ecb_events_in_selected_window": len(events),
            "missing_ois_1y_quotes": int(events[TENOR].isna().sum()),
            "exclusion_reason_counts_at_1d": dict(reasons),
            "ecb_workbook_update": "2025-11-04",
        },
        "estimation": {
            "model": "Univariate OLS with intercept",
            "reported_scale": "percent log EUR/NOK return per +10 bp OIS1Y repricing, with +25 bp and one-sample-SD scalings also retained",
            "primary_interval": "Descriptive 95% percentile interval from paired chronological circular event-block bootstrap",
            "block_length_events": BLOCK_EVENTS, "bootstrap_draws": BOOTSTRAP_DRAWS,
            "seed_base": SEED, "seed_per_horizon": "seed_base + horizon_business_days",
            "secondary_interval": "HC3 heteroskedasticity-robust asymptotic normal 95% interval; not robust to serial dependence",
            "multiple_horizons": "Three prespecified horizons. In addition to marginal 95% intervals, report Bonferroni-adjusted 98.333333% percentile intervals per horizon (bootstrap quantiles 0.833333% and 99.166667%) for a nominal 95% three-horizon family. Bootstrap/dependence limitations still apply; all results are exploratory.",
            "bonferroni_number_of_comparisons": len(HORIZONS),
            "bonferroni_per_horizon_confidence_level": 1.0 - 0.05 / len(HORIZONS),
        },
        "results": results,
        "sources": [
            {"publisher": "Norges Bank", "url": fx_source["actual_download_url"], "source_page": fx_source["reference_url"], "file": "raw/market_fx.csv", "sha256": sha256(fx_path), "retrieved_utc": fx_source["retrieved_utc"]},
            {"publisher": "European Central Bank", "url": ecb_manifest["url"], "file": "data/ea_mpd_events.csv", "sha256": sha256(events_path), "raw_workbook_sha256": ecb_manifest["sha256"], "retrieved_utc": ecb_manifest["retrieved_utc"], "actual_workbook_last_update": "2025-11-04"},
        ],
        "limitations": [
            "Association only. No exogenous causal monetary-policy shock is identified, and Norwegian news, global risk and other simultaneous information can confound the relationship.",
            "The predictor includes information and forward-guidance effects as well as policy repricing; a +25 bp OIS1Y move is not necessarily a +25 bp ECB policy-rate shock.",
            "Twenty-five basis points is a coefficient reporting scale, not a claim that a +25 bp event was observed. The retained predictor range and sample standard deviation are reported beside the coefficients.",
            "Norges Bank reference fixings are at 14:15 CET and may precede parts of ECB announcements. A strictly pre-event baseline and strictly later target avoid labelling a same-day fixing as the complete event reaction, but include unrelated overnight and multi-day news.",
            "Twenty-business-day response windows can overlap. Three-event circular blocks address local dependence heuristically; neither these descriptive bootstrap intervals nor HC3 ensure valid inference under arbitrary longer dependence or regime changes.",
            "Marginal 95% intervals are shown alongside Bonferroni-adjusted 98.333333% intervals for three prespecified horizons. These are exploratory descriptive bootstrap intervals; the adjustment does not remove confounding, regime instability or arbitrary serial dependence. Statistical association is not a demonstrated forecast or trading advantage.",
            "The retained ECB workbook ends on 30 October 2025. This historical module is excluded from the current complete-sample forecasting model; missing later events are not imputed as zero.",
            "Reference middle rates are indicative, not executable bid/ask prices; carry, spreads and transaction costs are excluded.",
        ],
        "observation_file": "event_observations.csv",
    }
    (output_dir / "event_study.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print("Wrote", output_dir / "event_study.json")
    for item in results:
        print(item["horizon_business_days"], "business days: n=", item["n"], "coefficient per25bp=", round(item["coefficient_pct_per_25bp"], 4), "bootstrap95%=", [round(v, 4) for v in item["block_bootstrap_ci95"]], "overlap=", item["adjacent_outcome_window_overlap_count"])


if __name__ == "__main__":
    main()
