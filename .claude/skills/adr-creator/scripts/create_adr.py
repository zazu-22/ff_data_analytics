#!/usr/bin/env python3
"""Interactive ADR creation script.

Prompts for ADR details and creates a new ADR file from template.
"""

import re
from datetime import datetime
from pathlib import Path

from get_next_adr_number import get_next_adr_number


def slugify(text: str) -> str:
    """Convert text to kebab-case slug."""
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and underscores with hyphens
    text = re.sub(r"[\s_]+", "-", text)
    # Remove non-alphanumeric characters (except hyphens)
    text = re.sub(r"[^a-z0-9-]", "", text)
    # Remove duplicate hyphens
    text = re.sub(r"-+", "-", text)
    # Strip leading/trailing hyphens
    text = text.strip("-")
    return text


def read_template() -> str:
    """Read the ADR template file."""
    template_path = Path(__file__).parent.parent / "assets" / "adr_template.md"

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found at {template_path}")

    return template_path.read_text()


def prompt_user() -> dict:
    """Prompt user for ADR details."""
    print("=== Create New Architecture Decision Record ===\n")

    # Get title
    title = input("ADR Title (short, descriptive): ").strip()
    if not title:
        raise ValueError("Title is required")

    # Get deciders
    deciders = input("Decision Makers (e.g., 'Jason Shaffer, Dev Team'): ").strip()
    if not deciders:
        deciders = "Development Team"

    # Get status
    print("\nStatus options: Draft, Accepted, Superseded, Deprecated")
    status = input("Status [Draft]: ").strip() or "Draft"

    # Check if it supersedes another ADR
    supersedes = input("Supersedes ADR number (leave blank if N/A): ").strip()

    # Get context
    print("\n--- Context Section ---")
    print("Describe the problem/decision that needs to be made.")
    print("(Enter 'DONE' on a blank line when finished)")
    context_lines = []
    while True:
        line = input()
        if line.strip().upper() == "DONE":
            break
        context_lines.append(line)
    context = "\n".join(context_lines)

    # Get decision
    print("\n--- Decision Section ---")
    print("Describe the chosen approach (be specific and actionable).")
    print("(Enter 'DONE' on a blank line when finished)")
    decision_lines = []
    while True:
        line = input()
        if line.strip().upper() == "DONE":
            break
        decision_lines.append(line)
    decision = "\n".join(decision_lines)

    # Get consequences
    print("\n--- Consequences ---")
    print("Enter positive consequences (one per line, blank line to finish):")
    positive = []
    while True:
        line = input("+ ").strip()
        if not line:
            break
        positive.append(f"- {line}")

    print("\nEnter negative consequences/trade-offs (one per line, blank line to finish):")
    negative = []
    while True:
        line = input("- ").strip()
        if not line:
            break
        negative.append(f"- {line}")

    # Get references
    print("\nEnter references (one per line, blank line to finish):")
    print("(e.g., 'SPEC-1', 'Related ADR-010', 'https://...')")
    references = []
    while True:
        line = input("📎 ").strip()
        if not line:
            break
        references.append(f"- {line}")

    return {
        "title": title,
        "deciders": deciders,
        "status": status,
        "supersedes": supersedes,
        "context": context or "{Describe the context here}",
        "decision": decision or "{Describe the decision here}",
        "positive": "\n".join(positive) or "- {Benefit 1}\n- {Benefit 2}",
        "negative": "\n".join(negative) or "- {Trade-off 1}\n- {Mitigation strategies}",
        "references": "\n".join(references) or "- [Related Spec/Document](#)",
    }


def create_adr(
    adr_number: int,
    title: str,
    details: dict,
    output_dir: Path = Path("docs/adr"),
) -> Path:
    """Create ADR file from template."""
    # Create slug from title
    slug = slugify(title)

    # Format filename
    filename = f"ADR-{adr_number:03d}-{slug}.md"
    output_path = output_dir / filename

    # Read template
    template = read_template()

    # Format date
    today = datetime.now().strftime("%Y-%m-%d")

    # Build supersedes line
    supersedes_line = ""
    if details.get("supersedes"):
        supersedes_line = f"\n**Supersedes**: ADR-{details['supersedes']}"

    # Replace placeholders
    content = template.replace("{NUMBER}", f"{adr_number:03d}")
    content = content.replace("{Title}", title)
    content = content.replace("**Status**: Draft | Accepted | Superseded | Deprecated",
                             f"**Status**: {details['status']}{supersedes_line}")
    content = content.replace("{YYYY-MM-DD}", today)
    content = content.replace("{Names or roles}", details["deciders"])

    # Replace sections with user input
    # Context section
    content = re.sub(
        r"## Context\n\n\{Describe the issue.*?\}",
        f"## Context\n\n{details['context']}",
        content,
        flags=re.DOTALL,
    )

    # Decision section
    content = re.sub(
        r"## Decision\n\n\{Describe the chosen.*?\}",
        f"## Decision\n\n{details['decision']}",
        content,
        flags=re.DOTALL,
    )

    # Consequences section
    content = re.sub(
        r"### Positive\n\n- \{Benefit.*?### Negative",
        f"### Positive\n\n{details['positive']}\n\n### Negative",
        content,
        flags=re.DOTALL,
    )

    content = re.sub(
        r"### Negative\n\n- \{Trade-off.*?## References",
        f"### Negative\n\n{details['negative']}\n\n## References",
        content,
        flags=re.DOTALL,
    )

    # References section
    content = re.sub(
        r"## References\n\n.*",
        f"## References\n\n{details['references']}",
        content,
        flags=re.DOTALL,
    )

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write file
    output_path.write_text(content)

    return output_path


def main():
    """Main entry point."""
    try:
        # Get next ADR number
        adr_number = get_next_adr_number()
        print(f"Creating ADR-{adr_number:03d}\n")

        # Prompt for details
        details = prompt_user()

        # Create ADR
        output_path = create_adr(
            adr_number=adr_number, title=details["title"], details=details
        )

        print(f"\n✅ ADR created successfully!")
        print(f"📄 File: {output_path}")
        print(f"\nNext steps:")
        print(f"1. Review and edit {output_path.name}")
        print(f"2. Add entry to docs/adr/README.md")
        print(f"3. Link from relevant specs (SPEC-1, etc.)")

    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
