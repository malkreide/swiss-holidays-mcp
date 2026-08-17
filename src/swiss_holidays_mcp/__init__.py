"""Swiss School Calendar MCP — school and public holidays for all 26 cantons."""

from ._version import __version__
from .server import mcp

__all__ = ["mcp", "__version__"]
