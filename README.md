# ⚡ VIGH-02 AI AGENT ⚡
### Offline-First Autonomous Local & Cloud Coding AI Assistant

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/)
[![Local AI](https://img.shields.io/badge/Local%20AI-Ollama%20%7C%20LM%20Studio-green.svg)](https://ollama.com/)
[![Offline](https://img.shields.io/badge/100%25-Offline%20Capable-brightgreen.svg)](https://github.com/)
[![Interface](https://img.shields.io/badge/Interface-CLI%20%26%20Web%20UI-purple.svg)](https://github.com/)

**VIGH-02 AI AGENT** is an intelligent, privacy-first coding AI assistant built to operate **100% locally and offline** without requiring any internet connection. It connects directly to your installed local AI models (such as `Qwen 2.5 Coder`, `Llama 3.2`, `DeepSeek Coder`, `Gemma 3`, `Falcon 3`, and `LM Studio`) to scan entire codebases, surgically edit files, provide architecture suggestions, generate unit tests, perform security audits, and execute terminal workflows.

---

## 🌟 Key Features

- 🔌 **100% Offline Capable**: Works directly with local AI models (Ollama, LM Studio, LocalAI, llama.cpp, vLLM). No internet connection or external API keys required!
- 🌐 **Dual Interface (CLI & Web UI)**: Run directly in your terminal or launch a modern browser IDE with split-panel code editor, visual diffs, and project health dashboard.
- ⚡ **Global Access Anywhere**: Activate with `vigh-02` in any folder or path on your computer.
- 🔍 **Deep Codebase Scanner**: Recursively inspects folder structures, language breakdowns (lines of code per language), open TODOs/FIXMEs, syntax validation, and security vulnerabilities.
- ✏️ **Autonomous File Editing**: Safely creates, edits, and refactors code with real-time before/after diffs and unified patch application.
- ⏪ **Instant Undo History**: File snapshots are preserved before every edit, allowing 1-click rollback (`/undo` or Web UI button).
- 🛡️ **Built-in Security Audit**: Detects hardcoded API keys, dangerous `eval`/`exec`, SQL injection vulnerabilities, and command injection risks.
- 🧪 **Unit Test & Refactor Engine**: One-click generation of comprehensive test suites and code optimizations.
- ☁️ **Optional Cloud Fallback**: Supports OpenAI, Anthropic, Gemini, Groq, and OpenRouter if internet and API keys are configured.

---

## 🚀 Quick Start

### 1. Installation

#### Option A: One-Click Windows Installer
Double-click `vigh_install.bat` or run:
```bash
.\vigh_install.bat
```

#### Option B: Pip Global Install
```bash
cd D:\Rajas-ai
pip install -e .
python -m vigh_agent.cli --install-global
```

---

## 💻 How to Use

### Activate in ANY Folder
Open any terminal in any directory and type:
```bash
vigh-02
```
Or:
```bash
python run_vigh.py
```

### Interactive Launch Menu
When run without flags, **VIGH-02** displays an interactive selection menu:
```text
 ╔══════════════════════════════════════════════════════════════════╗
 ║                     ⚡ VIGH-02 AI AGENT ⚡                       ║
 ║         Offline-First Local & Cloud Coding AI Assistant          ║
 ╚══════════════════════════════════════════════════════════════════╝

 Target Workspace: D:\my-project
 Active Local Model: qwen2.5-coder:7b (100% Offline Capable)

 Select Interface Mode:
   [1] 💻 Terminal CLI   - Interactive command line chat, live diffs & instant code edits
   [2] 🌐 Modern Web UI  - Browser dashboard with Code Editor, Visual Diff & File Tree
   [3] 🔍 Codebase Scan  - Deep structural audit, LOC stats, security check & TODOs
   [4] ⚙️ Select AI Model - Switch between installed local Ollama/LM Studio models
   [5] 🛠️ Global Install - Register 'vigh-02' command globally in Windows PATH
   [6] ❌ Exit

 Enter choice [1-6] (Default is 1):
```

---

## ⚡ Command Line Options & Flags

| Flag | Description | Example |
| :--- | :--- | :--- |
| `--cli`, `-c` | Launch directly in Terminal CLI mode | `vigh-02 --cli` |
| `--web`, `-w` | Launch directly in Modern Web UI mode | `vigh-02 --web` |
| `--scan`, `-s` | Run instant codebase scan and health audit | `vigh-02 --scan` |
| `--dir <path>`, `-d` | Set custom target workspace directory | `vigh-02 -d C:\MyProject` |
| `--model <name>`, `-m` | Specify model to use | `vigh-02 -m qwen2.5-coder:7b` |
| `--port <num>`, `-p` | Custom Web UI port (default `8440`) | `vigh-02 --web -p 9000` |
| `--no-browser` | Prevent auto-opening browser on web start | `vigh-02 --web --no-browser` |
| `--install-global` | Register global Windows terminal command | `vigh-02 --install-global` |

---

## ⌨️ CLI Interactive Slash Commands

Inside the CLI terminal session, you can use built-in slash commands:

- `/scan` — Deeply scan folder structure, stats, languages, security vulnerabilities, and TODOs
- `/edit <file>` — Request the AI to modify or create a specific file
- `/read <file>` — View syntax-highlighted code with line numbers
- `/diff` — Show git working tree or recent file diffs
- `/undo` — Instantly rollback the last file edit or creation
- `/model` — Switch active local AI model (Ollama, LM Studio, etc.)
- `/web` — Launch the modern Web UI in your browser
- `/cd <path>` — Switch active workspace directory to any folder
- `/clear` — Clear terminal screen
- `/help` — Show command cheat sheet
- `/exit` — Exit the agent

---

## 🌐 Web UI Features

When running in **Web UI Mode** (`http://127.0.0.1:8440`), you get an interactive dashboard:

1. **💬 Real-Time Streaming Chat**:
   - Multi-step autonomous agent loop with markdown rendering, syntax highlighting, and copy buttons.
   - Step-by-step tool execution badges (`⚡ Executing read_file...`, `✓ read_file completed`).
2. **📁 Workspace File Explorer**:
   - Hierarchical folder navigation with file icons, size badges, and real-time refreshing.
3. **📝 Integrated Code Editor**:
   - Open any file from your workspace, view syntax-highlighted code, make manual edits, or click **"✨ AI Edit File"**.
4. **🔀 Visual Diff Viewer**:
   - Review proposed and applied changes with highlighted additions (green) and deletions (red).
5. **🔍 Deep Project Health & Security Dashboard**:
   - Visual statistics cards (Total Files, Lines of Code, Open TODOs, Security Findings).
   - Severity-ranked security audit table with exact code snippets.
6. **⚡ 1-Click Quick Actions**:
   - 🔍 *Deep Codebase Scan*
   - ⚡ *Refactor & Optimize*
   - 🧪 *Generate Unit Tests*
   - 🛡️ *Security Vulnerability Audit*
   - 💡 *Explain Architecture*
7. **⏪ Instant Undo & Revert**:
   - Rollback any file modification with one click.

---

## 🧠 Local AI Model Setup (Zero Internet Required)

### 1. Using Ollama (Recommended)
VIGH-02 auto-detects running Ollama models at `http://127.0.0.1:11434`.
You can download models with:
```bash
ollama pull qwen2.5-coder:7b      # High-performance coding model (Recommended)
ollama pull llama3.2              # Lightweight general model
ollama pull deepseek-coder:1.3b   # Ultra-fast lightweight coder
```

### 2. Using LM Studio / llama.cpp / LocalAI
Start local server in LM Studio on `http://127.0.0.1:1234/v1`. VIGH-02 will auto-detect loaded models.

---

## 🛠️ Configuration

Configuration is saved in `~/.vigh02/config.json`:
```json
{
  "provider": "ollama",
  "model": "qwen2.5-coder:7b",
  "ollama_base_url": "http://127.0.0.1:11434",
  "lmstudio_base_url": "http://127.0.0.1:1234/v1",
  "web_host": "127.0.0.1",
  "web_port": 8440,
  "auto_open_browser": true
}
```

---

## 🛡️ License & Architecture

- **Engine**: VIGH-02 ReAct & Autonomous Reasoning Core
- **Backend**: FastAPI + Uvicorn + Python 3.8+
- **CLI**: Rich + Prompt Toolkit
- **Created by**: VIGH-02 AI Team
