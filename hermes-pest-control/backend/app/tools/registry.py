from app.tools.contracts import BackendTool
from app.tools.definitions.default import DEFAULT_BACKEND_TOOLS


class ToolRegistry:
    def __init__(self, tools: list[BackendTool] | None = None) -> None:
        self._tools = {tool.name: tool for tool in (tools or DEFAULT_BACKEND_TOOLS)}

    def list_tools(self) -> list[BackendTool]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> BackendTool | None:
        return self._tools.get(name)

    def require_tool(self, name: str) -> BackendTool:
        tool = self.get_tool(name)
        if tool is None:
            raise KeyError(f"Unknown backend tool: {name}")
        return tool

    def is_allowed(self, tool_name: str, action: str) -> bool:
        tool = self.get_tool(tool_name)
        return bool(tool and tool.is_action_allowed(action))

    def runtime_metadata(self) -> list[dict]:
        return [tool.as_runtime_metadata() for tool in self.list_tools()]


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry()
