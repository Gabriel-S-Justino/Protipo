"""Pure scientific functions. Coverage is independent of positive fire detections."""

from collections import defaultdict
from datetime import date, timedelta, datetime, timezone
import calendar as civil_calendar
import math
import random
import statistics as stats

MIN_YEARS = 3
MIN_CALIBRATION_MONTHS = 6
MIN_CALIBRATION_YEARS = 3


def quantile(values, q):
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lo = int(index)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)


def calibrate(pairs):
    """Pairs: (year, MODIS, VIIRS), same cell, dates and canonical reference satellite.
    Includes VIIRS zero months; MODIS zero cannot identify a multiplicative ratio.
    Bootstrap resamples entire years; validation holds out an entire year.
    """
    usable = [(y, m, v) for y, m, v in pairs if m > 0 and v >= 0]
    years = sorted({y for y, _, _ in usable})
    if len(usable) < MIN_CALIBRATION_MONTHS or len(years) < MIN_CALIBRATION_YEARS:
        return None
    factor = stats.median(v / m for _, m, v in usable)
    if factor <= 0:
        return None
    errors, baseline = [], []
    for held in years:
        train = [(m, v) for y, m, v in usable if y != held]
        ratio = stats.median(v / m for m, v in train)
        for y, m, v in usable:
            if y == held:
                errors.append(abs(v - m * ratio))
                baseline.append(abs(v - m))
    mae, naive = stats.mean(errors), stats.mean(baseline)
    rng = random.Random(42)
    boot = []
    for _ in range(300):
        sampled = [
            p for y in rng.choices(years, k=len(years)) for p in usable if p[0] == y
        ]
        boot.append(stats.median(v / m for _, m, v in sampled))
    return {
        "factor": factor,
        "low": quantile(boot, 0.025),
        "high": quantile(boot, 0.975),
        "months": len(usable),
        "years": len(years),
        "mae": mae,
        "baseline_mae": naive,
        "validated": mae <= naive,
        "method": "cell_ratio_year_bootstrap",
    }


def period_start(day, kind):
    if kind == "month":
        return day.replace(day=1)
    return day - timedelta(days=day.weekday())


def period_days(start, kind):
    length = (
        civil_calendar.monthrange(start.year, start.month)[1] if kind == "month" else 7
    )
    return [start + timedelta(days=n) for n in range(length)]


def bucket(start, kind):
    return start.month if kind == "month" else start.isocalendar().week


def probability(values):
    """Wilson 95% interval and rolling-origin Brier score; inputs (year,count).
    A year with coverage and zero detections is a valid negative observation.
    """
    values = sorted(values)
    n = len(values)
    if n < MIN_YEARS:
        return None
    positives = sum(v >= 1 for _, v in values)
    p = positives / n
    z = 1.959963984540054
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    errors = []
    prior = []
    for _, value in values:
        if len(prior) >= MIN_YEARS:
            estimate = (sum(prior) + 0.5) / (
                len(prior) + 1
            )  # Jeffreys smoothing, train only
            errors.append((estimate - int(value >= 1)) ** 2)
        prior.append(int(value >= 1))
    return {
        "probability": p,
        "ci_low": max(0, center - margin),
        "ci_high": min(1, center + margin),
        "years_used": n,
        "expected_count": stats.mean(v for _, v in values),
        "confidence": "medium" if n >= 8 and len(errors) >= 3 else "low",
        "validation": {
            "brier_score": stats.mean(errors) if errors else None,
            "test_years": len(errors),
            "method": "rolling_origin",
            "interval": "Wilson 95%; excludes sensor/model uncertainty",
        },
    }


def calendar_rows(daily, covered_days, kind, today=None):
    """Only fully acquired, completed periods. Unknown coverage is never a zero."""
    today = today or datetime.now(timezone.utc).date()
    starts = sorted({period_start(d, kind) for d in covered_days})
    buckets = defaultdict(list)
    for start in starts:
        days = period_days(start, kind)
        if days[-1] >= today or not all(d in covered_days for d in days):
            continue
        year = start.year if kind == "month" else start.isocalendar().year
        buckets[bucket(start, kind)].append((year, sum(daily.get(d, 0) for d in days)))
    return {
        b: result for b, values in buckets.items() if (result := probability(values))
    }
