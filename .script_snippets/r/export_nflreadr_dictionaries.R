#!/usr/bin/env Rscript
# export_nflreadr_dictionaries.R
# Purpose: Export all nflreadr package data dictionaries (objects named ^dictionary_*) to CSV and JSON.
#          Additionally: create a single combined JSON (all dictionaries) and a single Parquet
#          in a "long-form" keyed by dictionary name, plus a schema Parquet.
#
# Usage:
#   From R GUI: source("export_nflreadr_dictionaries.R")
#   From terminal:
#     Rscript export_nflreadr_dictionaries.R --outdir ./nflreadr_dictionaries --format both
#
# Options:
#   --outdir <path>   Output folder (default: "./nflreadr_dictionaries")
#   --format <csv|json|both>  Which per-dictionary formats to write (default: "both")
#
# Notes:
# - Only objects that are data.frames/tibbles are exported by default.
# - Set EXPORT_MAPPINGS=1 environment variable to also export named vectors (e.g., team_abbr_mapping) as two-column CSV/JSON.
# - New (combined outputs):
#     * combined/dictionaries.json:  {"dictionary_name": [ {...row1}, {...row2}, ...], ...}
#     * combined/dictionaries_long.parquet: long-form table with columns
#           [dictionary, row, column, value]
#       (value stored as string for cross-dictionary compatibility)
#     * combined/dictionary_schema.parquet: schema table with columns
#           [dictionary, column, type]
#
suppressPackageStartupMessages({
  if (!requireNamespace("optparse", quietly = TRUE)) install.packages("optparse", repos="https://cloud.r-project.org")
  if (!requireNamespace("jsonlite", quietly = TRUE)) install.packages("jsonlite", repos="https://cloud.r-project.org")
  if (!requireNamespace("nflreadr", quietly = TRUE)) install.packages("nflreadr", repos="https://cloud.r-project.org")
  if (!requireNamespace("arrow", quietly = TRUE)) install.packages("arrow", repos="https://cloud.r-project.org")
})

library(optparse)
library(jsonlite)
library(nflreadr)
library(arrow)

option_list <- list(
  make_option(c("--outdir"), type="character", default="./nflreadr_dictionaries",
              help="Output directory [default: %default]"),
  make_option(c("--format"), type="character", default="both",
              help="csv, json, or both [default: %default]")
)
opt <- parse_args(OptionParser(option_list=option_list))

outdir <- opt$outdir
fmt <- tolower(opt$format)
if (!fmt %in% c("csv","json","both")) stop("Invalid --format. Use csv, json, or both.")

if (!dir.exists(outdir)) dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

# subfolder for combined outputs
combined_dir <- file.path(outdir, "combined")
if (!dir.exists(combined_dir)) dir.create(combined_dir, recursive = TRUE, showWarnings = FALSE)

# Discover dictionary objects programmatically (most robust)
dict_names <- ls("package:nflreadr", pattern = "^dictionary_")

# Helper: write a single data.frame to disk
write_df <- function(df, name) {
  if (fmt %in% c("csv","both")) {
    write.csv(df, file = file.path(outdir, paste0(name, ".csv")), row.names = FALSE, na = "")
  }
  if (fmt %in% c("json","both")) {
    # dataframe="rows" yields an array of objects [{...}, {...}]
    write_json(df, path = file.path(outdir, paste0(name, ".json")), dataframe = "rows", na = "null", pretty = TRUE, auto_unbox = TRUE)
  }
}

# Export loop; also build combined structures
exported <- character(0)
skipped <- character(0)
combined_list <- list()          # for combined JSON
schema_rows <- list()            # for schema parquet
long_rows_part <- list()         # for long-form parquet

