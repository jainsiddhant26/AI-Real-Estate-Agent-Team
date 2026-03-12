# 🏠 Hindustan Realty AI — Multi-Agent Investment Advisor

> A PM portfolio project demonstrating agentic AI product thinking, rapid prototyping, and full-stack deployment using free and freemium tools.

🔗 **Live App:** [hindustan-realty-ai.streamlit.app](https://hindustan-realty-ai.streamlit.app/)
📦 **GitHub:** [github.com/jainsiddhant26/AI-Real-Estate-Agent-Team](https://github.com/jainsiddhant26/AI-Real-Estate-Agent-Team)

---

## 🎯 Problem Statement

Home buyers in Indian Tier 1 & 2 cities spend **8–12 hours** manually:

- Switching between MagicBricks, 99acres, Housing.com, and NoBroker
- Copy-pasting prices, amenities, and locality details into spreadsheets
- Estimating market trends and risk factors with incomplete or outdated data
- Making valuation calls without a consistent framework

There is no single tool that:

- Aggregates live listings from **multiple Indian portals**
- Adds **hyperlocal market context** (city and locality-level insights)
- Provides **per-property investment signals** (Fair / Overpriced / Underpriced) + clear next steps
- Exports a **single shareable report** ready for brokers, family, or investors

---

## 💡 Solution

**Hindustan Realty AI** compresses 8 hours of research into under 2 minutes using a 3-agent AI pipeline:

| Agent | Job | Technology |
|-------|-----|------------|
| Agent 1 — Property Search | Scrapes live listings from selected portals into a typed schema | Firecrawl Extract API |
| Agent 2 — Market Analysis | Analyzes city-level trends, neighbourhoods, investment outlook, risks | LLaMA 3.3 70B via Groq |
| Agent 3 — Property Valuation | Rates each property: Fair / Overpriced / Underpriced + one clear action | LLaMA 3.3 70B via Groq |

---

## 🏗 Architecture

### Logical Flow

```
User Inputs
    ↓
[Agent 1] Property Search — Firecrawl Extract API
    ↓  Structured PropertyListing objects (Pydantic)
[Agent 2] Market Analysis — Groq + LLaMA 3.3 70B
    ↓  City & locality context
[Agent 3] Property Valuation — Groq + LLaMA 3.3 70B
    ↓
Downloadable Markdown Report
```

### Component Breakdown

```
┌──────────────────────────────────────────────────────────┐
│                      Streamlit UI                        │
│  Sidebar: City · Locality · Budget · BHK · Platforms     │
│  Main: Status indicators · Cards · Analysis · Download   │
└─────────────────────┬────────────────────────────────────┘
                      │
           ┌──────────▼───────────┐
           │  Agent 1: Search     │
           │  Firecrawl Extract   │
           │  MagicBricks         │
           │  99acres             │
           │  Housing.com         │
           │  NoBroker            │
           └──────────┬───────────┘
                      │ List[PropertyListing]
           ┌──────────▼───────────┐
           │  Agent 2: Market     │
           │  Agno + Groq         │
           │  LLaMA 3.3 70B       │
           └──────────┬───────────┘
                      │ Markdown analysis
           ┌──────────▼───────────┐
           │  Agent 3: Valuation  │
           │  Agno + Groq         │
           │  LLaMA 3.3 70B       │
           └──────────┬───────────┘
                      │
           ┌──────────▼───────────┐
           │  Report Builder      │
           │  st.download_button  │
           └──────────────────────┘
```

### Physical Stack

- **UI & Orchestration:** Streamlit (`app.py`)
- **Agent Framework:** Agno (Python-native, open source)
- **LLM Provider:** Groq — LLaMA 3.3 70B versatile (free tier)
- **Web Extraction:** Firecrawl Python client (free tier)
- **Data Validation:** Pydantic v2
- **Configuration:** `.env` locally · Streamlit Secrets on cloud
- **Deployment:** Streamlit Community Cloud (free, always-on)

---

## ⚙️ Tech Stack

| Layer | Tool | Cost |
|-------|------|------|
| UI & Orchestration | Streamlit | Free |
| Agent Framework | Agno | Free / Open Source |
| LLM Inference | Groq (LLaMA 3.3 70B) | Free — 1,000 req/day |
| Web Extraction | Firecrawl Extract API | Free — 500 credits |
| Data Modelling | Pydantic v2 | Free |
| Config & Secrets | python-dotenv + Streamlit Secrets | Free |
| Deployment | Streamlit Community Cloud | Free |

**Total infrastructure cost: ₹0**

---

## 🧠 Key Product Decisions

### 1. India-Focused Portal Choice

**Decision:** Optimize for MagicBricks, 99acres, Housing.com, NoBroker.

**Why:** Most real-estate AI demos use US portals (Zillow, Realtor.com). Indian portals are heavier on JavaScript and anti-bot protection — a harder and more relevant challenge that shows deeper product research.

---

### 2. Three Agents with Separate Responsibilities

- **Agent 1 (Search):** Scrape → validate → structure. No LLM calls here.
- **Agent 2 (Market):** Macro insights only. No individual property mentions.
- **Agent 3 (Valuation):** Per-property signal + action. Uses Agent 2 output as context.

**Why:** Mirrors the real user mental model — Find → Understand → Decide. Easier to iterate and debug. Stronger story in interviews.

---

### 3. Sequential Execution with Progress Indicators

Agents run **one after another** with `st.status` indicators showing live progress.

**Why:**
- Free-tier rate limits on Groq (30 RPM) and Firecrawl make parallel execution risky
- Non-technical users can see exactly what is happening
- Clear step-by-step story for portfolio and interview demos

---

### 4. Hidden API Keys

Keys are **never shown in the UI**. Loaded from:
- `.env` locally (git-ignored)
- Streamlit Secrets in production

**Why:** Portfolio apps are shared publicly. Exposing key input fields looks unprofessional and risks misuse.

---

### 5. Fallback Demo Data

If Firecrawl returns no results, the app falls back to 3 curated demo listings and still runs the full agent pipeline.

**Why:** Portfolio demos must never show a blank screen. The fallback ensures Agent 2 and Agent 3 always run and the full value is always visible.

---

### 6. Groq over Gemini

**Decision:** Switched from Gemini 2.0 Flash to Groq + LLaMA 3.3 70B mid-build.

**Why:** Gemini's free tier returned `limit: 0` and `404` errors for Indian API keys. Groq's free tier is more generous (1,000 req/day), significantly faster (custom inference silicon), and LLaMA 3.3 70B produces higher-quality market analysis.

**Learning:** Always validate API free-tier availability by geography before committing to a model provider.

---

## 🧩 Data Model

### `PropertyListing` (Pydantic v2)

```python
class PropertyListing(BaseModel):
    address: str              # Full address or locality
    price_inr: str            # e.g. "95 Lakhs", "1.5 Cr"
    bhk: str                  # "2 BHK", "3 BHK"
    area_sqft: str            # Super built-up / carpet area
    listing_url: str          # Direct link to listing
    builder_name: str | None
    amenities: List[str] = [] # ["Gym", "Park", "24x7 Security"]
```

Used in three places:
- Firecrawl Extract API schema (target format)
- Streamlit property cards (UI display)
- LLM prompts (serialized to JSON as context)

---

## 📊 Metrics I Would Track in Production

| Metric | Type | Why |
|--------|------|-----|
| Search completion rate | Funnel | % of users who see results after clicking Search |
| Report download rate | Conversion | Proxy for "user found value" |
| Avg properties per search | Quality | Firecrawl extraction health |
| Agent 2 + 3 latency (p50/p95) | UX | Critical for perceived quality |
| Platform selection distribution | Behavioural | Which portals users trust most |
| Repeat visits | Retention | Are people coming back? |

---

## 🗺 Roadmap (What I Would Build Next)

### V2 — Personalization
- [ ] Save search history per user (SQLite / Streamlit + local DB)
- [ ] Price drop alerts via email (SendGrid free tier)
- [ ] EMI / affordability calculator with live RBI repo rate

### V3 — Intelligence
- [ ] RERA verification check for listed projects
- [ ] Builder reputation scoring (review sentiment analysis)
- [ ] Locality safety / infrastructure index overlay

### V4 — Distribution
- [ ] WhatsApp bot interface (Twilio + WhatsApp API)
- [ ] PDF report export with one click
- [ ] Compare two localities side-by-side

---

## 🚀 Running Locally

### Prerequisites

- Python 3.9+
- Free API keys:
  - [console.groq.com](https://console.groq.com) — Groq (LLaMA 3.3 70B)
  - [firecrawl.dev](https://www.firecrawl.dev) — Web extraction

### Setup

```bash
# Clone the repo
git clone https://github.com/jainsiddhant26/AI-Real-Estate-Agent-Team.git
cd AI-Real-Estate-Agent-Team

# Install dependencies
pip install -r requirements.txt

# Configure keys
cp .env.example .env
# Edit .env with your actual keys

# Run
streamlit run app.py
```

### `.env` format

```
GROQ_API_KEY=your_groq_key_here
FIRECRAWL_API_KEY=your_firecrawl_key_here
```

---

## ☁️ Deployment (Streamlit Cloud)

1. Fork / clone this repo
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select repo, branch `main`, file `app.py`
4. Add secrets in **Settings → Secrets**:

```toml
GROQ_API_KEY = "your_key"
FIRECRAWL_API_KEY = "your_key"
```

5. Deploy — live in ~2 minutes

---

## 📁 File Structure

```
AI-Real-Estate-Agent-Team/
├── app.py              ← Full application: UI + 3 agents + report
├── requirements.txt    ← Python dependencies
├── .env.example        ← API key template (safe to commit)
├── .gitignore          ← Excludes .env and cache files
└── README.md           ← This file
```

---

## 👤 About This Project

Built as a **PM portfolio piece** to demonstrate:

- **Product thinking** — Problem framing, decision tradeoffs, metrics definition, roadmap prioritisation
- **Agentic AI fluency** — Multi-agent pipeline design, prompt engineering, schema design, error handling
- **Rapid prototyping** — 0 → deployed app in one evening using AI-assisted coding
- **Ship-oriented mindset** — UI + backend + report + deployment, end to end, no engineering support

*This project is intentionally built at MVP scope. The goal is to validate the agent pipeline and UX, not production-grade engineering.*

---

**Built with ❤️ in India 🇮🇳**
