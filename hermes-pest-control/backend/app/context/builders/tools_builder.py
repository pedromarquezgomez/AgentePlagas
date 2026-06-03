from typing import Any
from app.tools.contracts import BackendTool
from app.tools.registry import default_tool_registry


class ToolsBuilder:
    def __init__(self, tool_registry: Any = None) -> None:
        self.tool_registry = tool_registry or default_tool_registry()

    def build(self) -> list[BackendTool]:
        if not self.tool_registry:
            return []
        try:
            return self.tool_registry.list_tools()
        except Exception:
            return []
