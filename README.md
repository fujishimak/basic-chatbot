# Basic Chatbot

A full-stack conversational AI web app built in pure Python with [Reflex](https://reflex.dev), backed by LangChain for model orchestration.

## Intent

This project is a learning-oriented chatbot that demonstrates how to build a modern, streaming conversational UI without writing any JavaScript. The frontend, state management, and backend event handling are all expressed in Python via Reflex, while LangChain handles the language-model calls, prompting, and tool orchestration.

It is **loosely based on the official [Reflex chatapp tutorial](https://reflex.dev/docs/getting-started/chatapp-tutorial/)**, which provides the baseline streaming chat UI and state pattern. From that starting point it has been extended with:

- **Structured output** — model and guardrail responses are parsed/validated into typed [Pydantic](https://docs.pydantic.dev) models rather than free-form text (e.g. structured search results and a toxicity classifier using `with_structured_output`).
- **Tool calling** — a hand-rolled tool-calling loop (`bind_tools` + a manual dispatch map) lets the assistant invoke tools, including a keyless [Tavily](https://tavily.com) web search, a topic-restriction guardrail, and a toxicity detector.

The assistant is configured as a helpful full-stack Python assistant, with guardrails that keep conversation on-topic and decline toxic input.

## Model hosting

The language-model endpoint is hosted at the [Spur Innovation Center](https://spuric.com/en/index.html) in Canada, which exposes an OpenAI-compatible gateway. This is why the environment template includes a `SPUR_ENDPOINT` variable pointing at that gateway (`https://ai.spuric.com/v1`).

The models used are:

- **Hari** — the main conversational model that powers the assistant's responses.
- **Llama 3B** — a small, fast model used as the classifier for the guardrail checks (topic restriction and toxicity detection), where low latency matters more than deep reasoning.

## Tech stack

- **[Reflex](https://reflex.dev)** — pure-Python full-stack web framework (compiles to React + FastAPI)
- **[LangChain](https://python.langchain.com)** — model orchestration, prompting, tool calling
- **OpenAI-compatible gateway** — chat and classifier models (via `ChatOpenAI`)
- **[Tavily](https://tavily.com)** — keyless web search tool
- **[Pydantic](https://docs.pydantic.dev)** — structured/validated inputs and outputs
- **OpenTelemetry / [OpenLIT](https://openlit.io)** — observability (in progress)

## Getting started

### Prerequisites

- Python (see `.python-version`)
- [uv](https://docs.astral.sh/uv/) for dependency management

### Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Create your environment file from the template and fill in your own values:
   ```bash
   cp .env.template .env
   ```
   Then edit `.env` and set your API keys. See `.env.template` for the required variables. **Never commit your real `.env`** — it is gitignored.

3. Run the app:
   ```bash
   reflex run
   ```

## Configuration

All configuration is read from environment variables (see `.env.template`):

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | API key for the main chat model |
| `CLASSIFIER_API_KEY` | API key for the classifier / guardrail models |
| `SPUR_ENDPOINT` | Base URL for the OpenAI-compatible model gateway |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint for OpenTelemetry / OpenLIT |

## Project structure

```
basic_chatbot/
  basic_chatbot.py    # Reflex app: pages, components, UI
  state.py            # State, event handlers, tools (search, topic, toxicity)
  style.py            # Component styling
  logging_config.py   # OpenTelemetry logging setup
```

## Roadmap / TODO

Remaining work to take this from an extended tutorial toward a fuller product:

- [ ] **Logging / instrumentation** — complete the OpenTelemetry + OpenLIT observability wiring (traces, metrics, and app logs in one place)
- [ ] **File upload support** — allow users to attach files to the conversation
- [ ] **RAG integration** — retrieval-augmented generation over a document/knowledge source
- [ ] **Chat UI history panel** — a sidebar listing past conversations
- [ ] **Navigation and menus** — routing between pages and in-app menus
- [ ] **Authentication / Authorisation** — user accounts, login, and per-user scoping

## Acknowledgements

Baseline chat UI and streaming pattern adapted from the [Reflex chatapp tutorial](https://reflex.dev/docs/getting-started/chatapp-tutorial/).
