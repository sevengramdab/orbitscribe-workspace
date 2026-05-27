"""
Business Tool Registry
All monetization tools register here so agents can discover and execute them.
"""

import asyncio
import importlib
import inspect
from typing import Any, Callable, Dict, List, Optional


class BusinessTool:
    def __init__(
        self,
        name: str,
        description: str,
        fn: Callable,
        category: str = "general",
        requires_api_key: bool = False,
        api_key_env: Optional[str] = None,
    ):
        self.name = name
        self.description = description
        self.fn = fn
        self.category = category
        self.requires_api_key = requires_api_key
        self.api_key_env = api_key_env

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool, handling both sync and async functions."""
        if asyncio.iscoroutinefunction(self.fn):
            return await self.fn(**kwargs)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self.fn(**kwargs))


class BusinessToolRegistry:
    """Central registry for all business automation tools."""

    _instance = None
    _tools: Dict[str, BusinessTool] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(
        self,
        name: str,
        description: str,
        fn: Callable,
        category: str = "general",
        requires_api_key: bool = False,
        api_key_env: Optional[str] = None,
    ) -> BusinessTool:
        tool = BusinessTool(name, description, fn, category, requires_api_key, api_key_env)
        self._tools[name] = tool
        return tool

    def get(self, name: str) -> Optional[BusinessTool]:
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[Dict[str, str]]:
        tools = self._tools.values()
        if category:
            tools = [t for t in tools if t.category == category]
        return [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "requires_api_key": t.requires_api_key,
            }
            for t in tools
        ]

    def categories(self) -> List[str]:
        return sorted({t.category for t in self._tools.values()})

    async def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Tool '{name}' not found", "available": list(self._tools.keys())}
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return {"error": str(e), "tool": name}


# Global singleton instance
registry = BusinessToolRegistry()


def business_tool(name: str, description: str, category: str = "general", requires_api_key: bool = False, api_key_env: Optional[str] = None):
    """Decorator to register a function as a business tool."""
    def decorator(fn: Callable):
        registry.register(name, description, fn, category, requires_api_key, api_key_env)
        return fn
    return decorator
