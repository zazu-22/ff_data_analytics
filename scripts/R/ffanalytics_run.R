# scripts/R/ffanalytics_run.R
# FFanalytics projections scraper with weighted consensus aggregation
# Outputs both raw source projections AND weighted consensus
# Maps player names to canonical mfl_id via dim_player_id_xref seed

suppressPackageStartupMessages({
  library(optparse)
  library(ffanalytics)
  library(arrow)
  library(jsonlite)
  library(dplyr)
  library(tidyr)
  library(stringr)
})

option_list <- list(
  make_option(c("--sources"), type="character",
              default="CBS,ESPN,FantasyData,FantasyPros,FantasySharks,FFToday,FleaFlicker,NumberFire,FantasyFootballNerd,NFL,RTSports,Walterfootball",
              help="Comma-separated list of sources (or 'all' for all available)"),
  make_option(c("--positions"), type="character", default="QB,RB,WR,TE,K,DST,DL,LB,DB",
              help="Comma-separated list of positions (all 9: QB,RB,WR,TE,K,DST,DL,LB,DB)"),
  make_option(c("--season"), type="integer", default=2024,
              help="Season year"),
  make_option(c("--week"), type="integer", default=0,
              help="Week number (0 for season-long)"),
  make_option(c("--out_dir"), type="character", default="data/raw/ffanalytics",
              help="Output directory"),
  make_option(c("--weights_csv"), type="character",
              default="config/projections/ffanalytics_projection_weights_mapped.csv",
              help="Path to site weights CSV"),
  make_option(c("--player_xref"), type="character",
              default="dbt/ff_analytics/seeds/dim_player_id_xref.csv",
              help="Path to player ID crosswalk seed")
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

# ============================================================
# WEIGHTED CONSENSUS AGGREGATION
# ============================================================

consensus_df <- data.frame()
mapping_stats <- list()

if(nrow(df) > 0) {
  cat("\n--- Weighted Consensus Aggregation ---\n")

  # Load site weights: ffanalytics research-backed defaults + optional custom overrides
  # ffanalytics default_weights (from package source - v1.5.0)
  # These are based on historical accuracy analysis
  default_wts <- c(
    CBS = 0.344,
    Yahoo = 0.400,
    ESPN = 0.329,
    NFL = 0.329,
    FFToday = 0.379,
    NumberFire = 0.322,
    FantasyPros = 0.000,  # Excluded by ffanalytics (consensus aggregator)
    FantasySharks = 0.327,
    FantasyFootballNerd = 0.000,  # Excluded by ffanalytics
    Walterfootball = 0.281,
    RTSports = 0.330,
    FantasyData = 0.428,
    Fleaflicker = 0.428
  )

  weights <- data.frame(
    site_id = names(default_wts),
    weight = as.numeric(default_wts),
    stringsAsFactors = FALSE
  )
  weights$site_id_lower <- tolower(weights$site_id)
  cat(sprintf("Using ffanalytics default_weights (%d sources)\n", nrow(weights)))

  # Load custom overrides if available
  custom_weights <- tryCatch({
    cw <- read.csv(opt$weights_csv, stringsAsFactors = FALSE)
    cw$site_id_lower <- tolower(cw$site_id)
    cat(sprintf("Loaded custom weight overrides from %s (%d sources)\n", opt$weights_csv, nrow(cw)))
    cw
  }, error = function(e) {
    NULL  # No custom weights available
  })

  # Apply custom overrides where specified
  if(!is.null(custom_weights)) {
    if(nrow(weights) > 0) {
      # We have defaults - merge custom as overrides
      weights <- weights %>%
        left_join(custom_weights %>% select(site_id_lower, custom_weight = weight),
                  by = "site_id_lower") %>%
        mutate(
          weight_original = weight,  # Keep original for logging
          weight = coalesce(custom_weight, weight)
        ) %>%
        select(site_id, site_id_lower, weight, weight_original)

      # Log which sources have custom overrides
      overridden <- weights %>%
        filter(weight != weight_original)

      if(nrow(overridden) > 0) {
        cat(sprintf("  Custom overrides applied to: %s\n",
                    paste(overridden$site_id, collapse=", ")))
      }

      weights <- weights %>% select(-weight_original)
    } else {
      # No defaults - use custom weights as primary
      weights <- custom_weights %>% select(site_id, site_id_lower, weight)
    }
  }

  cat(sprintf("Final weight configuration: %d sources\n", nrow(weights)))

  # Fallback for any successful sources without weights: equal weight
  if(nrow(weights) == 0) {
    cat("No weights configured - using equal weights for all successful sources\n")
    weights <- data.frame(
      site_id = successful_sources,
      weight = rep(1.0 / length(successful_sources), length(successful_sources)),
      stringsAsFactors = FALSE
    )
    weights$site_id_lower <- tolower(weights$site_id)
  }

  # Normalize df source names for matching (weights already normalized above)
  df$data_src_lower <- tolower(df$data_src)

  # Join weights to projections
  df_weighted <- df %>%
    left_join(weights %>% select(site_id_lower, weight),
              by = c("data_src_lower" = "site_id_lower")) %>%
    mutate(weight = ifelse(is.na(weight), 0, weight))  # Fallback for truly unknown sources

  # Warn if any sources have zero weight
  zero_weight_sources <- df_weighted %>%
    filter(weight == 0) %>%
    pull(data_src) %>%
    unique()

  if(length(zero_weight_sources) > 0) {
    cat(sprintf("  WARNING: %d sources have zero weight and will be excluded: %s\n",
                length(zero_weight_sources), paste(zero_weight_sources, collapse=", ")))
  }

  # Identify stat columns (numeric columns excluding metadata)
  metadata_cols <- c("player", "pos", "team", "data_src", "season", "week",
                     "data_src_lower", "weight")
  stat_cols <- setdiff(names(df_weighted)[sapply(df_weighted, is.numeric)],
                       c("season", "week", "weight"))

  cat(sprintf("Found %d stat columns to aggregate\n", length(stat_cols)))

  # Calculate weighted consensus per player per stat
  consensus_df <- df_weighted %>%
    filter(weight > 0) %>%  # Only use sources with weights
    group_by(player, pos, team, season, week) %>%
    summarise(
      across(all_of(stat_cols),
             ~ if(all(is.na(.))) NA_real_ else weighted.mean(., w = weight, na.rm = TRUE)),
      source_count = n(),
      total_weight = sum(weight),
      .groups = "drop"
    ) %>%
    mutate(
      provider = "ffanalytics_consensus",
      asof_date = as.character(Sys.Date())
    )

  cat(sprintf("Consensus projections: %d players\n", nrow(consensus_df)))

  # ============================================================
  # PLAYER NAME MAPPING TO CANONICAL MFL_ID
  # ============================================================

  cat("\n--- Player Name Mapping ---\n")

  # Load player ID crosswalk
  player_xref <- tryCatch({
    read.csv(opt$player_xref, stringsAsFactors = FALSE)
  }, error = function(e) {
    cat(sprintf("Warning: Could not load player xref from %s\n", opt$player_xref))
    cat("Proceeding without player ID mapping.\n")
    NULL
  })

  if(!is.null(player_xref)) {
    # Create normalized name for matching
    consensus_df <- consensus_df %>%
      mutate(player_normalized = tolower(trimws(player)))

    player_xref <- player_xref %>%
      mutate(
        name_normalized = tolower(trimws(name)),
        merge_name_normalized = tolower(trimws(merge_name))
      )

    # Try exact match on name first
    xref_name_match <- player_xref %>%
      select(name_normalized, mfl_id, position) %>%
      rename(mfl_id_name = mfl_id, position_name = position)

    # Try merge_name as fallback
    xref_merge_match <- player_xref %>%
      filter(!duplicated(merge_name_normalized)) %>%
      select(merge_name_normalized, mfl_id, position) %>%
      rename(mfl_id_merge = mfl_id, position_merge = position)

    # Join both and coalesce
    consensus_df <- consensus_df %>%
      left_join(xref_name_match,
                by = c("player_normalized" = "name_normalized")) %>%
      left_join(xref_merge_match,
                by = c("player_normalized" = "merge_name_normalized")) %>%
      mutate(
        player_id = coalesce(mfl_id_name, mfl_id_merge),
        # Use xref position if available, otherwise keep original
        position_final = coalesce(position_name, position_merge, pos)
      ) %>%
      select(-c(mfl_id_name, mfl_id_merge, position_name, position_merge, player_normalized))

    # Mapping statistics
    mapped_count <- sum(!is.na(consensus_df$player_id))
    total_count <- nrow(consensus_df)
    mapping_coverage <- mapped_count / total_count

    mapping_stats <- list(
      total_players = total_count,
      mapped_players = mapped_count,
      unmapped_players = total_count - mapped_count,
      mapping_coverage = round(mapping_coverage, 4)
    )

    cat(sprintf("Mapped %d / %d players (%.1f%% coverage)\n",
                mapped_count, total_count, mapping_coverage * 100))

    # For unmapped players, use -1 as sentinel
    consensus_df <- consensus_df %>%
      mutate(player_id = ifelse(is.na(player_id), -1, player_id))
  } else {
    consensus_df$player_id <- -1
    mapping_stats <- list(total_players = nrow(consensus_df),
                          mapped_players = 0,
                          mapping_coverage = 0)
  }

  # ============================================================
  # HORIZON DETECTION
  # ============================================================

  consensus_df <- consensus_df %>%
    mutate(horizon = case_when(
      week == 0 ~ "full_season",
      week > 0 ~ "weekly",
      TRUE ~ "unknown"
    ))
}

# ============================================================
# SAVE OUTPUTS
# ============================================================

dt <- format(Sys.time(), "%Y-%m-%d")
out_path <- file.path(opt$out_dir, "projections", paste0("dt=", dt))
dir.create(out_path, recursive = TRUE, showWarnings = FALSE)

output_files <- list()

if(nrow(df) > 0) {
  # Save RAW projections (all sources separately)
  cat("\n--- Saving Outputs ---\n")
  raw_parquet <- file.path(out_path, paste0("projections_raw_", dt, ".parquet"))
  arrow::write_parquet(df, raw_parquet)
  cat(sprintf("Raw projections: %s (%d rows)\n", raw_parquet, nrow(df)))
  output_files$raw <- raw_parquet
}

if(nrow(consensus_df) > 0) {
  # Save CONSENSUS projections (weighted)
  consensus_parquet <- file.path(out_path, paste0("projections_consensus_", dt, ".parquet"))
  arrow::write_parquet(consensus_df, consensus_parquet)
  cat(sprintf("Consensus projections: %s (%d rows)\n", consensus_parquet, nrow(consensus_df)))
  output_files$consensus <- consensus_parquet
}

# Create metadata
meta <- list(
  dataset = "ffanalytics_projections",
  asof_datetime = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz="UTC"),
  sources_requested = sources,
  sources_successful = successful_sources,
  sources_failed = failed_sources,
  positions = positions,
  season = opt$season,
  week = opt$week,
  horizon = if(opt$week == 0) "full_season" else "weekly",
  raw_rows = nrow(df),
  consensus_rows = nrow(consensus_df),
  player_mapping = mapping_stats,
  weights_file = opt$weights_csv,
  player_xref_file = opt$player_xref,
  output_files = output_files
)

writeLines(jsonlite::toJSON(meta, auto_unbox = TRUE, pretty = TRUE),
           file.path(out_path, "_meta.json"))

# Output JSON for pipeline
cat("\n--- Pipeline Manifest ---\n")
cat(jsonlite::toJSON(meta, auto_unbox = TRUE), "\n")
