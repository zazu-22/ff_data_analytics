# scripts/R/ffanalytics_run.R
# Runner for FantasyFootballAnalytics projections using a YAML config
# Usage:
#   Rscript scripts/R/ffanalytics_run.R --config config/projections/ffanalytics_projections_config.yaml --scoring config/scoring/sleeper_scoring_rules.yaml --out_dir gs://ff-analytics/raw/ffanalytics/projections

suppressPackageStartupMessages({
  library(optparse)
  library(yaml)
  library(jsonlite)
  library(arrow)
  library(lubridate)
  # library(ffanalytics) # ensure installed in renv; commented to avoid import error during generation
})

option_list <- list(
  make_option(c("--config"), type="character", help="YAML with sites/weights"),
  make_option(c("--scoring"), type="character", help="YAML with scoring rules"),
  make_option(c("--out_dir"), type="character", default="gs://ff-analytics/raw/ffanalytics/projections", help="Output directory root")
)
opt <- parse_args(OptionParser(option_list=option_list))

if (is.null(opt$config) || is.null(opt$scoring)) {
  stop("Missing --config or --scoring")
}

cfg <- yaml::read_yaml(opt$config)
scoring <- yaml::read_yaml(opt$scoring)

# ---- PSEUDO WORKFLOW (stub) ----
# sites <- cfg$projections$sites
# weights <- setNames(vapply(sites, `[[`, numeric(1), "weight"), vapply(sites, `[[`, character(1), "id"))
# proj <- ffanalytics::getProjections(sites = names(weights), scoringRules = scoring$scoring, avgMethod = "weighted", weight = weights)
# df <- proj$projections  # assume a long-form table; adjust as per actual package output

# For now, create an empty schema stub so pipeline CI doesn't break before package wiring:
df <- data.frame(
  player = character(0),
  position = character(0),
  team = character(0),
  season = integer(0),
  week = integer(0),
  projected_points = numeric(0),
  site_id = character(0),
  site_weight = numeric(0),
  generated_at = as.character(Sys.time())
)

dt <- format(Sys.time(), "%Y-%m-%d")
dir.create(file.path(opt$out_dir, paste0("dt=", dt)), recursive = TRUE, showWarnings = FALSE)
out_parquet <- file.path(opt$out_dir, paste0("dt=", dt), paste0("projections_", dt, ".parquet"))
arrow::write_parquet(df, out_parquet)

meta <- list(
  dataset = "ffanalytics_projections",
  asof_datetime = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz="UTC"),
  loader_path = "r:ffanalytics",
  source_name = "ffanalytics",
  source_version = "pinned via renv",
  output_parquet = out_parquet
)
writeLines(jsonlite::toJSON(meta, auto_unbox = TRUE, pretty = TRUE), file.path(opt$out_dir, paste0("dt=", dt), "_meta.json"))
cat(jsonlite::toJSON(meta, auto_unbox = TRUE), "\n")
