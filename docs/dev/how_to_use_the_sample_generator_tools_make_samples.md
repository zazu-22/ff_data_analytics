# How to Use the Sample Generator (tools/make_samples.py)

This guide explains how to generate **small, deterministic samples** for each provider in the Bell Keg League data pipeline using `tools/make_samples.py`. These samples are designed for:

- Validating dbt **schemas** and **tests**
- Building **local fixtures** for development
- Reproducing issues with minimal data

> The tool writes BOTH **CSV** and **Parquet**, plus a small `_meta.json` describing parameters used.

---

## Prerequisites (per provider)

### Common
- Python 3.11+
- `polars`, `pyarrow`, `pandas` installed (`uv pip install polars pyarrow pandas`)
- Repo structure from the SPEC (paths assumed below):
  - `ingest/nflverse/` (Python shim present)
  - `scripts/R/` (R runners present)
  - `config/projections/` & `config/scoring/` (YAMLs present)

### nflverse
- Python **shim** available: `ingest/nflverse/shim.py` and `ingest/nflverse/registry.py`
- Python deps: `nflreadpy`, `polars`, `pyarrow`
- Optional R fallback path requires R installed + `scripts/R/nflverse_load.R` + `nflreadr`

### Sleeper
- Internet access to public Sleeper API
- `requests` Python library
- **Input needed:** a **league_id** (we use `1230330435511275520` by default in examples)

### Google Sheets
- `gspread` and `google-auth`
- **Service Account** with read access to the league Google Sheet
- **Environment variable**: `GOOGLE_APPLICATION_CREDENTIALS_JSON` containing the **entire JSON** credentials blob
- **Sheet URL** for the commissioner SSoT

### KeepTradeCut (KTC)
- The provided sampler is a **stub** (generates synthetic top‑N rows). Replace with your fetcher when ready.

### FFanalytics (R)
- R 4.3+
- `scripts/R/ffanalytics_run.R` present; ffanalytics installed in your R env
- Current runner is a **stub** (writes an empty—but schema‑shaped—Parquet). Wire to `ffanalytics::getProjections(...)` when ready.

### SDIO (FantasyData exports)
- Local file paths to one or more CSV/Parquet exports

---

## Installation

Use `uv` (preferred) or `pip`:

```bash
uv pip install polars pyarrow pandas requests gspread google-auth
```

(For R providers, install R packages as per the SPEC; not required to run non‑R samples.)

---

## CLI Overview

```bash
python tools/make_samples.py <provider> [provider args] --out ./samples --max-rows 1000
```

- `provider` ∈ `{nflverse, sleeper, sheets, ktc, ffanalytics, sdio}`
- `--out` defaults to `./samples` (can be any writable path)
- `--max-rows` caps sample size per dataset (default 1000). All sampling is **deterministic** with a fixed seed.

---

## Usage by Provider (copy/paste examples)

### 1) nflverse (via Python shim; optional R fallback)
```bash
# players + weekly for 2023 week 1
python tools/make_samples.py nflverse \
  --datasets players weekly \
  --seasons 2023 \
  --weeks 1 \
  --out ./samples

# Force R fallback (requires R + nflreadr + scripts/R/nflverse_load.R)
python tools/make_samples.py nflverse \
  --datasets schedule \
  --seasons 2024 \
  --r-fallback \
  --out ./samples
```
**Outputs:**
```
./samples/nflverse/players/{players.csv, players.parquet, _meta.json}
./samples/nflverse/weekly/{weekly.csv, weekly.parquet, _meta.json}
```

### 2) Sleeper
```bash
python tools/make_samples.py sleeper \
  --datasets league users rosters players \
  --league-id 1230330435511275520 \
  --out ./samples
```
**Outputs:**
```
./samples/sleeper/league/{league.csv, league.parquet, _meta.json}
./samples/sleeper/users/{users.csv, users.parquet, _meta.json}
./samples/sleeper/rosters/{rosters.csv, rosters.parquet, _meta.json}
./samples/sleeper/players/{players.csv, players.parquet, _meta.json}
```

