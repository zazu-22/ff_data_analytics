# scripts/R/ffanalytics_run.R
# Simple runner to get raw projections from FFanalytics sources
# Just saves the raw projection data - no calculations or aggregations

suppressPackageStartupMessages({
  library(optparse)
  library(ffanalytics)
  library(arrow)
  library(jsonlite)
  library(dplyr)
})

option_list <- list(
  make_option(c("--sources"), type="character",
              default="CBS,ESPN,FantasyData,FantasyPros,FantasySharks,FFToday,FleaFlicker,NumberFire,FantasyFootballNerd,NFL,RTSports,Walterfootball",
              help="Comma-separated list of sources (or 'all' for all available)"),
  make_option(c("--positions"), type="character", default="QB,RB,WR,TE,K,DST",
              help="Comma-separated list of positions"),
  make_option(c("--season"), type="integer", default=2024,
              help="Season year"),
  make_option(c("--week"), type="integer", default=0,
              help="Week number (0 for season-long)"),
  make_option(c("--out_dir"), type="character", default="data/raw/ffanalytics",
              help="Output directory")
)
opt <- parse_args(OptionParser(option_list=option_list))

# Parse comma-separated inputs
if(opt$sources == "all") {
  # Get all available sources
  data('projection_sources', package = 'ffanalytics')
  sources <- names(projection_sources)
} else {
  sources <- trimws(strsplit(opt$sources, ",")[[1]])
}
positions <- trimws(strsplit(opt$positions, ",")[[1]])

cat("FFanalytics Raw Projections Scraper\n")
cat(sprintf("Season: %d, Week: %d\n", opt$season, opt$week))
cat(sprintf("Positions: %s\n", paste(positions, collapse=", ")))
cat(sprintf("Attempting %d sources...\n", length(sources)))

# Try each source individually to handle failures gracefully
cat("\nScraping projections from each source:\n")
all_scrapes <- list()
successful_sources <- c()
failed_sources <- c()

for(src in sources) {
  cat(sprintf("  Trying %s... ", src))
  src_scrape <- tryCatch({
    ffanalytics::scrape_data(
      src = src,
      pos = positions,
      season = opt$season,
      week = opt$week
    )
  }, error = function(e) {
    # Just return NULL on error, don't stop
    NULL
  })

  if(!is.null(src_scrape) && length(src_scrape) > 0) {
    # Check if we got actual data
    has_data <- FALSE
    for(p in names(src_scrape)) {
      if(nrow(src_scrape[[p]]) > 0) {
        has_data <- TRUE
        break
      }
    }

    if(has_data) {
      all_scrapes[[src]] <- src_scrape
      successful_sources <- c(successful_sources, src)
      cat("SUCCESS\n")
    } else {
      failed_sources <- c(failed_sources, src)
      cat("NO DATA\n")
    }
  } else {
    failed_sources <- c(failed_sources, src)
    cat("FAILED\n")
  }
}

cat(sprintf("\nSuccessful sources: %d\n", length(successful_sources)))
if(length(successful_sources) > 0) {
  cat(paste("  -", successful_sources, "\n"))
}
cat(sprintf("Failed sources: %d\n", length(failed_sources)))

# Combine all successful scrapes
my_scrape <- NULL
if(length(all_scrapes) > 0) {
  # Merge scrapes from all sources by position
  combined_by_pos <- list()

  for(src_name in names(all_scrapes)) {
    src_data <- all_scrapes[[src_name]]
    for(pos in names(src_data)) {
      if(!(pos %in% names(combined_by_pos))) {
        combined_by_pos[[pos]] <- list()
      }
      if(nrow(src_data[[pos]]) > 0) {
        combined_by_pos[[pos]] <- append(combined_by_pos[[pos]], list(src_data[[pos]]))
      }
    }
  }

  # Bind all data for each position
  my_scrape <- list()
  for(pos in names(combined_by_pos)) {
    if(length(combined_by_pos[[pos]]) > 0) {
      my_scrape[[pos]] <- bind_rows(combined_by_pos[[pos]])
    }
  }
}

if(is.null(my_scrape)) {
  cat("Scraping failed. Creating empty output.\n")
  df <- data.frame()
} else {
  # Combine all positions into one dataframe
  df_list <- list()
  for(pos in names(my_scrape)) {
    pos_data <- my_scrape[[pos]]
    if(nrow(pos_data) > 0) {
      # Add season and week columns
      pos_data$season <- opt$season
      pos_data$week <- opt$week
      df_list[[pos]] <- pos_data
      cat(sprintf("  %s: %d players from %d sources\n",
                  pos,
                  n_distinct(pos_data$player),
                  n_distinct(pos_data$data_src)))
    }
  }

  # Combine all positions
  df <- bind_rows(df_list)
  cat(sprintf("\nTotal: %d projection records\n", nrow(df)))
}

# Save to parquet with date partitioning
dt <- format(Sys.time(), "%Y-%m-%d")
out_path <- file.path(opt$out_dir, paste0("dt=", dt))
dir.create(out_path, recursive = TRUE, showWarnings = FALSE)

if(nrow(df) > 0) {
  # Save the raw projections
  out_parquet <- file.path(out_path, paste0("projections_raw_", dt, ".parquet"))
  arrow::write_parquet(df, out_parquet)

  # Create metadata
  meta <- list(
    dataset = "ffanalytics_projections_raw",
    asof_datetime = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz="UTC"),
    sources = sources,
    positions = positions,
    season = opt$season,
    week = opt$week,
    rows = nrow(df),
    players = n_distinct(df$player),
    output_parquet = out_parquet
  )

  writeLines(jsonlite::toJSON(meta, auto_unbox = TRUE, pretty = TRUE),
             file.path(out_path, "_meta.json"))

  # Output JSON for pipeline
  cat(jsonlite::toJSON(meta, auto_unbox = TRUE), "\n")
} else {
  cat("No data to save.\n")
}
