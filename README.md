# 🚀 StarSeeker MCP: GitHub Stars Intelligence Agent

A powerful MCP (Model Context Protocol) server that helps you discover relevant repositories from your own starred list on GitHub. It uses **BM25 keyword ranking** and **Gemini Semantic Search** to find the best tools for your next project.


## 📸 Screenshots

<p align="center">
  <img src="https://github.com/user-attachments/assets/8ff143dd-71c9-4894-90c1-eec89465bc49" width="48%" alt="Fetch and Search">
  <img src="https://github.com/user-attachments/assets/dde9d312-c5aa-4265-b29d-1e1fbfbd69d9" width="48%" alt="Output Results">
  <br>
  <em>StarSeeker: Fetch and Search part (left) and Result (Right)</em>
</p>




## 🚀 Features

- **Semantic Search**: Find repositories based on meaning and context, not just keywords, using Google Gemini (text-embedding-004).
- **Hybrid Search**: Google gemini text embedding + BM25( Fallback to BM25 and popularity-based rank fusion when gemini embedding isn't available.)
- **Docker Ready**: Easy containerized deployment.
- **Fast Performance**: Persistent embedding cache and efficient batching.

## 🛠 File Structure for MCP

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

## ⚙️ Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Star_Seeker_mcp
   ```

2. **Set up Environment**:
   Create a `.env` file in the root directory:
   ```env
   GITHUB_TOKEN=your_github_token
   GEMINI_API_KEY=your_gemini_api_key
   ```
   > **Note**: You can run without a `GITHUB_TOKEN` (GitHub API allows ~60 requests/hr or up to 1000 repos without a token), but a `GEMINI_API_KEY` is **required** for the Agent Playground and semantic search.

3. **Install Dependencies**:
   ```bash
   uv sync
   ```

## 🎮 Quick Start: Agent Playground
The fastest way to experience StarSeeker is through the integrated Agent Playground. It provides a visual chat interface (Gradio) to interact with your GitHub stars.

### 1. Launch the Visual UI (Recommended)
```bash
uv run agent_playground.py
```
- **Access**: Open [http://localhost:8080](http://localhost:8080) in your browser.
- **Features**: Chat with Gemini, ask it to fetch your stars, and then search through them using natural language.

> **💡 Quick Tip**: Once the UI is open, you can simply type:  
> `github name : your_username. Find me some cool React libraries.`  
> The agent will automatically fetch your stars (if not cached) and perform a semantic search.

### 2. Launch the CLI Version
If you prefer the terminal:
```bash
uv run agent_playground.py --cli
```

---

## 🔌 MCP Server (Integration for Cursor/Claude)
If you want to use StarSeeker as a tool inside **Cursor**, **Claude Desktop**, or **Antigravity**, follow these steps.


#### Option A: Running with Docker 
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

### `fetch_stars_tool`
Fetches all starred repositories for a given GitHub username and prepares the search index.
- **Args**: `username` (required), `token` (optional)

### `search_stars_tool`
Search through the fetched repositories using semantic or keyword search.
- **Args**: `username` (required), `query` (required)

## 🔌 Integrations

### 1. Antigravity (tested with Antigravity)
Click on the 3 dots in the top right corner, select **"MCP Servers"** -> **"Manage Servers"** -> **"View Raw Config"**, and paste this json inside of it . Restart Antigravity,then ou can use mcp server:
```json
{
  "mcpServers": {
    "star-seeker-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\path\\to\\Star_Seeker_mcp",
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
3. **Name**: `StarSeeker`, **Type**: `command`.
4. **Command**: `uv --directory "C:\path\to\Star_Seeker_mcp" run mcp_server.py`

### 3. Claude Desktop
Add the following to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "star-seeker-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\path\\to\\Star_Seeker_mcp",
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
- **Local (Windows)**: `explorer %USERPROFILE%\.star_seeker_mcp` to open the directory
- **Local (Linux/macOS)**: `~/.star_seeker_mcp`
- **Inside Docker**: `/root/.star_seeker_mcp` (backed by a Docker volume)

### Terminal Commands to Access Data

#### View Local Data Files (Windows CMD)
```cmd
dir %USERPROFILE%\.star_seeker_mcp
```

#### View Data Files Inside Running Docker Container
```bash
docker exec -it star-seeker-mcp ls -lh /root/.star_seeker_mcp
```

#### Copy a Data File from Docker to Local Machine
```bash
docker cp star-seeker-mcp:/root/.star_seeker_mcp/yourusername_stars.json .
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
