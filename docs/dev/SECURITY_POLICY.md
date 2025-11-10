# Security Policy & Guidelines

## Overview

This document outlines security practices for the ff-analytics project, covering credential management, secret handling, and CI/CD security.

______________________________________________________________________

## 1. Credential Management

### Golden Rules

1. **Never commit secrets to git** (API keys, passwords, tokens)
2. **Use GitHub Secrets** for sensitive values in CI/CD
3. **Use .env locally** (in .gitignore) for development
4. **Rotate credentials periodically** (90-day minimum)
5. **Audit credential usage** in logs and access patterns

### GitHub Secrets Setup

**Who can set**: Repository admins via Settings → Secrets and variables

**Required Secrets**:

```yaml
GOOGLE_APPLICATION_CREDENTIALS_JSON: # GCP service account key (base64)
GCP_PROJECT_ID: # GCP project ID
GCS_BUCKET: # GCS bucket name
COMMISSIONER_SHEET_ID: # Google Sheets ID
LEAGUE_SHEET_COPY_ID: # Google Sheets ID
DISCORD_WEBHOOK_URL: # Discord notification webhook
```

**Environment-Specific Secrets**:

```yaml
# Staging environment (Settings → Environments → staging → Secrets)
GCP_PROJECT_ID_STAGING: # Staging GCP project (optional)

# Production environment (Settings → Environments → production → Secrets)
GCP_PROJECT_ID_PROD: # Production GCP project (optional, same as main if only one)
```

### Local Development (.env)

**File**: `.env` (never commit)

```bash
# Copy template
cp .env.example .env

# Fill in your values
nano .env

# Load automatically via direnv
# (configured in .envrc)
source .env
```

### Credential Rotation Schedule

| Credential              | Rotation Period | Owner       | Notes                                  |
| ----------------------- | --------------- | ----------- | -------------------------------------- |
| GCP Service Account Key | 90 days         | DevOps Lead | Generate new key, update GitHub Secret |
| Discord Webhook URL     | 120 days        | Ops Team    | Regenerate in Discord server settings  |
| Google Sheets API Key   | 90 days         | DevOps Lead | Regenerate in GCP Console              |

**Rotation Process**:

```bash
# 1. Generate new credential (via GCP/Discord/Google Sheets)
# 2. Update GitHub Secret
gh secret set CREDENTIAL_NAME --body "new_value"

# 3. Verify new value works
# 4. Document in security log
# 5. Delete old credential (if supported)
```

______________________________________________________________________

## 2. Secret Scanning

### Pre-commit Secret Detection

**Tools**: TruffleHog, GitLeaks (configured in pre-commit hooks)

**What gets checked**:

- API keys (pattern: `api[_-]?key`)
- Private keys (PEM, RSA, DSA formats)
- Credentials (AWS, GCP, Azure keys)
- Database passwords
- Tokens (JWT, Bearer tokens)

**If a secret is accidentally committed**:

```bash
# 1. IMMEDIATELY rotate the credential in the system
# 2. Remove from git history
git log --all --full-history -- path/to/file
git filter-branch --tree-filter 'rm path/to/file' -- --all

# 3. Force push (dangerous - coordinate with team)
git push --force-with-lease

# 4. Notify team of exposure
# 5. File incident report
```

### CI/CD Secret Scanning

**Workflow**: `.github/workflows/security-scan.yml` (Phase 1)

Runs on:

- Pull requests
- Pushes to main
- Weekly schedule (Sunday midnight)

**Actions if secrets detected**:

- Workflow fails (blocks merge)
- Artifact uploaded with report
- Team notified via Discord

______________________________________________________________________

## 3. Dependency Security

### Vulnerability Scanning

**Tools**:

- Safety (Python package vulnerabilities)
- pip-audit (dependency audit)
- Dependabot (GitHub automated alerts)

**Thresholds**:

| Severity | Action                          | Timeline     |
| -------- | ------------------------------- | ------------ |
| CRITICAL | Fail CI, immediate fix required | Same day     |
| HIGH     | Fail CI, must fix before merge  | 1 week       |
| MEDIUM   | Warning only, backlog item      | 2 weeks      |
| LOW      | Informational only              | Next release |

**Update Process**:

