# scripts/R/nflverse_load.R
# Fallback runner for nflverse datasets using nflreadr
# Usage:
#   Rscript scripts/R/nflverse_load.R --dataset players --seasons 2020,2021 --out_dir gs://ff-analytics/raw/nflverse

suppressPackageStartupMessages({
  library(jsonlite)
  library(optparse)
  library(arrow)        # for write_parquet
  library(lubridate)
  library(nflreadr)
})

option_list <- list(
  make_option(c("--dataset"), type="character", help="Dataset key (players, weekly, season, injuries, depth_charts, schedule, teams)"),
  make_option(c("--seasons"), type="character", default=NULL, help="Comma-separated seasons"),
  make_option(c("--weeks"), type="character", default=NULL, help="Comma-separated weeks"),
  make_option(c("--out_dir"), type="character", default="gs://ff-analytics/raw/nflverse", help="Output root")
)
opt <- parse_args(OptionParser(option_list=option_list))

if (is.null(opt$dataset)) {
  stop("Missing --dataset")
}

seasons <- if (!is.null(opt$seasons)) as.integer(unlist(strsplit(opt$seasons, ","))) else NULL
weeks   <- if (!is.null(opt$weeks))   as.integer(unlist(strsplit(opt$weeks, ",")))   else NULL

dataset <- opt$dataset

# Helper to write parquet with meta
write_with_meta <- function(df, dataset, out_dir) {
  dt <- format(Sys.time(), "%Y-%m-%d")
  dir.create(file.path(out_dir, dataset, paste0("dt=", dt)), recursive = TRUE, showWarnings = FALSE)
  parquet_file <- file.path(out_dir, dataset, paste0("dt=", dt), paste0(dataset, "_", substr(digest::digest(Sys.time()), 1, 8), ".parquet"))
  arrow::write_parquet(df, parquet_file)
  meta <- list(
    dataset = dataset,
    asof_datetime = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz="UTC"),
    loader_path = "r:nflreadr",
    source_name = "nflverse",
    source_version = as.character(utils::packageVersion("nflreadr")),
    output_parquet = parquet_file
  )
  writeLines(jsonlite::toJSON(meta, auto_unbox = TRUE, pretty = TRUE), file.path(out_dir, dataset, paste0("dt=", dt), "_meta.json"))
  return(meta)
}

df <- NULL
if (dataset == "players") {
  df <- nflreadr::load_players()
} else if (dataset == "weekly") {
  df <- nflreadr::load_player_stats(seasons = seasons, stat_type = "week")
  if (!is.null(weeks)) df <- df[df$week %in% weeks, ]
} else if (dataset == "season") {
  df <- nflreadr::load_player_stats(seasons = seasons, stat_type = "season")
} else if (dataset == "injuries") {
  df <- nflreadr::load_injuries(seasons = seasons)
} else if (dataset == "depth_charts") {
  df <- nflreadr::load_depth_charts(seasons = seasons, weeks = weeks)
} else if (dataset == "schedule") {
  df <- nflreadr::load_schedules(seasons = seasons)
} else if (dataset == "teams") {
  df <- nflreadr::load_teams()
} else {
  stop(paste("Unknown dataset:", dataset))
}

meta <- write_with_meta(df, dataset, opt$out_dir)

# Print JSON manifest (single line) to stdout for the Python shim to parse if desired
cat(jsonlite::toJSON(meta, auto_unbox = TRUE), "\n")