for (nm in dict_names) {
  obj <- get(nm, asNamespace("nflreadr"))
  if (inherits(obj, "data.frame")) {
    df <- as.data.frame(obj, stringsAsFactors = FALSE)
    # per-dictionary exports
    write_df(df, nm)
    exported <- c(exported, nm)
    # combined JSON
    combined_list[[nm]] <- df
    # schema rows
    col_types <- vapply(df, function(x) paste(class(x), collapse="|"), character(1))
    schema_rows[[length(schema_rows)+1]] <- data.frame(
      dictionary = nm,
      column = names(df),
      type = unname(col_types),
      stringsAsFactors = FALSE
    )
    # long-form rows: dictionary, row, column, value (as character)
    if (nrow(df) > 0 && ncol(df) > 0) {
      # build with vectorization
      row_idx <- rep(seq_len(nrow(df)), times = ncol(df))
      col_rep <- rep(names(df), each = nrow(df))
      # coerce each column to character then unlist
      values <- unlist(lapply(df, function(col) {
        if (is.list(col)) {
          # serialize lists/nested to JSON for stable representation
          vapply(col, function(x) jsonlite::toJSON(x, auto_unbox=TRUE, null="null"), character(1))
        } else {
          as.character(col)
        }
      }), use.names = FALSE)
      long_rows_part[[length(long_rows_part)+1]] <- data.frame(
        dictionary = nm,
        row = row_idx,
        column = col_rep,
        value = values,
        stringsAsFactors = FALSE
      )
    } else {
      # even empty data frames should be represented in schema, which we already did
      invisible(NULL)
    }
  } else {
    # Optionally export named vectors (e.g., mappings) if user sets ENV var
    if (!is.null(Sys.getenv("EXPORT_MAPPINGS")) && nzchar(Sys.getenv("EXPORT_MAPPINGS")) && is.atomic(obj) && !is.null(names(obj))) {
      df <- data.frame(name = names(obj), value = unname(obj), stringsAsFactors = FALSE)
      write_df(df, nm)
      exported <- c(exported, nm)
      # include in combined JSON
      combined_list[[nm]] <- df
      # schema
      schema_rows[[length(schema_rows)+1]] <- data.frame(
        dictionary = nm,
        column = names(df),
        type = vapply(df, function(x) paste(class(x), collapse="|"), character(1)),
        stringsAsFactors = FALSE
      )
      # long-form
      if (nrow(df) > 0) {
        row_idx <- rep(seq_len(nrow(df)), times = ncol(df))
        col_rep <- rep(names(df), each = nrow(df))
        values <- unlist(lapply(df, function(col) as.character(col)), use.names = FALSE)
        long_rows_part[[length(long_rows_part)+1]] <- data.frame(
          dictionary = nm, row = row_idx, column = col_rep, value = values, stringsAsFactors = FALSE
        )
      }
    } else {
      skipped <- c(skipped, nm)
    }
  }
}

# Create an index.csv/json with basic metadata and reference URL for each exported dictionary
index <- data.frame(
  dictionary = exported,
  rows = vapply(exported, function(nm) nrow(get(nm, asNamespace("nflreadr"))), integer(1)),
  cols = vapply(exported, function(nm) ncol(get(nm, asNamespace("nflreadr"))), integer(1)),
  reference_url = sprintf("https://nflreadr.nflverse.com/reference/%s.html", exported),
  stringsAsFactors = FALSE
)
write_df(index, "dictionary_index")

# Combined JSON (all dictionaries -> one JSON file)
# Note: write_json handles lists-of-data.frames; use dataframe="rows" for row-wise records.
combined_json_path <- file.path(combined_dir, "dictionaries.json")
write_json(combined_list, path = combined_json_path, dataframe = "rows", na = "null", pretty = TRUE, auto_unbox = TRUE)

# Schema parquet
schema_df <- if (length(schema_rows)) do.call(rbind, schema_rows) else data.frame(dictionary=character(), column=character(), type=character(), stringsAsFactors = FALSE)
write_parquet(schema_df, sink = file.path(combined_dir, "dictionary_schema.parquet"))

# Long-form parquet (dictionary, row, column, value)
long_df <- if (length(long_rows_part)) do.call(rbind, long_rows_part) else data.frame(dictionary=character(), row=integer(), column=character(), value=character(), stringsAsFactors = FALSE)
write_parquet(long_df, sink = file.path(combined_dir, "dictionaries_long.parquet"))

# Also write a README to the output folder
readme_path <- file.path(outdir, "README.txt")
cat(
  "nflreadr Data Dictionary Export\n",
  "================================\n\n",
  "This folder contains CSV/JSON exports of data dictionary objects from the nflreadr R package,\n",
  "plus combined outputs in ./combined/.\n",
  "Files were generated by export_nflreadr_dictionaries.R on ", as.character(Sys.time()), "\n\n",
  "How to update:\n",
  "  Rscript export_nflreadr_dictionaries.R --outdir ./nflreadr_dictionaries --format both\n\n",
  "Combined outputs:\n",
  "  - combined/dictionaries.json            (map: name -> array of rows)\n",
  "  - combined/dictionaries_long.parquet    (columns: dictionary, row, column, value)\n",
  "  - combined/dictionary_schema.parquet    (columns: dictionary, column, type)\n\n",
  "Notes:\n",
  "  - Only objects whose names begin with 'dictionary_' are exported by default.\n",
  "  - Non-data.frame objects (e.g., named vectors) are skipped by default.\n",
  "    To export those as two-column tables, set: EXPORT_MAPPINGS=1\n",
  "  - See dictionary_index.csv/json for a list of exported items and doc links.\n",
  file = readme_path, sep = ""
)

message(sprintf("Done. Exported %d dictionaries to: %s", length(exported), normalizePath(outdir)))
if (length(skipped)) message(sprintf("Skipped (non-data.frame): %s", paste(skipped, collapse = ", ")))
