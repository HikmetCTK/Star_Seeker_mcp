# 🚀 StarSeeker MCP: GitHub Stars Intelligence Agent

A powerful MCP (Model Context Protocol) server that helps you discover relevant repositories from your own starred list on GitHub. It uses **BM25 keyword ranking** and **Gemini Semantic Search** to find the best tools for your next project.

## 🚀 Features

- **Semantic Search**: Find repositories based on meaning and context, not just keywords, using Google Gemini (text-embedding-004).
- **Hybrid Search**: Fallback to BM25 and popularity-based rank fusion when AI isn't available.
- **Modular Architecture**: Clean separation of concerns (Config, GitHub Client, Search Engine, Server).
- **Docker Ready**: Easy containerized deployment.
- **Fast Performance**: Persistent embedding cache and efficient batching.

## 🛠 File Structure

- `mcp_server.py`: Main entry point.
- `server.py`: Tool definitions and MCP logic.
- `search_engine.py`: Core logic for BM25 and Gemini embeddings.
- `github_client.py`: GitHub API integration for fetching stars.
- `config.py`: Configuration and environment management.

## 📋 Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended)
- GitHub Personal Access Token (for higher rate limits)
- Gemini API Key (for semantic search capabilities)

## ⚙️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd github_stars_project
   ```

2. **Set up environment variables**:
   Create a `.env` file in the root directory:
   ```env
   GITHUB_TOKEN=your_github_token
   GEMINI_API_KEY=your_gemini_api_key
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

## 🚀 Usage

### 🎨 Agent Playground (Local Testing)
The fastest way to test and interact with the system visually using Gradio.
1. **Run Locally**:
   ```bash
   uv run agent_playground.py
   ```
2. **Access**: Open [http://localhost:8080](http://localhost:8080) in your browser.

### 🔌 MCP Server (Standalone / Production)
To run the server for integration with tools like Cursor or Claude.

#### Option A: Running with Docker (Recommended for Stability)
The Docker image is optimized to only install the core MCP server dependencies (skipping Gradio).

1. **Build and Start**:
   ```bash
   docker-compose up --build -d
   ```
2. **Access**: The server runs on stdio/HTTP inside the container, ready for your tools.

#### Option B: Running Locally
```bash
uv run mcp_server.py
```

## 🛠 MCP Tools

### `_fetch_stars_for_user`
Fetches all starred repositories for a given GitHub username and prepares the search index.
- **Args**: `username` (required), `token` (optional)

### `search_stars`
Search through the fetched repositories using semantic or keyword search.
- **Args**: `username` (required), `query` (required)

## 🔌 Integrations

### 1. Antigravity (tested with Antigravity)
Click on the 3 dots in the top right corner, select **"MCP Servers"** -> **"Manage Servers"** -> **"View Raw Config"**, and add:
```json
{
  "mcpServers": {
    "github-stars": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\path\\to\\github_stars_project",
        "run",
        "mcp_server.py"
      ],
      "env": {
        "GEMINI_API_KEY": "your_key",
        "GITHUB_TOKEN": "your_token"
      }
    }
  }
}
```

### 2. Cursor AI
1. **Settings** -> **Cursor Settings** -> **MCP**.
2. **+ Add New MCP Server**.
3. **Name**: `GitHub Stars`, **Type**: `command`.
4. **Command**: `uv --directory "C:\path\to\github_stars_project" run mcp_server.py`

### 3. Claude Desktop
Add the following to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "github-stars": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\path\\to\\github_stars_project",
        "run",
        "mcp_server.py"
      ],
      "env": {
        "GITHUB_TOKEN": "your_token",
        "GEMINI_API_KEY": "your_key"
      }
    }
  }
}
```

## 📂 Data Storage & Access

The server stores fetched JSON data and search embeddings in a centralized directory to avoid duplicates and ensure persistence.

### File Locations
- **Local (Windows)**: `explorer %USERPROFILE%\.github_stars_mcp` to open the directory
- **Local (Linux/macOS)**: `~/.github_stars_mcp`
- **Inside Docker**: `/root/.github_stars_mcp` (backed by a Docker volume)

### Terminal Commands to Access Data

#### View Local Data Files (Windows CMD)
```cmd
dir %USERPROFILE%\.github_stars_mcp
```

#### View Data Files Inside Running Docker Container
```bash
docker exec -it github-stars-mcp ls -lh /root/.github_stars_mcp
```

#### Copy a Data File from Docker to Local Machine
```bash
docker cp github-stars-mcp:/root/.github_stars_mcp/yourusername_stars.json .
```

## 🧠 How it Works

1. **Data Collection**: Fetches repo names, descriptions, and topics via GitHub API.
2. **Indexing**: 
   - Generates vector embeddings for all descriptions using `text-embedding-004`.
   - Builds a BM25 index for keyword search fallback.
3. **Retrieval**: 
   - Uses Cosine Similarity for semantic matches.
   - For keyword search, it uses a rank fusion of BM25 scores and repository popularity (stars).

## 📄 License
MIT
