# ✦ Atlas Research Agent

> **Evidence-first AI research, with answers you can inspect.**

Atlas is a focused, production-oriented AI research agent. It plans a research path, selects retrieval tools, filters noisy evidence, and produces a structured, cited answer with confidence and limitations.

🌐 **GitHub:** [Nikhil-tech-eng](https://github.com/Nikhil-tech-eng) · ✉️ **Email:** [teckchandaninikhil@gmail.com](mailto:teckchandaninikhil@gmail.com)

---

## ✨ What it does

```text
Question → Plan → Select tools → Retrieve → Filter & rank → Synthesize → Validate citations → JSON brief
```

| Capability | Implementation |
| --- | --- |
| 🧠 Planning | LLM produces a typed, visible research plan with 2–6 steps. |
| 🔎 Retrieval | Tavily web search, Wikipedia search, and safe public-page fetching. |
| 🧹 Evidence quality | Empty/weak sources are filtered; URLs are deduplicated and ranked. |
| 📌 Grounding | Every finding must cite a URL returned by retrieval. |
| 🛡️ Reliability | Retries, fallbacks, isolated tool failures, and safe low-confidence responses. |
| 📊 Observability | Trace ID, latency, source counts, filtering counts, and failure counts. |

## 🖥️ Demo dashboard

The Streamlit dashboard makes the full workflow easy to explain:

- visible plan and tool choices;
- cited findings and retrieved sources;
- confidence, assumptions, limitations, and next steps;
- reliability metrics, failures, and safety controls;
- downloadable final JSON.

It also has an offline **View demo result** mode for presentations without API credits.

```powershell
streamlit run streamlit_app.py
```

Open `http://localhost:8501`.

## 🚀 Quick start

**Requirements:** Python 3.11+

```powershell
git clone https://github.com/Nikhil-tech-eng/<your-repository>.git
cd research-agent

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

Copy-Item .env.example .env
```

Add your key to `.env`:

```env
OPENAI_API_KEY=your_key_here
# Optional, recommended for stronger current-web retrieval
TAVILY_API_KEY=your_tavily_key_here
```

Start the dashboard:

```powershell
streamlit run streamlit_app.py
```

Or use the CLI:

```powershell
research-agent "Compare Qdrant, Weaviate, and Milvus for a small RAG startup."
research-agent "Compare approaches to memory in an AI support agent." -o output.json
```

> ⚠️ OpenAI API billing is separate from a ChatGPT subscription. A `429 insufficient_quota` error means the API organization/project needs available credits or a higher spend limit.

## 🧩 Architecture

```text
                 ┌────────────────┐
                 │ User question  │
                 └───────┬────────┘
                         ▼
                 ┌────────────────┐
                 │ Typed planner  │
                 └───────┬────────┘
                         ▼
 ┌─────────────────────────────────────────────┐
 │ Tool executor: web search · Wikipedia · URL │
 │ retries · fallback · SSRF protection         │
 └────────────────────┬────────────────────────┘
                      ▼
             filter · rank · deduplicate
                      ▼
              typed answer synthesis
                      ▼
       citation allow-list + confidence guardrails
                      ▼
                 FinalAnswer JSON
```

### Why an agent?

Research tasks vary by topic, freshness, and evidence required. A bounded planner/executor flow can choose a suitable retrieval path while retaining deterministic schemas, source limits, and auditable failures. This is deliberately a **single-agent** design: simpler, cheaper, and easier to evaluate than a multi-agent system for this scope.

## ✅ Assignment coverage

| Assignment requirement | Where to see it |
| --- | --- |
| Working agentic workflow | `ResearchAgent` and the Streamlit dashboard |
| At least 2 tools | Three retrieval tools in `tools.py` |
| Visible planning | `ResearchPlan` tab and final JSON |
| Structured final output | Pydantic `FinalAnswer` model |
| Failure handling | Retries, fallback plan, no-evidence and synthesis-failure responses |
| Evaluation framework | [`evaluation/EVALUATION.md`](evaluation/EVALUATION.md) |
| Architecture and tradeoffs | This README |
| Sample outputs | [`examples/`](examples/) |

## 📦 Output contract

Every result contains:

| Field | Purpose |
| --- | --- |
| `user_question` / `short_answer` | Original request and concise result |
| `key_findings` | Claims, evidence, and validated source URLs |
| `sources_used` | Retrieved evidence records |
| `confidence_level` | `low`, `medium`, or `high` |
| `limitations_or_assumptions` | What the answer cannot establish |
| `suggested_next_steps` | Useful follow-up actions |
| `plan`, `failures`, `metrics`, `trace_id` | Auditability and operational context |

## 🛡️ Safety and reliability

| Risk | Mitigation |
| --- | --- |
| Timeouts / transient network failure | Bounded retries with exponential jitter |
| Missing Tavily key | Wikipedia fallback is attempted and recorded |
| Bad tool records | Malformed result items are skipped without discarding valid siblings |
| Weak or duplicate sources | Minimum evidence filter, score ranking, URL deduplication, source cap |
| Hallucinated citations | Findings are removed unless every URL came from retrieval |
| Prompt injection | Untrusted source text is marked and never treated as instructions |
| SSRF | Only public HTTP(S) URLs; redirect destinations are revalidated |
| Planner or synthesis outage | Deterministic fallback plan or safe low-confidence output |

## 🧪 Evaluation

Run the automated checks:

```powershell
python -m pytest -q
python -m ruff check .
```

The evaluation plan covers seven scenarios, including vector-database comparison, Indian HR SaaS discovery, multi-agent tradeoffs, agent memory, blocked local URLs, provider timeouts, and prompt-injection content. See [`evaluation/EVALUATION.md`](evaluation/EVALUATION.md).

## ⚖️ Key tradeoffs

| Decision | Why |
| --- | --- |
| Custom orchestration | Clear and testable for a small, bounded workflow. |
| Single agent | Avoids multi-agent coordination cost and failure complexity. |
| Heuristic ranking | Transparent and cheap; not a replacement for a learned reranker. |
| CLI + Streamlit | Easy to automate and easy to demo; no unnecessary backend service. |
| URL allow-listing | Prevents invented citations, but does not prove claim-level entailment. |

## 🔭 Known limits and next steps

- No JavaScript rendering, PDF ingestion, persistent memory, or semantic reranking.
- Source quality and freshness are heuristic rather than learned.
- Citation validation proves provenance, not full factual entailment.
- A production deployment would add egress sandboxing, DNS revalidation, durable caching, tenant controls, OpenTelemetry, claim-entailment checks, and release-gated evaluation data.

## 📁 Project layout

```text
research-agent/
├── src/research_agent/    # Agent, schemas, LLM adapter, tools, security, CLI
├── tests/                 # Deterministic orchestration and security tests
├── evaluation/            # Test-query rubric and evaluation notes
├── examples/              # Success and failure JSON examples
├── streamlit_app.py       # Presentation dashboard
├── Steps to run.txt       # Windows setup and demo reference
└── pyproject.toml         # Dependencies and tool configuration
```

## 📄 License

Released under the [MIT License](LICENSE).

---

Built by [Nikhil-tech-eng](https://github.com/Nikhil-tech-eng) ✦
