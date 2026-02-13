# HeadlineArt — Multi-Agent Pipeline

A spec-driven, 7-agent workflow that transforms daily news into art — including actual image generation — using Microsoft Agent Framework and Azure AI Foundry.

## Architecture

```
Input (trigger)
    → News Scout         — Searches the web via Bing Grounding for real-time news
    → News Analyst       — Filters, ranks, identifies themes
    → Creative Director  — Creates art concept brief
    → Art Generator      — Produces image generation prompts
    → Copywriter         — Crafts Instagram caption + hashtags
    → Quality Reviewer   — Approves or loops back for revisions
    │    ↑_________________________________|  (on REVISION_NEEDED, max 3 cycles)
    └→ Image Creator     — Generates the final artwork with gpt-image-1.5
         ↓
    Final Package (image + caption + hashtags)
```

## Agent Specs

Each agent's behavior is defined in a spec file under `specs/`:

| # | Agent | Spec | Purpose |
|---|-------|------|---------|
| 1 | News Scout | `specs/01_news_scout.md` | Search the web for today's most compelling stories (via Bing Grounding) |
| 2 | News Analyst | `specs/02_news_analyst.md` | Curate top 3 stories, identify unifying theme |
| 3 | Creative Director | `specs/03_creative_director.md` | Design art concept with style, palette, symbolism |
| 4 | Art Generator | `specs/04_art_generator.md` | Create optimized image generation prompts |
| 5 | Copywriter | `specs/05_copywriter.md` | Write Instagram caption, hashtags, CTA |
| 6 | Quality Reviewer | `specs/06_quality_reviewer.md` | Score and approve/reject the final package |
| 7 | Image Creator | `specs/07_image_creator.md` | Generate actual artwork using gpt-image-1.5 |

## Tech Stack

- **Microsoft Agent Framework** (`agent-framework-core`, `agent-framework-azure-ai`) — workflow orchestration
- **Azure AI Foundry** — model hosting (gpt-4.1 for text agents, gpt-image-1.5 for image generation)
- **Bing Grounding** — real-time web search for the News Scout agent
- **Entra ID (DefaultAzureCredential)** — token-based authentication (no API keys)
- **AsyncAzureOpenAI** — async client for image generation API
- **agentdev CLI** — HTTP server + debugging with AI Toolkit Agent Inspector

## Setup

### 1. Prerequisites

- Python 3.10+
- An Azure AI Foundry project with **gpt-4.1** deployed
- An Azure OpenAI resource with **gpt-image-1.5** deployed
- A **Grounding with Bing Search** connection in your Azure AI Foundry project (optional but recommended)
- Azure CLI logged in (`az login`) with access to both resources

### 2. Configure environment

Copy the sample and fill in your values:

```bash
cp .env.sample .env
```

```env
# Microsoft Foundry — text agents (gpt-4.1)
FOUNDRY_PROJECT_ENDPOINT=https://<your-resource>.services.ai.azure.com/api/projects/<your-project>
FOUNDRY_MODEL_DEPLOYMENT_NAME=gpt-4.1

# Image generation — gpt-image-1.5
FOUNDRY_IMAGE_MODEL_DEPLOYMENT_NAME=gpt-image-1.5
FOUNDRY_IMAGE_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/

# Bing Grounding — real-time web search for News Scout (optional)
# Get from: Azure AI Foundry > Connected resources > Grounding with Bing Search
BING_CONNECTION_ID=<your-bing-connection-id>
```

> **Note:** Authentication uses `DefaultAzureCredential` (Entra ID). No API keys are needed — just make sure you are logged in with `az login`.

### 3. Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

### 4. Run the server

```bash
python app.py
```

The HTTP server starts via agentdev CLI. Use `--port 8087` to specify a port:

```bash
python -m agentdev run app.py --verbose --port 8087
```

## Debugging with AI Toolkit

Press **F5** in VS Code to:
1. Start the HTTP server with debugpy on port 5679
2. Launch the AI Toolkit Agent Inspector
3. Interact with the workflow visually — see each agent's input/output in real time

The launch configuration is pre-configured in `.vscode/launch.json` and `.vscode/tasks.json`.

## How It Works

1. Send a message like *"Scan today's news and create an art quadro"*
2. The **News Scout** searches the web via Bing Grounding for today's top stories
3. The **News Analyst** curates the top 3 with visual potential
4. The **Creative Director** designs an art concept brief (style, palette, symbolism)
5. The **Art Generator** produces optimized image generation prompts
6. The **Copywriter** creates the Instagram caption, hashtags, and CTA
7. The **Quality Reviewer** scores everything (1–10 across 5 categories)
   - If **APPROVED**: routes the package to the Image Creator
   - If **REVISION_NEEDED**: loops back to Creative Director (max 3 cycles)
8. The **Image Creator** extracts a safe, abstract art prompt and calls gpt-image-1.5
   - If content moderation blocks the prompt, it automatically retries with a generic fallback
   - The generated image is saved as a PNG to `generated_images/quadro_YYYYMMDD_HHMMSS.png`
9. The final output includes the image path, prompt used, caption, and hashtags

## Image Generation Details

The Image Creator agent uses **gpt-image-1.5** via `AsyncAzureOpenAI` with Entra ID token authentication. Key design decisions:

- **Safe prompt extraction**: The agent rewrites prompts to focus on abstract art, avoiding brand names, real people, and sensitive content that would trigger content moderation
- **Prompt length cap**: Prompts are truncated to 800 characters to reduce moderation false positives
- **Automatic retry**: If the first prompt is blocked, a generic abstract art fallback prompt is used
- **Output**: Images are saved as 1024x1024 PNG files in the `generated_images/` directory

## Customization

- **Edit specs** in `specs/` to adjust agent behavior, quality criteria, or output format
- **Change the text model** in `.env` — different models produce different creative styles
- **Change the image model** in `.env` — swap `gpt-image-1.5` for another supported model
- **Adjust review cycles** — modify `MAX_REVIEW_CYCLES` in `app.py` (default: 3)

## Project Structure

```
HeadlineArt/
├── app.py                          # Main 7-agent workflow + HTTP server
├── requirements.txt                # Pinned dependencies
├── .env.sample                     # Environment template (safe to commit)
├── .gitignore                      # Excludes .env, venv, pycache
├── specs/                          # Agent spec files (instructions)
│   ├── 01_news_scout.md
│   ├── 02_news_analyst.md
│   ├── 03_creative_director.md
│   ├── 04_art_generator.md
│   ├── 05_copywriter.md
│   ├── 06_quality_reviewer.md
│   └── 07_image_creator.md
├── generated_images/               # Output PNGs (created at runtime)
├── .vscode/
│   ├── launch.json                 # Debug configuration (F5)
│   └── tasks.json                  # Build/run tasks
└── README.md
```

## Next Steps

- **Add tracing** — Monitor agent interactions and latency with OpenTelemetry
- **Add evaluation** — Measure quality consistency across runs
- **Schedule daily runs** — Automate with Azure Functions or cron
- **Post to Instagram** — Integrate Instagram Graph API to publish directly
