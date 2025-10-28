# Linting Configuration Consistency Checklist

## Problem

Pre-commit hooks run in **isolated environments** and may use different configuration than direct tool invocations, causing:

```bash
# Direct command passes
$ uv run ruff check file.py
All checks passed! ✅

# Pre-commit fails
$ git commit
ruff.............................Failed ❌
```

______________________________________________________________________

## Consistency Requirements

### ✅ Rule #1: Explicit Config References

**Every pre-commit hook MUST explicitly reference the config file:**

```yaml
# ❌ BAD: Implicit config discovery
- id: ruff
  args: ["--fix"]

# ✅ GOOD: Explicit config
- id: ruff
  args: ["--fix", "--config=pyproject.toml"]
```

### ✅ Rule #2: Pinned Dependencies

**Pin tool versions in pre-commit to match project dependencies:**

```yaml
# ❌ BAD: Unpinned, may drift
additional_dependencies: [ruff]

# ✅ GOOD: Pinned to match dev deps
additional_dependencies: [ruff==0.6.4]
```

### ✅ Rule #3: No Conflicting Hook Responsibilities

**When multiple hooks modify the same file type, use exclusions to prevent conflicts:**

```yaml
# ❌ BAD: Both hooks format notebooks
- id: pretty-format-json
  args: ["--autofix", "--no-sort-keys"]
  # Will reformat .ipynb files (which are JSON)

- id: nbstripout
  files: ^notebooks/.*\.ipynb$
  # Also reformats notebooks - CONFLICT!

# ✅ GOOD: Clear separation of responsibilities
- id: pretty-format-json
  args: ["--autofix", "--no-sort-keys"]
  exclude: \.ipynb$  # Let nbstripout handle notebooks

- id: nbstripout
  files: ^notebooks/.*\.ipynb$
  # Sole authority for notebook formatting
```

**Why?**

- Conflicting hooks create infinite loops where they undo each other
- Causes false failures even when file is correctly formatted
- Blocks commits unnecessarily

### ✅ Rule #4: Unified Ignore Rules

**Notebook-specific ignores must be in BOTH places:**

```toml
# pyproject.toml (for direct invocation)
[tool.ruff.lint.per-file-ignores]
"notebooks/**/*.ipynb" = ["E501", "F821"]
```

```yaml
# .pre-commit-config.yaml (for pre-commit)
- id: nbqa-ruff
  args:
    - "--extend-ignore=E501,F821"
```

**Why both?**

- `pyproject.toml`: Used by `uv run ruff check notebooks/`
- Pre-commit args: Used by `pre-commit run nbqa-ruff`
- They must match!

______________________________________________________________________

## Validation Commands

Run these **before committing configuration changes:**

```bash
# 1. Test direct invocation
uv run ruff check .
uv run ruff format --check .

# 2. Test pre-commit (all files)
uv run pre-commit run --all-files

# 3. Test specific hook
uv run pre-commit run ruff --all-files
uv run pre-commit run nbqa-ruff --all-files

# 4. Validate config syntax
uv run pre-commit validate-config

# 5. Check for version mismatches
uv run pre-commit run --hook-stage manual --all-files
```

**Expected:** All commands should have identical results (pass or same errors).

______________________________________________________________________

## Common Tools Requiring Consistency

| Tool                   | Config File      | Pre-commit Arg            | Note                            |
| ---------------------- | ---------------- | ------------------------- | ------------------------------- |
| **ruff**               | `pyproject.toml` | `--config=pyproject.toml` | Most critical                   |
| **nbqa-ruff**          | `pyproject.toml` | `--config=pyproject.toml` | + `--extend-ignore`             |
| **sqlfluff**           | `pyproject.toml` | `--config=pyproject.toml` | Already correct                 |
| **mypy**               | `pyproject.toml` | Auto-detected             | Usually OK                      |
| **yamllint**           | `pyproject.toml` | Auto-detected             | Usually OK                      |
| **mdformat**           | `pyproject.toml` | Auto-detected             | Usually OK                      |
| **pretty-format-json** | Built-in         | `--no-sort-keys`          | Exclude `.ipynb$`               |
| **nbstripout**         | Built-in         | N/A                       | Must be only notebook formatter |

______________________________________________________________________

## When Adding New Tools

**Checklist for adding a new linting tool:**

- [ ] Add tool to `[dependency-groups] dev` in `pyproject.toml`
- [ ] Add configuration to `pyproject.toml` under `[tool.toolname]`
- [ ] Add pre-commit hook with:
  - [ ] Pinned version matching dev deps
  - [ ] Explicit `--config=pyproject.toml` arg
  - [ ] Correct `files:` pattern
- [ ] Test both direct invocation AND pre-commit
- [ ] Add to Makefile targets (`lintcheck`, `lintfix`, etc.)
- [ ] Document in this file

______________________________________________________________________

## Troubleshooting

### Symptom: Hook fails repeatedly claiming "files were modified" but no changes visible

**Diagnosis:**

```bash
# Run hooks individually to isolate conflict
uv run pre-commit run pretty-format-json --files file.ipynb
git diff file.ipynb  # Check what changed

uv run pre-commit run nbstripout --files file.ipynb
git diff file.ipynb  # Check if it reverted changes
```

**Common causes:**

1. ❌ Multiple hooks formatting the same file type
2. ❌ Hooks using different indentation/formatting preferences
3. ❌ No `exclude:` pattern to separate responsibilities

**Fix:** Add exclusions to prevent overlap:

```yaml
- id: pretty-format-json
  exclude: \.ipynb$  # Don't format notebooks

- id: nbstripout
  files: ^notebooks/.*\.ipynb$  # Handle notebooks only
```

______________________________________________________________________

### Symptom: Pre-commit fails but direct command passes

**Diagnosis:**

```bash
# Run both and compare
uv run ruff check file.py
uv run pre-commit run ruff --files file.py --verbose
```

**Common causes:**

1. ❌ No `--config=pyproject.toml` in pre-commit args
2. ❌ Version mismatch (pre-commit using newer/older version)
3. ❌ Different ignore rules in pre-commit vs pyproject.toml
4. ❌ Working directory different (use absolute paths)

**Fix:** Add explicit config and pin versions.

______________________________________________________________________

### Symptom: Both pass locally, CI fails

**Diagnosis:**

```bash
# Recreate pre-commit environment
uv run pre-commit clean
uv run pre-commit run --all-files
```

**Common causes:**

1. ❌ CI using different Python version
2. ❌ CI cache stale (old tool versions)
3. ❌ Missing config files in CI (`.gitignore`d?)
4. ❌ Different environment variables

**Fix:** Check CI configuration matches local dev setup.

______________________________________________________________________

## References

- [Pre-commit configuration docs](https://pre-commit.com/#pre-commit-configyaml---hooks)
- [Ruff configuration](https://docs.astral.sh/ruff/configuration/)
- [nbQA documentation](https://nbqa.readthedocs.io/)
