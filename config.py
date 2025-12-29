"""
Configuration module for the GitHub Stars MCP Server.
Handles path setup, environment variable loading, and logging.
"""

import pathlib
import os
from dotenv import load_dotenv
import logging
import sys

# Configure logging to output to stderr (required for MCP servers)
logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stderr)],
    format="%(asctime)s [MCP] %(message)s"
)

logger = logging.getLogger(__name__)

# Global storage directory for user data (JSON, Embeddings, .env)
# Default is ~/.star_seeker_mcp
DATA_DIR = pathlib.Path.home() / ".star_seeker_mcp"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables (.env files)
# Strategy: 1. Project-level .env, then 2. Global storage .env
script_dir = pathlib.Path(__file__).parent
load_dotenv(script_dir / ".env")
load_dotenv(DATA_DIR / ".env")

# Default system prompt for the MCP server
SYSTEM_PROMPT = """
You are a helpful assistant that helps users find relevant GitHub repositories based on their search queries. 
You are given a list of repositories that a user has starred on GitHub. You can suggest repositories that are relevant to the user's search query.
"""

# Default Gemini model for completions and tool use
DEFAULT_MODEL = "gemini-3-flash-preview"

def get_data_dir():
    """Returns the absolute path to the data storage directory."""
    return DATA_DIR

def get_system_prompt():
    """Returns the default system prompt for the AI model."""
    return SYSTEM_PROMPT

def get_default_model():
    """Returns the default Gemini model name."""
    return DEFAULT_MODEL
