"""Commerce assistant built on Google ADK.

Re-exports ``root_agent`` and ``app`` for ADK tooling discovery.
"""

from .agent import root_agent
from .app import app

__all__ = ["app", "root_agent"]
