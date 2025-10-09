"""
awesome-well-mcp 包

井身结构图生成器 MCP 服务
基于井数据自动生成井身结构图的服务
"""

__version__ = "1.0.3"
__author__ = "awesome-well-mcp team"
__description__ = "井身结构图生成器 MCP 服务"

from .main import main, generate_well_structure

__all__ = ["main", "generate_well_structure"]
