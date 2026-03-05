"""
Web interface for HyperEternalAgent.

This package provides a web-based visualization and orchestration interface
for managing agents, tasks, and flows.
"""

from .api import (
    app,
    run_server,
    get_system,
)

__all__ = [
    "app",
    "run_server",
    "get_system",
]
