"""
tools/make_samples.py

Programmatically create *small* deterministic samples for each target dataset so we can
validate dbt contracts, DQ tests, and loaders without pulling full tables.

Usage examples:
  # Sample nflverse players + weekly
  python tools/make_samples.py nflverse \
    --datasets players weekly \
    --seasons 2023 \
    --weeks 1 \
    --out ./samples

  # Sample Sleeper (uses LEAGUE_ID env or --league-id) for rosters/users
  python tools/make_samples.py sleeper \
    --datasets rosters users \
    --league-id 1230330435511275520 \
    --out ./samples

  # Sample Google Sheets tabs
  python tools/make_samples.py sheets --tabs contracts rosters cap --sheet-url <URL> --out ./samples

  # Sample KeepTradeCut (players + picks)
  python tools/make_samples.py ktc --assets players picks --top-n 50 --out ./samples

  # Sample FFanalytics projections (subset of sites/positions/weeks)
  python tools/make_samples.py ffanalytics \
    --config config/projections/ffanalytics_projections_config.yaml \
    --scoring config/scoring/sleeper_scoring_rules.yaml \
    --weeks 1 \
    --positions QB,RB,WR,TE \
    --sites fantasypros,numberfire \
    --out ./samples

  # Sample SDIO FantasyData exports (first 1,000 rows per file)
  python tools/make_samples.py sdio \
    --paths '/data/sdio/player_game_2023.csv /data/sdio/boxscore_2023.csv' \
    --out ./samples

Notes:
- All samplers write both Parquet and CSV,
  with a small sidecar _meta.json recording source + params.
- Random sampling uses a fixed seed for determinism.
"""

from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SEED = 42
random.seed(SEED)


def _ensure_out(root: Path, provider: str, dataset: str) -> Path:
    d = root / provider / dataset
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_outputs(
    df: pd.DataFrame, out_dir: Path, provider: str, dataset: str, meta: dict, max_rows: int = 500
):
    # thin the data deterministically
    if len(df) > max_rows:
        df = df.sample(n=max_rows, random_state=SEED)
    parquet = out_dir / f"{dataset}.parquet"
    csv = out_dir / f"{dataset}.csv"
    df.to_parquet(parquet.as_posix(), index=False)
    df.to_csv(csv.as_posix(), index=False)
    meta = {**meta, "provider": provider, "dataset": dataset, "rows": int(len(df)), "seed": SEED}
    (out_dir / "_meta.json").write_text(json.dumps(meta, indent=2))
    return {
        "csv": csv.as_posix(),
        "parquet": parquet.as_posix(),
        "meta": (out_dir / "_meta.json").as_posix(),
    }


# ---------- nflverse (python-first via nflreadpy; fallback optional) ----------
def sample_nflverse(
    datasets: list[str],
    out: Path,
    seasons: list[int] | None = None,
    weeks: list[int] | None = None,
    r_fallback: bool = False,
    max_rows: int = 1000,
):
    from ingest.nflverse.shim import load_nflverse  # expects your repo layout

    manifest = {}
    for ds in datasets:
        # Use shim to load; out_dir points to a temp build dir (not GCS) to read back and thin
        cache_dir = out / "_cache_nflverse"
        cache_dir.mkdir(parents=True, exist_ok=True)
        man = load_nflverse(
            ds,
            seasons=seasons,
            weeks=weeks,
            out_dir=cache_dir.as_posix(),
            loader_preference=("r_only" if r_fallback else "python_first"),
        )
        # Find the parquet the shim wrote (python path); if fallback to R only,
        # just skip read/return manifest
        dataset_dir = Path(man.get("partition_dir", cache_dir / ds))
        # Read all parquet files in the dir
        files = list(dataset_dir.glob("*.parquet"))
        if not files:
            # Nothing to thin—just record manifest and continue
            manifest[ds] = {
                "note": "No parquet files found (likely R fallback path only). See manifest.",
                "manifest": man,
            }
            continue
        # Concatenate and thin
        df = pd.concat((pd.read_parquet(f) for f in files), ignore_index=True)
        out_dir = _ensure_out(out, "nflverse", ds)
        paths = _write_outputs(
            df,
            out_dir,
            "nflverse",
            ds,
            {"seasons": seasons, "weeks": weeks, "loader_path": man.get("loader_path")},
            max_rows=max_rows,
        )
        manifest[ds] = paths
    return manifest