### 3) Google Sheets (commissioner tabs)
```bash
export GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type":"service_account", ... }'
python tools/make_samples.py sheets \
  --tabs contracts rosters cap draft_assets trade_conditions \
  --sheet-url "https://docs.google.com/..." \
  --out ./samples
```
**Output per tab:**
```
./samples/sheets/<tab>/{<tab>.csv, <tab>.parquet, _meta.json}
```

### 4) KeepTradeCut (stubbed data)
```bash
python tools/make_samples.py ktc \
  --assets players picks \
  --top-n 50 \
  --out ./samples
```
**Output:**
```
./samples/ktc/assets/{assets.csv, assets.parquet, _meta.json}
```
> Replace this stub with your actual KTC fetcher when ready.

### 5) FFanalytics (R runner)
```bash
python tools/make_samples.py ffanalytics \
  --config config/projections/ffanalytics_projections_config.yaml \
  --scoring config/scoring/sleeper_scoring_rules.yaml \
  --weeks 1 --positions QB RB WR TE --sites fantasypros numberfire \
  --out ./samples
```
**Output:**
```
./samples/ffanalytics/projections/{projections.csv, projections.parquet, _meta.json}
```
> Current runner emits a **schema-only stub**. When wired to ffanalytics, it will contain real projections.

### 6) SDIO (FantasyData exports)
```bash
python tools/make_samples.py sdio \
  --paths /path/to/player_game_2023.csv /path/to/boxscore_2023.parquet \
  --out ./samples
```
**Output per file:**
```
./samples/sdio/<dataset>/{<dataset>.csv, <dataset>.parquet, _meta.json}
```

---

## What’s Stubbed vs. Ready (Action Items)

- **KTC sampler** → **STUB**: Replace with real fetcher (respect robots/ToS, add caching). Update `tools/make_samples.py: sample_ktc`.
- **FFanalytics runner** → **STUB**: Implement:
  - `ffanalytics::getProjections(...)` with `sites` from YAML (`config/projections/ffanalytics_projections_config.yaml`).
  - Apply `weight`s and scoring rules from `config/scoring/sleeper_scoring_rules.yaml`.
  - Emit long-form table with columns: `player, position, team, season, week, projected_points, site_id, site_weight, generated_at`.
- **Sheets sampler**: Requires service-account JSON in `GOOGLE_APPLICATION_CREDENTIALS_JSON` and that the account has read access to the sheet.

---

## Inputs Required (per provider)

- **nflverse**: `--datasets`, optional `--seasons`, `--weeks`.
- **Sleeper**: `--league-id` (or env `LEAGUE_ID`).
- **Sheets**: `--sheet-url`, env `GOOGLE_APPLICATION_CREDENTIALS_JSON`.
- **KTC**: choose `--assets` and `--top-n` (until replaced by real fetcher).
- **FFanalytics**: `--config` and `--scoring` YAML paths (already generated for you); optional `--weeks`, `--positions`, `--sites`.
- **SDIO**: `--paths` to one or more local CSV/Parquet files.

---

## Tips
- Keep samples small (default `--max-rows 1000`) for fast CI and dbt checks.
- Commit samples to a separate branch or a dedicated `samples/` artifact store; avoid bloating the repo.
- The tool is **deterministic** (fixed seed), so re-runs produce comparable samples.

---

## Troubleshooting
- **No R installed** but you run `--r-fallback` or `ffanalytics`: install R 4.3+ per SPEC and try again.
- **Sheets auth error**: confirm the service account email has read access to the sheet and the env var contains the full JSON.
- **Missing columns**: schemas differ slightly by loader; open an issue with the `_meta.json` attached.

---

## Contact
Post issues in the repo under **Data Pipeline → Samples** with command used, `_meta.json`, and any stack traces.

