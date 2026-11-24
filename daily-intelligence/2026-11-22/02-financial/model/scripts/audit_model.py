#!/usr/bin/env python3
"""Independent arithmetic, timing, provenance and future-information checks.

This checks published artifacts against observed data and invariants. It is not
an independent economic identification exercise or a claim of real-time vintages.
Only output/audit.json is written; no inputs or model outputs are altered.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import traceback

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reject_constant(value):
    raise ValueError(f"Nonstandard JSON numeric constant: {value}")


def read_json(path):
    return json.loads(path.read_text(), parse_constant=reject_constant)


def same(a, b, label, tolerance=2e-9):
    if not math.isfinite(float(a)) or not math.isfinite(float(b)):
        raise AssertionError(f"Nonfinite number: {label}: {a}, {b}")
    if not math.isclose(float(a), float(b), rel_tol=tolerance, abs_tol=tolerance):
        raise AssertionError(f"{label}: {a} != {b}")


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def main():
    specification = importlib.util.spec_from_file_location("eur_nok_run_model", ROOT / "scripts/run_model.py")
    model = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(model)
    raw = model.load_data()
    features = model.generate_features(raw)
    results = read_json(OUT / "results.json")
    predictions = read_json(OUT / "predictions.json")
    ablations = read_json(OUT / "ablation_predictions.json")
    checks = []

    def check(name, function):
        try:
            detail = function()
            checks.append({"name": name, "status": "PASS", "detail": detail})
            print(f"PASS {name}")
        except Exception as error:
            checks.append({"name": name, "status": "FAIL", "detail": str(error), "traceback": traceback.format_exc()})
            print(f"FAIL {name}: {error}")

    def sources():
        market = read_json(ROOT / "data/market_manifest.json")
        macro = read_json(ROOT / "data/macro_manifest.json")
        sources = list(market["sources"].values()) + macro["sources"]
        for source in sources:
            path = ROOT / source["raw_file"]
            require(path.exists(), f"Missing retained source {path}")
            require(sha(path) == source["sha256"], f"Source hash mismatch {path}")
            require(path.stat().st_size == source["bytes"], f"Source byte count mismatch {path}")
        require(sha(ROOT / market["data_file"]) == market["data_sha256"], "Normalized market hash mismatch")
        require(sha(ROOT / "PROTOCOL.md") == results["metadata"]["protocol_sha256"], "Protocol changed after model run")
        return {"retained_sources_verified": len(sources), "market_panel_hash_verified": True, "protocol_hash_verified": True}

    def calendar_and_target_provenance():
        require(raw.index.equals(pd.period_range("2000-01", "2026-10", freq="M")), "Monthly calendar differs from protocol or contains gaps")
        require(not raw.spot_eurnok.isna().any(), "Missing target quote")
        require((raw.spot_eurnok > 0).all(), "Nonpositive target quote")
        daily = pd.read_csv(ROOT / "raw/market_fx.csv", sep=";")
        daily = daily[(daily.BASE_CUR == "EUR") & (daily.QUOTE_CUR == "NOK") & (daily.TENOR == "SP")]
        daily["month"] = pd.to_datetime(daily.TIME_PERIOD).dt.to_period("M")
        last = daily.sort_values("TIME_PERIOD").dropna(subset=["OBS_VALUE"]).groupby("month").tail(1).set_index("month")
        for month in raw.index:
            same(raw.loc[month, "spot_eurnok"], last.loc[month, "OBS_VALUE"], f"Last daily fixing {month}")
        require(raw.loc[:"2005-12", "usd_broad"].isna().all(), "Invented broad-dollar prehistory")
        require(raw.loc["2006-01":, "usd_broad"].notna().all(), "Unexpected broad-dollar missing block")
        return {"months": len(raw), "last_daily_quote_identities": len(raw), "target_is_month_end_not_month_average": True}

    def timing_and_samples():
        count = 0
        all_features = sorted(set(sum(model.MODEL_FEATURES.values(), [])))
        complete = features[all_features].notna().all(axis=1)
        information_fields = ["origin", "target", "actual", "spot_origin", "spot_target", "train_n", "train_end", "max_train_target"]
        for h_key, model_rows in predictions.items():
            h = int(h_key)
            reference = model_rows["rw"]
            origins = [r["origin"] for r in reference]
            require(origins == sorted(set(origins)), f"Unsorted or repeated origins h={h}")
            signature = [[r[k] for k in information_fields] for r in reference]
            for name, rows in {**model_rows, **{f"without_{k}": v for k, v in ablations[h_key].items()}}.items():
                require([[r[k] for k in information_fields] for r in rows] == signature, f"Unequal evaluation sample h={h}, {name}")
                for row in rows:
                    origin, target = pd.Period(row["origin"], "M"), pd.Period(row["target"], "M")
                    require(target == origin + h, f"Wrong target horizon {name} {origin}")
                    require(pd.Period(row["max_train_target"], "M") <= origin, f"Immature training label {name} {origin}")
                    require(pd.Period(row["train_end"], "M") + h == pd.Period(row["max_train_target"], "M"), "Training timestamp mismatch")
                    eligible = features.index[complete & (features.index <= origin - h)]
                    require(len(eligible) == row["train_n"] >= 60, f"Training count inconsistent with mature complete rows {name} {origin}")
                    require(str(eligible[-1]) == row["train_end"], f"Wrong final training origin {name} {origin}")
                    same(row["spot_origin"], raw.loc[origin, "spot_eurnok"], "Origin spot")
                    same(row["spot_target"], raw.loc[target, "spot_eurnok"], "Target spot")
                    same(row["actual"], 100 * math.log(row["spot_target"] / row["spot_origin"]), "Cumulative target identity")
                    same(row["baseline"], 0.0, "Random-walk target")
                    require(math.isfinite(row["predicted"]), f"Missing/nonfinite forecast {name} {origin}")
                    count += 1
            for row in reference:
                same(row["predicted"], 0.0, "Random-walk prediction")
            for index, row in enumerate(model_rows["ensemble"]):
                same(row["predicted"], 0.25 * model_rows["ar1"][index]["predicted"] + 0.25 * model_rows["full"][index]["predicted"], "Fixed ensemble weights")
        return {"prediction_rows_verified_including_ablations": count, "models_share_sample": True, "training_labels_mature_at_origin": True}

    def arithmetic():
        count = 0
        for h, block in results["horizons"].items():
            by_model = {s["id"]: s for s in block["models"]}
            require(set(by_model) == set(predictions[h]), "Model ID mismatch")
            for name, rows in predictions[h].items():
                s = by_model[name]
                errors = [r["actual"] - r["predicted"] for r in rows]
                n = len(rows)
                require(s["n"] == n, f"Wrong metric sample size {h}/{name}")
                mae = sum(abs(e) for e in errors) / n
                same(s["mae"], mae, "MAE")
                same(s["rmse"], math.sqrt(sum(e * e for e in errors) / n), "RMSE")
                same(s["bias"], sum(errors) / n, "Mean signed error")
                same(s["win_rate"], sum(abs(e) < abs(r["actual"]) for r, e in zip(rows, errors)) / n, "RW win rate")
                if name == "rw":
                    require(s["direction_accuracy"] is None, "RW has no directional forecast")
                else:
                    same(s["direction_accuracy"], sum(np.sign(r["actual"]) == np.sign(r["predicted"]) for r in rows) / n, "Direction accuracy")
                same(s["improvement_vs_rw"], by_model["rw"]["mae"] - mae, "Paired gain vs RW")
                same(s["improvement_vs_ar1"], by_model["ar1"]["mae"] - mae, "Paired gain vs AR1")
                for key in ["improvement_ci", "ar1_improvement_ci", "longer_block_ci"]:
                    lo, hi = s[key]
                    require(math.isfinite(lo) and math.isfinite(hi) and lo <= hi, f"Invalid interval {h}/{name}/{key}")
                require(s["block_months"] >= max(3, int(h)), "Block shorter than overlap horizon")
                count += 1
            for ablation in block["ablations"]:
                rr = ablations[h][ablation["block"]]
                without = sum(abs(r["actual"] - r["predicted"]) for r in rr) / len(rr)
                same(ablation["without_mae"], without, "Ablation MAE")
                same(ablation["full_mae"], by_model["full"]["mae"], "Full-model MAE in ablation")
                same(ablation["incremental_gain"], without - by_model["full"]["mae"], "Block incremental gain")
                require(bool(ablation["exploratory"]), "Ablation presented as confirmatory")
            scenario = block["scenario"]
            same(scenario["baseline_prediction"], scenario["intercept"] + sum(x["value"] * x["coefficient"] for x in scenario["features"]), "Scenario coefficient identity")
        return {"model_metric_sets_verified": count, "ablation_and_scenario_arithmetic_verified": True}

    def calibration():
        band_rows = 0
        for h, blocks in predictions.items():
            summaries = {s["id"]: s for s in results["horizons"][h]["models"]}
            for name, rows in blocks.items():
                valid = []
                for index, row in enumerate(rows):
                    past = [p["actual"] - p["predicted"] for p in rows[:index] if p["target"] <= row["origin"]][-60:]
                    require(row["calibration_n"] == len(past), f"Wrong mature calibration count {h}/{name}/{row['origin']}")
                    if len(past) < 24:
                        require(row["lower"] is None and row["upper"] is None, "Premature prediction band")
                    else:
                        lo, hi = np.quantile(past, [0.05, 0.95])
                        same(row["lower"], row["predicted"] + lo, "Lower empirical band")
                        same(row["upper"], row["predicted"] + hi, "Upper empirical band")
                        valid.append(row)
                        band_rows += 1
                s = summaries[name]
                require(s["interval_n"] == len(valid), f"NaN/missing bands counted as valid {h}/{name}")
                if valid:
                    same(s["interval_coverage"], sum(r["lower"] <= r["actual"] <= r["upper"] for r in valid) / len(valid), "Band coverage denominator")
            for snapshot in results["horizons"][h]["latest_forecasts"]:
                require(snapshot["origin"] == str(raw.index[-1]), "Snapshot origin is not the latest observed month")
                require(pd.Period(snapshot["target_month"], "M") == raw.index[-1] + int(h), "Snapshot horizon incorrect")
                rows = blocks[snapshot["model_id"]]
                past = [r["actual"] - r["predicted"] for r in rows if r["target"] <= snapshot["origin"]][-60:]
                require(snapshot["calibration_n"] == len(past), "Snapshot calibration count mismatch")
                if len(past) >= 24:
                    same(snapshot["prob_nok_depreciation"], sum(snapshot["prediction"] + e > 0 for e in past) / len(past), "Residual-based empirical probability")
        return {"mature_empirical_bands_checked": band_rows, "missing_early_bands_excluded_from_coverage": True}

    def multiplicity():
        family = []
        for h in results["horizons"].values():
            for s in h["models"]:
                for base in ["rw", "ar1"]:
                    if s["id"] not in [base, "rw"]:
                        p = s[f"p_{base}"]
                        require(0 <= p <= 1, "Invalid raw p-value")
                        family.append((p, s, base))
        family.sort(key=lambda entry: entry[0])
        require(results["multiplicity"]["family_size"] == len(family) == 45, "Incomplete declared comparison family")
        cumulative = 0.0
        for index, (p, s, base) in enumerate(family):
            cumulative = max(cumulative, min(1.0, (len(family) - index) * p))
            same(s[f"p_{base}_holm"], cumulative, "Holm step-down adjustment")
        require("Latest-vintage" in results["metadata"]["validation_label"], "Vintage classification missing")
        require("not an October-issued" in results["metadata"]["forecast_timestamp_warning"], "Retrospective snapshot warning missing")
        return {"holm_family_size": len(family), "snapshot_and_vintage_warnings_present": True}

    def future_information():
        cols = sorted(set(sum(model.MODEL_FEATURES.values(), [])))
        checked = 0
        for cutoff in ["2017-12", "2020-12", "2023-12"]:
            period = pd.Period(cutoff, "M")
            future = raw.copy()
            future.loc[future.index > period] = future.loc[future.index > period] * 9.0 + 17.0
            altered = model.generate_features(future)
            pd.testing.assert_frame_equal(features.loc[:period, cols], altered.loc[:period, cols], check_exact=True)
            # Same-month delayed-market observations and the two most recent
            # macro observation months must not change the origin's features.
            delayed = raw.copy()
            delayed.loc[delayed.index >= period, ["brent", "vix", "usd_broad"]] *= 13.0
            macro_cols = ["no_hicp_yoy", "ea_hicp_yoy", "no_ip_yoy", "ea_ip_yoy"]
            delayed.loc[delayed.index >= period - 1, macro_cols] += 500.0
            altered = model.generate_features(delayed)
            pd.testing.assert_frame_equal(features.loc[:period, cols], altered.loc[:period, cols], check_exact=True)
            # Changing only the forecast-origin row must not change fitted
            # coefficients/intercept for a fixed training set.
            train = features.loc[:period - 1].dropna(subset=cols).copy()
            train["target"] = 100 * np.log(raw.spot_eurnok.shift(-1) / raw.spot_eurnok).reindex(train.index)
            origin = features.loc[period]
            shifted = origin.copy()
            shifted[model.FULL] = shifted[model.FULL] * 15.0 + 400.0
            _, coefficients, intercept = model.fit_predict(train, origin, model.FULL)
            _, alternate_coefficients, alternate_intercept = model.fit_predict(train, shifted, model.FULL)
            np.testing.assert_array_equal(coefficients, alternate_coefficients)
            same(intercept, alternate_intercept, "Fitting independent of forecast-origin values", tolerance=0)
            checked += 1
        return {"perturbation_cutoffs": checked, "post_origin_changes_do_not_change_past_features": True,
                "declared_publication_lags_verified_by_perturbation": True, "forecast_origin_excluded_from_fitting": True}

    def truncated_reproduction():
        # A snapshot calculated with the entire future removed must equal the
        # corresponding previously saved out-of-sample forecast. This exercises
        # the production walk-forward path, rather than copying its fit logic.
        count = 0
        for cutoff in ["2020-12", "2023-12"]:
            shorter = features.loc[:cutoff].copy()
            for h in [1, 3, 6]:
                summary, _, _ = model.run_horizon(shorter, h)
                for snapshot in summary["latest_forecasts"]:
                    name = snapshot["model_id"]
                    original = next(r for r in predictions[str(h)][name] if r["origin"] == cutoff)
                    same(snapshot["prediction"], original["predicted"], f"Future-truncated forecast {cutoff}/h{h}/{name}")
                    same(snapshot["lower"], original["lower"], "Future-truncated lower band")
                    same(snapshot["upper"], original["upper"], "Future-truncated upper band")
                    count += 1
        return {"forecast_and_band_reproductions": count, "future_removed_cutoffs": ["2020-12", "2023-12"], "horizons": [1, 3, 6]}

    for name, function in [
        ("retained_source_integrity", sources),
        ("continuous_calendar_and_month_end_quote_provenance", calendar_and_target_provenance),
        ("mature_training_labels_and_equal_model_samples", timing_and_samples),
        ("forecast_metric_ablation_and_scenario_arithmetic", arithmetic),
        ("empirical_band_maturity_and_coverage", calibration),
        ("multiplicity_and_historical_timestamp_disclosures", multiplicity),
        ("future_and_unreleased_input_perturbations", future_information),
        ("forecast_reproduction_after_removing_entire_future", truncated_reproduction),
    ]:
        check(name, function)
    failures = [c for c in checks if c["status"] == "FAIL"]
    paths = [ROOT / "scripts/run_model.py", ROOT / "scripts/audit_model.py", ROOT / "PROTOCOL.md", ROOT / "data/market.csv", ROOT / "data/macro.csv", OUT / "results.json", OUT / "predictions.json", OUT / "ablation_predictions.json"]
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not failures else "FAIL", "check_count": len(checks), "failure_count": len(failures),
        "scope": "Independent artifact arithmetic, chronological eligibility, source retention, input availability perturbations and truncated-history reproduction. No claim of a causal or real-time-vintage validation.",
        "checks": checks,
        "artifact_sha256": {str(path.relative_to(ROOT)): sha(path) for path in paths},
        "interpretation_boundaries": [
            "Passing these checks does not establish predictive value; use the reported loss comparisons and adjusted uncertainty.",
            "This is latest-vintage pseudo-out-of-sample validation; publication lags cannot restore historical data vintages.",
            "The original monthly-average return target and this end-month target differ. Their MAEs cannot be read as a before/after performance comparison.",
            "Empirical residual-based probabilities and bands are descriptive and not externally calibrated guarantees.",
        ],
    }
    (OUT / "audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "checks": len(checks), "failures": len(failures)}))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
