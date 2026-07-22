"""Swiss School Calendar MCP — school and public holidays for all 26 cantons."""

__version__ = "0.4.0"

from .server import mcp

__all__ = ["mcp", "__version__"]
