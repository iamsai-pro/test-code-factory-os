"""Factory OS MCP server. Run with: python server.py"""
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("factory-os")

# Each tool module registers its own tools, keeping the code modular.
from tools.llm_gateway import register as register_llm_gateway
from tools.calculator import register as register_calculator
from tools.json_tools import register as register_json
from tools.filesystem import register as register_filesystem
from tools.memory import register as register_memory
from tools.database import register as register_database
from tools.web import register as register_web
from tools.aws_s3 import register as register_s3
from tools.excel_tool import register as register_excel
from tools.word_tool import register as register_word
from tools.pdf_tool import register as register_pdf
from tools.powerpoint_tool import register as register_powerpoint
from tools.vercel_deploy import register as register_vercel
from tools.http_tool import register as register_http
from tools.zip_tool import register as register_zip

for register_tools in (
    register_llm_gateway, register_calculator, register_json, register_filesystem, register_memory,
    register_database, register_web, register_s3, register_excel, register_word,
    register_pdf, register_powerpoint, register_vercel, register_http, register_zip,
):
    register_tools(mcp)

# Unsafe shell / arbitrary code execution is intentionally not enabled by default.
if os.getenv("FACTORY_OS_ENABLE_UNSAFE_TOOLS", "false").lower() == "true":
    from tools.optional_execution import register as register_unsafe
    register_unsafe(mcp)

if __name__ == "__main__":
    mcp.run()
