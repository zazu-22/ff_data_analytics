# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for the Fantasy Football Analytics project.

## Index

| ADR                                                               | Title                                           | Status     | Date    |
| ----------------------------------------------------------------- | ----------------------------------------------- | ---------- | ------- |
| [ADR-001](../../docs/spec/SPEC-1_v_2.2.md#adrs-examples)          | Canonical stat dictionary                       | Accepted\* | -       |
| [ADR-002](../../docs/spec/SPEC-1_v_2.2.md#adrs-examples)          | Twice-daily cron schedule                       | Accepted\* | -       |
| [ADR-003](../../docs/spec/SPEC-1_v_2.2.md#adrs-examples)          | Versioning strategy for breaking changes        | Accepted\* | -       |
| [ADR-004](ADR-004-github-actions-for-sheets.md)                   | GitHub Actions for Sheets access                | Accepted   | 2024-09 |
| [ADR-005](ADR-005-commissioner-sheet-ingestion-strategy.md)       | Commissioner Sheet ingestion strategy           | Accepted   | 2024-09 |
| [ADR-006](ADR-006-gcs-integration-strategy.md)                    | GCS integration strategy                        | Accepted   | 2024-09 |
| [ADR-007](ADR-007-separate-fact-tables-actuals-vs-projections.md) | Separate fact tables for actuals vs projections | Accepted   | 2025-09 |
| [ADR-008](ADR-008-league-transaction-history-integration.md)      | League transaction history integration          | Accepted   | 2025-09 |

\*Note: ADRs 001-003 are documented in the main specification as examples and will be formalized as separate documents when implementation decisions are finalized.

## ADR Format

Each ADR follows this structure:

- **Status**: Draft | Accepted | Superseded | Deprecated
- **Context**: The issue or decision that needs to be made
- **Decision**: The chosen approach
- **Consequences**: Positive and negative impacts
- **References**: Related documents and resources

## Creating New ADRs

1. Copy an existing ADR as a template
1. Number sequentially (ADR-007, ADR-008, etc.)
1. Update this index
1. Reference in SPEC-1 if architecturally significant
