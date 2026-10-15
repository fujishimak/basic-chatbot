# Basic Chatbot

A full-stack conversational AI web app built in pure Python with [Reflex](https://reflex.dev), backed by LangChain for model orchestration.

## Intent

This project is a learning-oriented chatbot that demonstrates how to build a modern, streaming conversational UI without writing any JavaScript. The frontend, state management, and backend event handling are all expressed in Python via Reflex, while LangChain handles the language-model calls, prompting, and tool orchestration.

It is **loosely based on the official [Reflex chatapp tutorial](https://reflex.dev/docs/getting-started/chatapp-tutorial/)**, which provides the baseline streaming chat UI and state pattern. From that starting point it has been extended with:

- **Structured output** — model and guardrail responses are validated into typed [Pydantic](https://docs.pydantic.dev) models via `with_structured_output` rather than free-form text (used for search results, the topic classifier, and the toxicity detector). This replaced brittle string parsers (e.g. `BooleanOutputParser`) that broke whenever the model returned prose or JSON instead of a bare `YES`/`NO`.
- **Tool calling** — a hand-rolled tool-calling loop (`bind_tools` + a manual dispatch map) lets the assistant invoke a keyless [Tavily](https://tavily.com) web search tool when a query needs external or up-to-date information.
- **Input guardrails as deterministic pre-checks** — topic restriction and toxicity detection run as plain `async` functions (via `asyncio.gather`) **before** the agent is invoked, not as optional tools. Framing them as tools let them crowd out the search tool and made enforcement non-deterministic; running them as a pre-check gate guarantees they always execute and short-circuit on failure.
- **Observability** — application logs and LLM/tool traces are exported over OTLP to a self-hosted [OpenLIT](https://openlit.io) instance (see Observability below).

The assistant is configured as a helpful full-stack Python assistant. The topic guardrail keeps conversation on-topic (allowing social pleasantries), and the toxicity guardrail declines to engage with MEDIUM/HIGH-rated input.

### Request flow

```
user query
   │
   ▼
input guardrails (topic + toxicity, run concurrently)  ← pre-check gate
   ├── off-topic / toxic ──► short-circuit with a refusal (agent never runs)
   │
   ▼ passed
agent: model with search_tool bound
   ├── model requests search_tool ──► run it, feed results back
   │
   ▼
stream the final answer into the chat
```

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
- **OpenTelemetry / [OpenLIT](https://openlit.io)** — traces, metrics, and logs over OTLP

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

## Observability

Telemetry is exported over OTLP to a self-hosted OpenLIT instance (OpenLIT + ClickHouse, run via `podman-compose` / `docker compose`). `openlit.init()` auto-instruments the LLM and tool calls (traces + metrics), while application logs are bridged into OpenTelemetry through the standard-library logging handler configured in `logging_config.py` and shipped to the same OTLP endpoint, so logs and traces land together.

The OTLP receiver listens on `:4318` (HTTP) and `:4317` (gRPC). Point `OTEL_EXPORTER_OTLP_ENDPOINT` at it (default `http://127.0.0.1:4318`).

> Note: the OpenLIT image runs its OTLP receiver as an internal OpenTelemetry Collector that must be given a collector config mounted at `/etc/otel/otel-collector-config.yaml`. A mismatched/missing config leaves the receiver unbound and causes `ConnectionReset` errors on export. Use the compose file and collector config from a matching OpenLIT release tag.

## Project structure

```
basic_chatbot/
  basic_chatbot.py    # Reflex app: pages, components, UI (fixed-height flex layout, auto-scroll)
  state.py            # State, event handlers, search tool, guardrail pre-checks, agent loop
  style.py            # Component styling
  logging_config.py   # OpenTelemetry logging -> OTLP export
```

## Roadmap / TODO

Remaining work to take this from an extended tutorial toward a fuller product:

- [x] **Logging / instrumentation** — OpenTelemetry + OpenLIT observability wiring (traces, metrics, and app logs over OTLP)
- [ ] **Output guardrails** — moderate the model's *response* (not just the input) before/while it reaches the user
- [ ] **File upload support** — allow users to attach files to the conversation
- [ ] **RAG integration** — retrieval-augmented generation over a document/knowledge source
- [ ] **Chat UI history panel** — a sidebar listing past conversations
- [ ] **Navigation and menus** — routing between pages and in-app menus
- [ ] **Authentication / Authorisation** — user accounts, login, and per-user scoping

## Acknowledgements

Baseline chat UI and streaming pattern adapted from the [Reflex chatapp tutorial](https://reflex.dev/docs/getting-started/chatapp-tutorial/).