```bash
# Check for vulnerabilities
uv run safety check

# If vulnerabilities found:
# 1. Update to patched version
uv add --upgrade vulnerable_package

# 2. Run tests
uv run pytest tests/

# 3. Commit and PR
git add uv.lock pyproject.toml
git commit -m "security: update vulnerable dependency"
git push -u origin security/fix-<package>-<cve>
```

______________________________________________________________________

## 4. Code Security

### Static Analysis (SAST)

**Tools** (Phase 1):

- Bandit (Python security issues)
- Semgrep (pattern-based security checks)

**What gets checked**:

- SQL injection vulnerabilities
- Hardcoded credentials
- Insecure deserialization
- Path traversal issues
- Command injection risks

**Example Issues**:

```python
# ❌ BAD: Hardcoded credentials
API_KEY = "sk_live_abcd1234"

# ✅ GOOD: Use environment variable
import os
API_KEY = os.getenv("SPORTS_DATA_API_KEY")
if not API_KEY:
    raise ValueError("SPORTS_DATA_API_KEY not set")

# ❌ BAD: SQL injection risk
query = f"SELECT * FROM players WHERE name = '{user_input}'"

# ✅ GOOD: Use parameterized query
query = "SELECT * FROM players WHERE name = ?"
cursor.execute(query, (user_input,))
```

### Code Review Security Checklist

Before approving PRs:

- [ ] No hardcoded secrets or API keys
- [ ] External inputs validated
- [ ] SQL queries parameterized
- [ ] Permissions properly checked
- [ ] Error messages don't leak info
- [ ] No debug logging of sensitive data
- [ ] Dependencies up to date
- [ ] New external API calls documented

______________________________________________________________________

## 5. Infrastructure Security

### GCP Service Accounts

**Principle**: Least privilege access

**Service Account Configuration**:

```hcl
# Only grant necessary roles
resource "google_project_iam_member" "pipeline_storage" {
  project = var.gcp_project_id
  role    = "roles/storage.objectAdmin"  # Only for data bucket
  member  = "serviceAccount:${google_service_account.pipeline.email}"
}

# NOT:
# role = "roles/editor"  # Too broad!
# role = "roles/owner"   # Definitely not!
```

**Credential Rotation** (via Terraform):

```hcl
resource "google_service_account_key" "pipeline_key" {
  service_account_id = google_service_account.pipeline.name
  lifecycle {
    create_before_destroy = true
  }
}

# Rotate every 90 days:
# 1. terraform apply (creates new key)
# 2. Update GitHub Secret
# 3. terraform apply again (old key destroyed)
```

### GCS Bucket Security

**Recommended Configuration**:

```hcl
resource "google_storage_bucket" "data" {
  name = "ff-analytics"

  # Enforce uniform access control
  uniform_bucket_level_access = true

  # Require HTTPS
  force_ssl = true

  # Enable versioning for audit trail
  versioning {
    enabled = true
  }

  # Lifecycle policy for data retention
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}
```

**Access Control** (via .gitignore):

```bash
# Never commit credentials to bucket
echo "config/secrets/" >> .gitignore
echo ".env" >> .gitignore
```

______________________________________________________________________

## 6. API Security

### External API Integration

When adding new API integrations:

1. **Use environment variables for keys**:

   ```python
   from ingest.nflverse import NFLverseClient

   client = NFLverseClient(
       api_key=os.getenv("NFLVERSE_API_KEY")
   )
   ```

2. **Validate API responses**:

   ```python
   response = client.get_players()
   assert response.status_code == 200
   assert "players" in response.json()
   ```

3. **Handle errors gracefully**:

   ```python
   try:
       data = client.load_data()
   except APIRateLimitError:
       logger.warning("Rate limited, retrying...")
   except APIAuthError:
       raise ValueError("Invalid API key")
   ```

4. **Log securely** (no credentials):

   ```python
   # ❌ BAD
   logger.info(f"API call with key: {api_key}")

   # ✅ GOOD
   logger.info("API call successful")
   logger.debug(f"Endpoint: {endpoint}, Status: {response.status_code}")
   ```

______________________________________________________________________

## 7. Logging & Audit

### What to Log

**DO log**:

- API call success/failure (no credentials)
- Data ingestion timestamps
- dbt test results (pass/fail)
- Deployment events (who, when, what)
- Access attempts (for audit)

**DON'T log**:

- API keys or tokens
- User passwords
- Full request bodies (may contain secrets)
- Personal identifiable information
- Internal IP addresses

### Audit Trail

