# GCS Lifecycle Policy Tutorial

## Basic Structure

A GCS lifecycle policy is a JSON file with this structure:

```json
{
  "lifecycle": {
    "rule": [
      // Array of rules, each executed independently
    ]
  }
}
```

## Each Rule Has Two Parts

1. **action**: What to do (SetStorageClass, Delete)
1. **condition**: When to do it (age, matchesPrefix, etc.)

## Example Rules Explained

### Rule 1: Move raw/ data to Nearline after 30 days

```json
{
  "action": {
    "type": "SetStorageClass",
    "storageClass": "NEARLINE"
  },
  "condition": {
    "age": 30,                    // Files older than 30 days
    "matchesPrefix": ["raw/"]     // Only files starting with "raw/"
  }
}
```

### Rule 2: Move raw/ data to Coldline after 180 days

```json
{
  "action": {
    "type": "SetStorageClass",
    "storageClass": "COLDLINE"
  },
  "condition": {
    "age": 180,
    "matchesPrefix": ["raw/"]
  }
}
```

### Rule 3: Delete old ops logs after 90 days

```json
{
  "action": {
    "type": "Delete"
  },
  "condition": {
    "age": 90,
    "matchesPrefix": ["ops/logs/"]
  }
}
```

## Key Points

- **Multiple rules can apply** to the same files (e.g., raw/ goes Standard → Nearline → Coldline)
- **matchesPrefix** is an array - you can specify multiple prefixes in one rule
- **age** is in days since object creation
- **Storage classes** in order of cost: STANDARD > NEARLINE > COLDLINE > ARCHIVE

## For FF Analytics

Based on the SPEC, you need:

1. **raw/** - Immutable snapshots, accessed rarely → good for cold storage
1. **mart/** - Analytics queries, accessed frequently → keep in Standard
1. **stage/** - Intermediate data → maybe Nearline after 30 days
1. **ops/** - Logs and metrics → delete old ones to save costs

## Complete Example for Your Project

```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 30, "matchesPrefix": ["raw/", "stage/"]}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 180, "matchesPrefix": ["raw/"]}
      },
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90, "matchesPrefix": ["ops/logs/"]}
      }
    ]
  }
}
```

This policy:

- Moves raw/ and stage/ to Nearline after 30 days
- Moves raw/ to Coldline after 180 days (further cost savings)
- Deletes old logs after 90 days
- Leaves mart/ in Standard (no rules = no changes)
