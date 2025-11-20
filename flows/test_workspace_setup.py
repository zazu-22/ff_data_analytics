"""Prefect Cloud Workspace Setup Test Flow.

Simple test flow to verify Prefect Cloud integration and local execution.
Validates workspace connectivity, state transitions, and logging to Prefect UI.

Story: 0-1-prefect-cloud-workspace-setup
Acceptance Criteria: AC-3, AC-4
"""

from prefect import flow, task


@task(name="hello-prefect-task")
def hello_task() -> str:
    """Print a message and return it."""
    message = "Hello from Prefect - Workspace setup successful!"
    print(message)
    return message


@flow(name="test-workspace-setup")
def test_workspace_setup() -> None:
    """Test flow for validating Prefect Cloud workspace setup.

    This flow:
    - Executes locally on Mac
    - Sends state transitions to Prefect Cloud
    - Logs task execution to Prefect UI
    - Validates end-to-end workspace connectivity
    """
    result = hello_task()
    print(f"Flow completed with result: {result}")


if __name__ == "__main__":
    # Execute the flow locally (state sent to Prefect Cloud)
    test_workspace_setup()
