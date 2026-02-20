"""
Orchestrated AI Hierarchy — interactive CLI entry point.

Usage:
    python main.py

Requirements:
    - ANTHROPIC_API_KEY in a .env file (or set as an environment variable)
    - pip install anthropic python-dotenv
"""

import os
import sys

# Ensure project root is on sys.path regardless of where script is run from
_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

# Load .env file if present (so ANTHROPIC_API_KEY can be stored there)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_PROJECT_DIR, ".env"))
except ImportError:
    pass  # dotenv not installed — fall back to environment variables

from orchestrator import OrchestratorAgent  # noqa: E402  (after path fix)

BANNER = """\
╔══════════════════════════════════════════════════════════╗
║          Orchestrated AI Hierarchy                       ║
║                                                          ║
║  Agents: Orchestrator → Research · Code · Data · Writing ║
║  Each agent can spawn sub-agents as needed               ║
║  Type 'quit' or 'exit' to stop                           ║
╚══════════════════════════════════════════════════════════╝"""

SEPARATOR = "─" * 60


def check_api_key() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "[Error] ANTHROPIC_API_KEY environment variable is not set.\n"
            "Export it before running:\n"
            "  export ANTHROPIC_API_KEY=sk-ant-..."
        )
        return False
    return True


def main() -> None:
    print(BANNER)
    print()

    if not check_api_key():
        sys.exit(1)

    orchestrator = OrchestratorAgent()

    while True:
        try:
            task = input("Task> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        if not task:
            continue

        if task.lower() in ("quit", "exit", "q"):
            print("Goodbye.")
            break

        print()
        try:
            result = orchestrator.run(task)
        except Exception as exc:
            print(f"\n[Error] {exc}")
            continue

        print(f"\n{SEPARATOR}")
        print("RESULT")
        print(SEPARATOR)
        print(result)
        print(f"{SEPARATOR}\n")


if __name__ == "__main__":
    main()