# ---------- Sleeper ----------
def _sleeper_get(endpoint: str, **params):
    import requests

    base = "https://api.sleeper.com"
    url = f"{base}{endpoint}"
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def sample_sleeper(datasets: list[str], out: Path, league_id: str | None, max_rows: int = 1000):
    if not league_id:
        league_id = os.getenv("LEAGUE_ID")
    if not league_id:
        raise SystemExit("Sleeper league_id is required (env LEAGUE_ID or --league-id).")

    manifest = {}
    for ds in datasets:
        if ds == "league":
            data = _sleeper_get(f"/v1/league/{league_id}")
            df = pd.json_normalize(data)
        elif ds == "users":
            data = _sleeper_get(f"/v1/league/{league_id}/users")
            df = pd.json_normalize(data)
        elif ds == "rosters":
            data = _sleeper_get(f"/v1/league/{league_id}/rosters")
            df = pd.json_normalize(data)
        elif ds == "players":
            # Use compact players; keep just a small subset of columns for sample
            data = _sleeper_get("/v1/players/nfl")
            # data is a dict keyed by player_id
            df = (
                pd.DataFrame.from_dict(data, orient="index")
                .reset_index()
                .rename(columns={"index": "player_id"})
            )
            keep_cols = [
                c
                for c in [
                    "player_id",
                    "full_name",
                    "position",
                    "team",
                    "years_exp",
                    "status",
                    "injury_status",
                ]
                if c in df.columns
            ]
            if keep_cols:
                df = df[keep_cols]
        else:
            raise SystemExit(f"Unknown Sleeper dataset: {ds}")

        out_dir = _ensure_out(out, "sleeper", ds)
        paths = _write_outputs(
            df, out_dir, "sleeper", ds, {"league_id": league_id}, max_rows=max_rows
        )
        manifest[ds] = paths
    return manifest


