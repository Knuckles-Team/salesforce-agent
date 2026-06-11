#!/usr/bin/env python3
"""Smoke-validate the salesforce-agent A2A agent server.

Imports the package's ``agent_server`` module and verifies the entry point
and version metadata are importable without starting the server.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from salesforce_agent import agent_server
except ImportError as e:
    print(f"Import Error: {e}")
    print("Please install dependencies via `pip install .[all]`")
    sys.exit(1)


def main() -> int:
    print(f"salesforce-agent agent_server v{agent_server.__version__}")
    if not callable(getattr(agent_server, "agent_server", None)):
        print("FAILED: agent_server() entry point is missing or not callable")
        return 1
    print("Agent server module validated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
