"""
samsung.py - reads a Samsung Health data export and turns it into one simple
row per day: steps, distance, walking sessions, sleep and weight.

Samsung's CSV files look like this:
  line 1: file info, e.g. "com.samsung.shealth.step_daily_trend,7013005,6"   (skipped)
  line 2: column names, sometimes long like "com.samsung.health.exercise.duration"
  line 3+: the data
You can upload the individual CSV files, or the whole export folder as a .zip.
"""

import io
import zipfile

import pandas as pd

# Which Samsung files we use, matched by part of the file name
FILES = {
    "steps": "step_daily_trend",
    "exercise": "shealth.exercise.",
    "sleep": "health.sleep.",
    "weight": "health.weight.",
}


def _read_csv(data: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(data), skiprows=1, index_col=False, encoding="utf-8-sig", low_memory=False)
    # "com.samsung.health.exercise.duration" -> "duration"
    df.columns = [str(c).split(".")[-1] for c in df.columns]
    return df


def _local_time(df: pd.DataFrame, column: str) -> pd.Series:
    """Samsung stores times in UTC with a separate offset like 'UTC+0530'. Convert to local time."""
    times = pd.to_datetime(df[column], errors="coerce")
    if "time_offset" in df:
        off = df["time_offset"].astype(str).str.extract(r"UTC([+-])(\d{2})(\d{2})")
        sign = off[0].map({"+": 1, "-": -1}).fillna(0)
        minutes = sign * (off[1].astype(float).fillna(0) * 60 + off[2].astype(float).fillna(0))
        times = times + pd.to_timedelta(minutes, unit="m")
    return times


def collect_files(uploads) -> dict[str, bytes]:
    """Find the files we need among the uploads (CSV files and/or a .zip of the export folder)."""
    found: dict[str, tuple[str, bytes]] = {}

    def consider(name: str, read):
        lower = name.lower().replace("\\", "/").split("/")[-1]
        if not lower.endswith(".csv"):
            return
        for kind, pattern in FILES.items():
            if pattern in lower and kind not in found:
                found[kind] = (lower, read())

    for up in uploads:
        if up.name.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(up.getvalue())) as z:
                for name in z.namelist():
                    consider(name, lambda n=name: z.read(n))
        else:
            consider(up.name, up.getvalue)
    return {kind: data for kind, (_, data) in found.items()}


def parse_steps(data: bytes) -> pd.DataFrame:
    df = _read_csv(data)
    df["date"] = pd.to_datetime(df["day_time"], errors="coerce").dt.date
    # source_type -2 = Samsung's combined total from all devices; fall back to the highest count
    if "source_type" in df and (df["source_type"] == -2).any():
        df = df[df["source_type"] == -2]
    daily = df.groupby("date").agg(steps=("count", "max"), distance_m=("distance", "max"))
    return pd.DataFrame({"steps": daily["steps"].astype(int), "distance_km": (daily["distance_m"] / 1000).round(2)})


def parse_exercise(data: bytes) -> pd.DataFrame:
    df = _read_csv(data)
    df["date"] = _local_time(df, "start_time").dt.date
    daily = df.groupby("date").agg(
        workouts=("duration", "size"),
        workout_min=("duration", lambda s: s.sum() / 60000),  # milliseconds -> minutes
        workout_km=("distance", lambda s: s.fillna(0).sum() / 1000),
        workout_kcal=("calorie", "sum"),
    )
    return daily.round(1)


def parse_sleep(data: bytes) -> pd.DataFrame:
    df = _read_csv(data)
    start, end = _local_time(df, "start_time"), _local_time(df, "end_time")
    df["hours"] = (end - start).dt.total_seconds() / 3600
    df["date"] = end.dt.date  # a night's sleep counts for the day you wake up
    df = df[(df["hours"] > 0) & (df["hours"] < 24)]
    return df.groupby("date").agg(sleep_hours=("hours", "sum")).round(1)


def parse_weight(data: bytes) -> pd.DataFrame:
    df = _read_csv(data)
    df["date"] = _local_time(df, "start_time" if "start_time" in df else "create_time").dt.date
    df = df[pd.to_numeric(df["weight"], errors="coerce") > 0]
    return df.groupby("date").agg(weight_kg=("weight", "last")).round(1)


PARSERS = {"steps": parse_steps, "exercise": parse_exercise, "sleep": parse_sleep, "weight": parse_weight}


def import_export(uploads) -> tuple[dict, list[str], list[str]]:
    """Returns (daily data as {"2026-11-13": {...}}, what was imported, what was missing/failed)."""
    files = collect_files(uploads)
    frames, imported, problems = [], [], []
    for kind, parser in PARSERS.items():
        if kind not in files:
            problems.append(f"No {kind} file found")
            continue
        try:
            frames.append(parser(files[kind]))
            imported.append(kind)
        except Exception as err:  # Samsung formats vary by version, so never crash the app
            problems.append(f"Couldn't read the {kind} file ({err})")

    if not frames:
        return {}, imported, problems
    combined = pd.concat(frames, axis=1).sort_index()
    combined = combined[pd.notna(combined.index)]
    daily = {
        str(day): {k: (v.item() if hasattr(v, "item") else v) for k, v in row.dropna().items()}
        for day, row in combined.iterrows()
    }
    return daily, imported, problems