# ---------- Google Sheets (export sample rows using Sheets API) ----------
def sample_sheets(tabs: list[str], out: Path, sheet_url: str, max_rows: int = 1000):
    """
    Requires Google credentials set up. For sampling, we pull only the first N rows per tab.
    """
    import gspread  # pip install gspread google-auth
    from google.oauth2.service_account import Credentials

    # Try GOOGLE_APPLICATION_CREDENTIALS_JSON first (JSON content)
    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    # Fallback to GOOGLE_APPLICATION_CREDENTIALS (file path)
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if creds_json:
        # Environment variable contains JSON content directly
        creds = Credentials.from_service_account_info(
            json.loads(creds_json), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
    elif creds_path:
        # Environment variable contains path to JSON file
        if os.path.exists(creds_path):
            with open(creds_path) as f:
                creds_info = json.load(f)
            creds = Credentials.from_service_account_info(
                creds_info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
            )
        else:
            raise SystemExit(f"Credentials file not found at: {creds_path}")
    else:
        raise SystemExit(
            "Set GOOGLE_APPLICATION_CREDENTIALS_JSON (JSON content) or "
            "GOOGLE_APPLICATION_CREDENTIALS (file path) to sample Sheets."
        )
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(sheet_url)

    manifest = {}
    for tab in tabs:
        ws = sh.worksheet(tab)
        values = ws.get_all_values()
        if values:
            # Handle duplicate column names by appending a suffix
            columns = values[0]
            col_counts = {}
            unique_columns = []
            for col in columns:
                if col in col_counts:
                    col_counts[col] += 1
                    unique_columns.append(f"{col}_{col_counts[col]}")
                else:
                    col_counts[col] = 0
                    unique_columns.append(col)
            df = pd.DataFrame(values[1 : max_rows + 1], columns=unique_columns)
        else:
            df = pd.DataFrame()
        out_dir = _ensure_out(out, "sheets", tab)
        paths = _write_outputs(
            df, out_dir, "sheets", tab, {"sheet_url": sheet_url}, max_rows=max_rows
        )
        manifest[tab] = paths
    return manifest


# ---------- KeepTradeCut (players + picks; top-N) ----------
def sample_ktc(out: Path, assets: list[str], top_n: int = 100, max_rows: int = 1000):
    """
    Respectful scraping: small, top-N only; use cached endpoints if you have them.
    This function is a placeholder — wire it to your existing KTC fetcher.
    """
    # Placeholder small frame for contract. Replace with your actual fetch logic.
    rows = []
    for asset_type in assets:
        for i in range(min(top_n, 50)):
            rows.append(
                {
                    "asset_type": asset_type,
                    "asset_id": f"{asset_type}_{i}",
                    "rank": i + 1,
                    "ktc_value": 1000 - i * 3,
                    "asof_date": "2025-08-01",
                }
            )
    df = pd.DataFrame(rows)
    out_dir = _ensure_out(out, "ktc", "assets")
    return _write_outputs(
        df, out_dir, "ktc", "assets", {"assets": assets, "top_n": top_n}, max_rows=max_rows
    )


# ---------- FFanalytics (subset of sites/weeks/positions) ----------
def sample_ffanalytics(
    out: Path,
    config_yaml: str,
    scoring_yaml: str,
    weeks: list[int] | None = None,
    positions: list[str] | None = None,
    sites: list[str] | None = None,
    max_rows: int = 1000,
):
    import subprocess

    # Build arg list (avoids shell quoting and keeps line lengths short)
    runner = "scripts/R/ffanalytics_run.R"
    out_dir_arg = (out / "ffanalytics").as_posix()
    cmd = [
        "Rscript",
        runner,
        "--config",
        config_yaml,
        "--scoring",
        scoring_yaml,
        "--out_dir",
        out_dir_arg,
    ]
    # For now the R runner itself is responsible for subsetting; extend it later to accept filters.
    # Run the R runner and raise on non‑zero exit; no unused variable.
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    # Locate parquet (the runner writes it)
    dt = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    df_path = out / "ffanalytics" / f"dt={dt}" / f"projections_{dt}.parquet"
    if df_path.exists():
        df = pd.read_parquet(df_path)
        if positions is not None and "position" in df.columns:
            df = df[df["position"].isin(positions)]
        if weeks is not None and "week" in df.columns:
            df = df[df["week"].isin(weeks)]
        if sites is not None and "site_id" in df.columns:
            df = df[df["site_id"].isin(sites)]
        out_dir = _ensure_out(out, "ffanalytics", "projections")
        return _write_outputs(
            df,
            out_dir,
            "ffanalytics",
            "projections",
            {"positions": positions, "weeks": weeks, "sites": sites},
            max_rows=max_rows,
        )
    return {"note": "Runner wrote no parquet (stub mode?)"}


# ---------- SDIO FantasyData (local files) ----------
def sample_sdio(paths: list[str], out: Path, max_rows: int = 1000):
    manifest = {}
    for p in paths:
        pth = Path(p)
        if not pth.exists():
            manifest[pth.name] = {"error": "file not found"}
            continue
        df = pd.read_parquet(pth) if pth.suffix.lower() in {".parquet", ".pq"} else pd.read_csv(pth)
        dataset = pth.stem
        out_dir = _ensure_out(out, "sdio", dataset)
        paths_out = _write_outputs(
            df, out_dir, "sdio", dataset, {"source_file": pth.as_posix()}, max_rows=max_rows
        )
        manifest[dataset] = paths_out
    return manifest


# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="provider", required=True)

    # nflverse
    p_nv = sub.add_parser("nflverse")
    p_nv.add_argument("--datasets", nargs="+", required=True)
    p_nv.add_argument("--seasons", nargs="*", type=int, default=None)
    p_nv.add_argument("--weeks", nargs="*", type=int, default=None)
    p_nv.add_argument("--r-fallback", action="store_true")
    p_nv.add_argument("--out", default="./samples")
    p_nv.add_argument("--max-rows", type=int, default=1000)

    # sleeper
    p_sl = sub.add_parser("sleeper")
    p_sl.add_argument(
        "--datasets", nargs="+", required=True, choices=["league", "users", "rosters", "players"]
    )
    p_sl.add_argument("--league-id", default=os.getenv("LEAGUE_ID"))
    p_sl.add_argument("--out", default="./samples")
    p_sl.add_argument("--max-rows", type=int, default=1000)

    # sheets
    p_sh = sub.add_parser("sheets")
    p_sh.add_argument("--tabs", nargs="+", required=True)
    p_sh.add_argument("--sheet-url", required=True)
    p_sh.add_argument("--out", default="./samples")
    p_sh.add_argument("--max-rows", type=int, default=1000)

    # ktc
    p_ktc = sub.add_parser("ktc")
    p_ktc.add_argument("--assets", nargs="+", required=True, choices=["players", "picks"])
    p_ktc.add_argument("--top-n", type=int, default=100)
    p_ktc.add_argument("--out", default="./samples")
    p_ktc.add_argument("--max-rows", type=int, default=1000)

    # ffanalytics
    p_ffa = sub.add_parser("ffanalytics")
    p_ffa.add_argument("--config", required=True)
    p_ffa.add_argument("--scoring", required=True)
    p_ffa.add_argument("--weeks", nargs="*", type=int, default=None)
    p_ffa.add_argument("--positions", nargs="*", default=None)
    p_ffa.add_argument("--sites", nargs="*", default=None)
    p_ffa.add_argument("--out", default="./samples")
    p_ffa.add_argument("--max-rows", type=int, default=1000)

    # sdio
    p_sdio = sub.add_parser("sdio")
    p_sdio.add_argument("--paths", nargs="+", required=True)
    p_sdio.add_argument("--out", default="./samples")
    p_sdio.add_argument("--max-rows", type=int, default=1000)

    args = ap.parse_args()
    out = Path(args.out)

    if args.provider == "nflverse":
        res = sample_nflverse(
            args.datasets,
            out,
            seasons=args.seasons,
            weeks=args.weeks,
            r_fallback=args.r_fallback,
            max_rows=args.max_rows,
        )
    elif args.provider == "sleeper":
        res = sample_sleeper(args.datasets, out, league_id=args.league_id, max_rows=args.max_rows)
    elif args.provider == "sheets":
        res = sample_sheets(args.tabs, out, sheet_url=args.sheet_url, max_rows=args.max_rows)
    elif args.provider == "ktc":
        res = sample_ktc(out, assets=args.assets, top_n=args.top_n, max_rows=args.max_rows)
    elif args.provider == "ffanalytics":
        res = sample_ffanalytics(
            out,
            config_yaml=args.config,
            scoring_yaml=args.scoring,
            weeks=args.weeks,
            positions=args.positions,
            sites=args.sites,
            max_rows=args.max_rows,
        )
    elif args.provider == "sdio":
        res = sample_sdio(args.paths, out, max_rows=args.max_rows)
    else:
        raise SystemExit("Unknown provider")

    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
