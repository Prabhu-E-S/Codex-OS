from typing import Optional

def build_codex_prompt(goal: str, repository_path: str, project_name: Optional[str] = None) -> str:
    """
    Format a structured prompt to guide Codex execution against the project repository.
    """
    name_str = f"Project: {project_name}\n" if project_name else ""
    return (
        f"# Codex OS Autonomous Engineering Task\n"
        f"{name_str}"
        f"Working Directory: {repository_path}\n\n"
        f"## Engineering Goal\n"
        f"{goal.strip()}\n\n"
        f"## Instructions\n"
        f"1. Inspect the codebase in the working directory.\n"
        f"2. Plan and implement the necessary code modifications to achieve the stated goal.\n"
        f"3. Run validation or tests to verify correctness.\n"
        f"4. Provide a clear summary of all changes made and test results.\n"
    )
