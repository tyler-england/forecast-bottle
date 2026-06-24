"""
prediction.py

Given a list of raw feed-log strings (from Google Keep), parse them into a
DataFrame, then estimate:
  - when the next feed will be needed
  - how many mL that feed should be
  - how many minutes of breastfeeding that equates to

Returns a FeedPrediction dataclass, or raises ValueError with a descriptive
message if prediction is not possible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FeedPrediction:
    time_next: datetime
    qty_ml: int               # bottle mL for the next feed
    bf_mins: int              # breastfeed minutes equivalent
    time_last: datetime
    avg_feed_ml: int          # average single-feed size (mL)
    avg_daily_ml: float       # average daily total (mL)
    avg_feed_interval: timedelta


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

# Supported date formats in the Keep note (with and without explicit year).
_DATE_FMTS_WITH_YEAR = ["%b %d %Y"]
_DATE_FMTS_WITHOUT_YEAR = ["%b %d"]

# Time-of-day formats that appear after the comma separator.
_TIME_FMTS = ["%I:%M %p", "%I:%M%p"]

# Regex to pull mL and BF-minutes out of the quantity portion of a line.
_ML_RE = re.compile(r"(\d+)\s*ml", re.IGNORECASE)
_BF_RE = re.compile(r"(\d+)\s*min", re.IGNORECASE)


def _parse_date(raw_day: str, today: datetime) -> Optional[datetime]:
    """
    Try to parse *raw_day* (the part before the dash) as a date.
    If no year is present, infer the most recent past occurrence.
    Returns a datetime at midnight, or None on failure.
    """
    raw_day = raw_day.strip().rstrip(",")

    # Explicit year (e.g. "Jan 1 2024")
    for fmt in _DATE_FMTS_WITH_YEAR:
        try:
            return datetime.strptime(raw_day, fmt)
        except ValueError:
            pass

    # No year — pick the most recent occurrence that is not in the future.
    for fmt in _DATE_FMTS_WITHOUT_YEAR:
        try:
            candidate = datetime.strptime(f"{raw_day} {today.year}", f"{fmt} %Y")
            if candidate > today:
                candidate = candidate.replace(year=today.year - 1)
            return candidate
        except ValueError:
            pass

    return None


def _parse_datetime(date_obj: datetime, raw_time: str) -> Optional[datetime]:
    """
    Combine *date_obj* with *raw_time* (e.g. "3:00 pm").
    Returns a datetime, or None on failure.
    """
    raw_time = raw_time.strip()
    for fmt in _TIME_FMTS:
        try:
            t = datetime.strptime(raw_time, fmt)
            return date_obj.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        except ValueError:
            pass
    return None


def parse_feed_log(data_list: list[str]) -> pd.DataFrame:
    """
    Parse raw Keep-note lines into a DataFrame with columns:
      Date (str YYYY-MM-DD), Time (str HH:MM:SS), mLs (int), BF_Mins (int)

    Lines that cannot be parsed are silently skipped.
    """
    today = datetime.today()
    rows = []

    for raw in data_list:
        raw = raw.strip()
        if not raw or "-" not in raw:
            continue

        # Split on the first dash only — the time part also contains colons/dashes.
        dash_pos = raw.index("-")
        raw_day = raw[:dash_pos]
        rest = raw[dash_pos + 1:].strip()   # e.g. "3:00 pm, 30 mL + 15 min BF"

        date_obj = _parse_date(raw_day, today)
        if date_obj is None:
            continue

        # Separate time from quantities at the comma.
        if "," not in rest:
            continue
        comma_pos = rest.index(",")
        raw_time = rest[:comma_pos]
        raw_qty = rest[comma_pos + 1:]

        dt = _parse_datetime(date_obj, raw_time)
        if dt is None:
            continue

        ml_match = _ML_RE.search(raw_qty)
        bf_match = _BF_RE.search(raw_qty)
        mls = int(ml_match.group(1)) if ml_match else 0
        bfs = int(bf_match.group(1)) if bf_match else 0

        rows.append({
            "Date": dt.strftime("%Y-%m-%d"),
            "Time": dt.strftime("%H:%M:%S"),
            "mLs": mls,
            "BF_Mins": bfs,
        })

    if not rows:
        return pd.DataFrame(columns=["Date", "Time", "mLs", "BF_Mins"])

    df = (
        pd.DataFrame(rows)
        .sort_values(["Date", "Time"])
        .reset_index(drop=True)
    )

    # Discard entries older than 30 days.
    cutoff = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    df = df[df["Date"] >= cutoff].reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Age-based feed guidelines
# ---------------------------------------------------------------------------

@dataclass
class AgeGuidelines:
    feed_min_ml: int
    feed_max_ml: int
    interval_min_hrs: float
    interval_max_hrs: float


def load_age_guidelines(age_doc_path: str) -> Optional[AgeGuidelines]:
    """
    Read age_info.txt and return feed-size and interval guidelines for the
    baby's current age in weeks.  Returns None if the file is missing or the
    baby's age does not match any row.

    Expected file format (first line is birthday, remaining lines are ranges):
        birthday: 2024-01-15
        0-4,60,120,1,3
        4-8,90,150,2,4
        ...
    Each data line: week_start-week_end, feed_min_ml, feed_max_ml, min_hrs, max_hrs
    """
    try:
        lines = Path(age_doc_path).read_text().splitlines()
    except OSError:
        return None

    today = datetime.today()
    birthday: Optional[datetime] = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Birthday line
        if line.lower().startswith("birthday"):
            try:
                birthday = datetime.strptime(line.split(":", 1)[1].strip(), "%Y-%m-%d")
            except (ValueError, IndexError):
                pass
            continue

        if birthday is None:
            continue

        # Guideline line
        parts = line.split(",")
        if len(parts) < 3:
            continue
        try:
            week_range = parts[0].split("-")
            wk_lo, wk_hi = int(week_range[0]), int(week_range[1])
            feed_min = int(parts[1])
            feed_max = int(parts[2])
            int_min = float(parts[3]) if len(parts) > 3 else 1.0
            int_max = float(parts[4]) if len(parts) > 4 else 4.0
        except (ValueError, IndexError):
            continue

        num_wks = (today - birthday).days // 7
        if wk_lo <= num_wks <= wk_hi:
            return AgeGuidelines(feed_min, feed_max, int_min, int_max)

    return None


# ---------------------------------------------------------------------------
# BF mL/min estimation
# ---------------------------------------------------------------------------

_BF_ML_PER_MIN_DEFAULT = 2.0
_BF_ML_PER_MIN_MAX = 10.0


def estimate_bf_ml_per_min(
    daily_mls: list[float],
    daily_bf_mins: list[float],
) -> float:
    """
    Estimate how many mL one minute of breastfeeding delivers.

    Strategy: if we have ≥2 days of bottle data, solve the linear system
      total_mL[day] = bottle_mL[day] + bf_ml_per_min * bf_mins[day]
    for pairs of days. Average all positive solutions found.

    Falls back to _BF_ML_PER_MIN_DEFAULT if the data are insufficient or
    the result is out of a plausible range.
    """
    if len(daily_mls) < 2 or sum(daily_mls) < 100:
        return _BF_ML_PER_MIN_DEFAULT

    estimates = []
    n = len(daily_mls)
    for i in range(n):
        for j in range(i + 1, n):
            delta_bf = daily_bf_mins[j] - daily_bf_mins[i]
            delta_ml = daily_mls[i] - daily_mls[j]
            if delta_bf == 0:
                continue
            rate = delta_ml / delta_bf
            if 0 < rate <= _BF_ML_PER_MIN_MAX:
                estimates.append(rate)

    if not estimates:
        return _BF_ML_PER_MIN_DEFAULT

    return sum(estimates) / len(estimates)


# ---------------------------------------------------------------------------
# Core prediction
# ---------------------------------------------------------------------------

_HISTORY_DAYS = 3          # how many past days to look at
_MAX_INTERVAL_HRS = 4      # hard cap on time between feeds
_INTAKE_WINDOW_HRS = 10    # rolling window for qty estimation
_ML_RATIO_FLOOR = 0.625    # don't penalise a past feed below this fraction


def _daily_sums(df: pd.DataFrame, col: str) -> dict[str, float]:
    """Return {date_str: sum} for *col*."""
    return df.groupby("Date")[col].sum().to_dict()


def _closest_feed_index(df: pd.DataFrame, target_time_str: str) -> pd.Series:
    """
    For each date in *df*, return the index of the row whose Time is closest
    to *target_time_str* (HH:MM:SS), accounting for midnight wrap-around.
    """
    t_target = pd.to_datetime(target_time_str, format="%H:%M:%S")
    df = df.copy()
    df["_tdiff"] = (
        pd.to_datetime(df["Time"], format="%H:%M:%S") - t_target
    ).abs()
    # Midnight wrap: if (24h - diff) < diff, use that instead.
    day = pd.Timedelta(hours=24)
    df["_tdiff"] = df["_tdiff"].apply(lambda d: min(d, day - d))
    return df.groupby("Date")["_tdiff"].idxmin()


def predict(
    df: pd.DataFrame,
    age_guidelines: Optional[AgeGuidelines],
    bf_ml_per_min: float,
) -> FeedPrediction:
    """
    Core prediction logic.  Separated from I/O so it can be unit-tested.

    Raises ValueError if there is not enough data.
    """
    if df.empty:
        raise ValueError("Feed log is empty after parsing.")

    today = datetime.today()

    # ------------------------------------------------------------------ #
    # Step 1: add BF mL column                                            #
    # ------------------------------------------------------------------ #
    df = df.copy()
    df["BF_mL"] = df["BF_Mins"] * bf_ml_per_min
    df["Total_mL"] = df["mLs"] + df["BF_mL"]

    # Verify the last row is complete (both columns zero = unfinished entry).
    if df["mLs"].iloc[-1] == 0 and df["BF_mL"].iloc[-1] == 0:
        raise ValueError(
            "Last feed entry has no mL and no BF — entry may be unfinished."
        )

    # ------------------------------------------------------------------ #
    # Step 2: establish reference window                                   #
    # ------------------------------------------------------------------ #
    cutoff_date = (today - timedelta(days=_HISTORY_DAYS)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    window = df[(df["Date"] >= cutoff_date) & (df["Date"] <= today_str)].copy()

    if window.empty:
        raise ValueError("No feed data in the last 3 days.")

    last_row = df.iloc[-1]
    time_last = datetime.strptime(
        f"{last_row['Date']} {last_row['Time']}", "%Y-%m-%d %H:%M:%S"
    )

    # ------------------------------------------------------------------ #
    # Step 3: predict WHEN the next feed will be                          #
    # ------------------------------------------------------------------ #
    last_time_str = last_row["Time"]
    last_total_ml = last_row["mLs"] + last_row["BF_mL"]
    if last_total_ml == 0 and len(window) >= 2:
        # Unfinished last entry — use the second-to-last.
        second_last = window.iloc[-2]
        last_total_ml = second_last["mLs"] + second_last["BF_mL"]

    # Find the closest feed in each past day to the current last-feed time.
    past_window = window[window["Date"] < today_str].copy()
    if past_window.empty:
        raise ValueError("Need at least one previous day of data to predict timing.")

    closest_idx = _closest_feed_index(past_window, last_time_str)

    intervals: list[timedelta] = []
    ml_ratios: list[float] = []

    fmt_full = "%Y-%m-%d %H:%M:%S"

    for date_str, row_idx in closest_idx.items():
        row = past_window.loc[row_idx]
        # Find the *next* feed after this one.
        next_candidates = past_window[
            (past_window["Date"] >= date_str)
            & (past_window.index > row_idx)
        ]
        if next_candidates.empty:
            # Wrap to the first feed of the following day.
            next_day = (
                datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)
            ).strftime("%Y-%m-%d")
            next_candidates = window[window["Date"] == next_day]

        if next_candidates.empty:
            # Last resort: use the gap from the preceding feed.
            prev_candidates = past_window[past_window.index < row_idx]
            if prev_candidates.empty:
                continue
            prev_row = prev_candidates.iloc[-1]
            t1 = datetime.strptime(
                f"{prev_row['Date']} {prev_row['Time']}", fmt_full
            )
            t2 = datetime.strptime(f"{row['Date']} {row['Time']}", fmt_full)
            interval = t2 - t1
        else:
            next_row = next_candidates.iloc[0]
            t1 = datetime.strptime(f"{row['Date']} {row['Time']}", fmt_full)
            t2 = datetime.strptime(
                f"{next_row['Date']} {next_row['Time']}", fmt_full
            )
            interval = t2 - t1

        # Ignore nonsensical intervals (negative or > 6 hours).
        if not timedelta(0) < interval <= timedelta(hours=6):
            continue

        row_total = row["mLs"] + row["BF_mL"]
        ratio = (row_total / last_total_ml) if last_total_ml > 0 else 1.0
        ratio = max(ratio, _ML_RATIO_FLOOR)

        intervals.append(interval)
        ml_ratios.append(ratio)

    if not intervals:
        raise ValueError("Could not determine feed intervals from historical data.")

    # Scale each interval by the mL ratio (smaller feed → shorter gap).
    adjusted = [iv / r for iv, r in zip(intervals, ml_ratios)]
    avg_interval = sum(adjusted, timedelta()) / len(adjusted)

    time_next = time_last + avg_interval

    # Apply hard cap.
    time_max = time_last + timedelta(hours=_MAX_INTERVAL_HRS)
    time_next = min(time_next, time_max)

    # Apply age-based interval bounds.
    if age_guidelines:
        lo = timedelta(hours=age_guidelines.interval_min_hrs)
        hi = timedelta(hours=age_guidelines.interval_max_hrs)
        elapsed = time_next - time_last
        if elapsed < lo:
            time_next = time_last + lo
        elif elapsed > hi:
            time_next = time_last + hi

    # ------------------------------------------------------------------ #
    # Step 4: predict HOW MUCH at the next feed                           #
    # ------------------------------------------------------------------ #
    # For each of the past _HISTORY_DAYS days (and the current partial day),
    # sum all intake within the _INTAKE_WINDOW_HRS leading up to the
    # closest equivalent feed time.

    time_next_str = time_next.strftime("%H:%M:%S")
    broader_cutoff = (today - timedelta(days=_HISTORY_DAYS + 1)).strftime("%Y-%m-%d")
    broader = df[(df["Date"] >= broader_cutoff) & (df["Date"] <= today_str)].copy()
    broader["Total_mL"] = broader["mLs"] + broader["BF_mL"]

    qty_closest_idx = _closest_feed_index(
        broader[broader["Date"] < today_str], time_next_str
    )

    window_totals: list[float] = []
    fmt_full = "%Y-%m-%d %H:%M:%S"

    def _window_sum(sub: pd.DataFrame, before_dt: datetime) -> float:
        start_dt = before_dt - timedelta(hours=_INTAKE_WINDOW_HRS)
        mask = sub.apply(
            lambda r: start_dt
            <= datetime.strptime(f"{r['Date']} {r['Time']}", fmt_full)
            < before_dt,
            axis=1,
        )
        return sub.loc[mask, "Total_mL"].sum()

    for date_str, row_idx in qty_closest_idx.items():
        ref_row = broader.loc[row_idx]
        ref_dt = datetime.strptime(
            f"{ref_row['Date']} {ref_row['Time']}", fmt_full
        )
        window_totals.append(_window_sum(broader, ref_dt))

    # Current partial day: sum from now back _INTAKE_WINDOW_HRS.
    current_window_total = _window_sum(broader, today)
    window_totals.append(current_window_total)

    if len(window_totals) < 2:
        raise ValueError("Insufficient data for quantity prediction.")

    past_totals = window_totals[:-1]
    current_total = window_totals[-1]
    avg_window_total = sum(past_totals) / len(past_totals)

    qty_needed = avg_window_total - current_total

    # Floor: if already above average, use the max past day as the target.
    if qty_needed < 0:
        qty_needed = max(past_totals) - current_total

    # If still negative, baby has had plenty — use average feed size.
    avg_feed_ml = int(broader["Total_mL"].mean())

    if age_guidelines:
        feed_min = age_guidelines.feed_min_ml
        feed_max = age_guidelines.feed_max_ml
    else:
        feed_min, feed_max = 60, 180

    if qty_needed <= 0:
        qty_next = max(avg_feed_ml, feed_min)
    else:
        # Clamp to age-appropriate range.
        qty_next = max(feed_min, min(feed_max, qty_needed))

    # Round to nearest 10 mL for easy measuring.
    qty_next = int(round(qty_next / 10) * 10)

    bf_mins = int(qty_next / bf_ml_per_min)
    bf_mins = (bf_mins // 5) * 5  # round down to nearest 5

    # ------------------------------------------------------------------ #
    # Step 5: summary stats                                                #
    # ------------------------------------------------------------------ #
    daily_totals = broader.groupby("Date")["Total_mL"].sum()
    avg_daily_ml = daily_totals.mean()

    feed_times = []
    for i in range(len(broader) - 1):
        t1 = datetime.strptime(
            f"{broader.iloc[i]['Date']} {broader.iloc[i]['Time']}", fmt_full
        )
        t2 = datetime.strptime(
            f"{broader.iloc[i+1]['Date']} {broader.iloc[i+1]['Time']}", fmt_full
        )
        delta = t2 - t1
        if timedelta(0) < delta <= timedelta(hours=6):
            feed_times.append(delta)

    avg_interval = (
        sum(feed_times, timedelta()) / len(feed_times)
        if feed_times
        else timedelta(hours=2, minutes=30)
    )

    return FeedPrediction(
        time_next=time_next,
        qty_ml=qty_next,
        bf_mins=bf_mins,
        time_last=time_last,
        avg_feed_ml=avg_feed_ml,
        avg_daily_ml=avg_daily_ml,
        avg_feed_interval=avg_interval,
    )


# ---------------------------------------------------------------------------
# Public entry point (matches the original get_time_qty_summary signature)
# ---------------------------------------------------------------------------

def get_time_qty_summary(
    data_list: list[str],
    age_doc_path: Optional[str] = None,
) -> FeedPrediction:
    """
    Parse *data_list* and return a FeedPrediction.

    *age_doc_path* defaults to  <project_root>/age_info.txt  using the same
    directory-climbing logic as the original script.

    Raises ValueError with a human-readable message on failure.
    """
    if age_doc_path is None:
        age_doc_path = str(Path(__file__).parents[2] / "age_info.txt")

    df = parse_feed_log(data_list)
    if df.empty:
        raise ValueError("No valid feed entries could be parsed from the log.")

    age_guidelines = load_age_guidelines(age_doc_path)

    # Estimate BF mL/min from the last _HISTORY_DAYS days.
    today = datetime.today()
    cutoff = (today - timedelta(days=_HISTORY_DAYS)).strftime("%Y-%m-%d")
    recent = df[df["Date"] >= cutoff]

    ml_sums = _daily_sums(recent, "mLs")
    bf_sums = _daily_sums(recent, "BF_Mins")
    # Use only days present in both dicts, in consistent order.
    common_dates = sorted(set(ml_sums) & set(bf_sums), reverse=True)
    daily_mls = [ml_sums[d] for d in common_dates]
    daily_bf = [bf_sums[d] for d in common_dates]

    bf_ml_per_min = estimate_bf_ml_per_min(daily_mls, daily_bf)

    return predict(df, age_guidelines, bf_ml_per_min)