**Deployment manifest** (automatically created):

```json
{
  "environment": "production",
  "timestamp": "2025-11-10T14:30:00Z",
  "commit_sha": "abc1234",
  "deployed_by": "github-actions",
  "backup_location": "gs://ff-analytics/backups/2025-11-10-143000"
}
```

**Access logging** (GCS):

```bash
# View who accessed data
gsutil logging get gs://ff-analytics

# Set up Cloud Audit Logs
gcloud logging sinks create storage-audit \
  logging.googleapis.com/projects/ff-analytics-1/logs/cloudaudit.googleapis.com
```

______________________________________________________________________

## 8. Incident Response

### Security Incident Classification

| Severity     | Examples                          | Response Time | Actions                                               |
| ------------ | --------------------------------- | ------------- | ----------------------------------------------------- |
| **Critical** | Credential exposed, data breach   | 1 hour        | Rotate immediately, notify team, incident post-mortem |
| **High**     | Vulnerability found in dependency | 1 day         | Patch, test, deploy                                   |
| **Medium**   | Weak credential, poor logging     | 1 week        | Fix, document, prevent recurrence                     |
| **Low**      | Outdated best practice            | 2 weeks       | Backlog item                                          |

### Incident Report Template

**File**: `docs/incidents/INCIDENT-YYYY-MM-DD-{name}.md`

```markdown
# Incident Report: [Name]

## Timeline

- **Discovered**: YYYY-MM-DD HH:MM UTC by [person]
- **Impact Started**: [estimated timestamp]
- **Resolved**: [timestamp]
- **Duration**: X minutes/hours

## What Happened

[Detailed description of the incident]

## Root Cause

[What caused this to happen?]

## Impact

- Data affected: [which tables/timeframes]
- Systems down: [which services]
- Users affected: [estimate]

## Resolution

[How it was fixed]

## Preventive Actions

- [ ] Action 1 (owner: name, deadline: date)
- [ ] Action 2 (owner: name, deadline: date)

## Lessons Learned

[What we learned]

---

Reviewed by: [names]
Date: [date]
```

______________________________________________________________________

## 9. Third-Party Dependencies

### Approved Vendors

| Service               | Purpose               | Auth Method     | Owner        |
| --------------------- | --------------------- | --------------- | ------------ |
| Google Cloud Platform | Data storage, compute | Service account | DevOps       |
| Google Sheets API     | League configuration  | OAuth2          | Commissioner |
| Discord               | Notifications         | Webhook         | DevOps       |
| Sports Data IO        | NFL data              | API key         | Data team    |

### Dependency Updates

**Policy**:

- Security updates: Apply within 24 hours (if test-passing)
- Minor updates: Review monthly
- Major updates: Plan in sprint

**Process**:

```bash
# Check for updates
uv pip list --outdated

# Update safely
uv add --upgrade package_name

# Run tests
uv run pytest tests/
uv run mypy src/

# Commit
git add uv.lock pyproject.toml
git commit -m "deps: upgrade package_name to v1.2.3"
```

______________________________________________________________________

## 10. Security Checklist for New Features

Before committing new code:

- [ ] No hardcoded credentials
- [ ] External inputs validated
- [ ] API keys used from environment variables
- [ ] Error messages don't leak sensitive info
- [ ] Logging doesn't include secrets
- [ ] New dependencies vetted (no malware/unmaintained)
- [ ] Tests include security test cases
- [ ] Code review focused on security aspects
- [ ] Changes documented in CHANGELOG

______________________________________________________________________

## Reporting Security Issues

**DO NOT** create a public GitHub issue for security vulnerabilities.

**Instead**:

1. Email: [security-contact@example.com]
2. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)
3. Allow 24-48 hours for response before public disclosure

______________________________________________________________________

## Resources

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CWE Top 25**: https://cwe.mitre.org/top25/
- **Bandit**: https://bandit.readthedocs.io/
- **Semgrep**: https://semgrep.dev/docs/
- **GCP Security**: https://cloud.google.com/architecture/devops/devops-tech-secure-scm

______________________________________________________________________

## Contacts

- **Security Lead**: [name] ([email])
- **DevOps**: [name] ([email])
- **On-Call**: See on-call schedule in project README

______________________________________________________________________

**Last Updated**: 2025-11-10
**Review Frequency**: Quarterly
**Next Review Date**: 2026-02-10
