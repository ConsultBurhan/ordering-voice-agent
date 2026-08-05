# Ordering Voice Agent

An interactive voice agent application for automated ordering built with [Pipecat](https://github.com/pipecat-ai/pipecat), SmallWebRTC transport, Anthropic Claude, OpenAI (STT & TTS), and a Vite + React web interface.

---

## 🏗️ Project Architecture

```
ordering-voice-agent/
├── pyproject.toml        # Root UV python configuration & dependencies
├── uv.lock               # UV lockfile
├── .python-version       # Python runtime version (>=3.12)
├── server/               # Voice Agent Server (Pipecat + FastAPI)
│   ├── main.py           # Server entry point
│   ├── config/           # Application settings & logging configuration
│   └── src/
│       └── voice/        # Voice pipeline, latency observers, system prompt
└── client/               # Web Application Frontend (Vite + React)
```

---

## 🚀 Getting Started

### Prerequisites

- **Python**: `>= 3.12`
- **Package Manager**: [`uv`](https://github.com/astral-sh/uv) (for python) and `npm` / `node` (for frontend)

---

## 🐍 Backend Setup (Server)

### 1. Install Dependencies

From the project root directory, sync the python virtual environment:

```bash
uv sync
```

### 2. Configure Environment Variables

Create a `.env` file inside the `server/` directory (or update existing):

```env
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
LANGSMITH_API_KEY=your-langsmith-api-key
```

### 3. Run the Server

From the root directory:

```bash
uv run python server/main.py
```

---

## 💻 Frontend Setup (Client)

### 1. Install Dependencies

Navigate into the `client/` directory and install npm packages:

```bash
cd client
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

---

## 🛠️ Technology Stack

- **Voice Pipeline Framework**: [Pipecat](https://pipecat.ai)
- **Transport**: `SmallWebRTCTransport` (WebRTC audio & video)
- **Speech-to-Text (STT)**: OpenAI Whisper
- **LLM**: Anthropic Claude
- **Text-to-Speech (TTS)**: OpenAI TTS
- **VAD**: Silero VAD
- **Observability & Tracing**: LangSmith
- **Frontend**: Vite + React
