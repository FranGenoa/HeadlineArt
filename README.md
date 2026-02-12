# Instagram Art Quadro — Multi-Agent Pipeline

A spec-driven, 6-agent workflow that transforms daily news into Instagram-ready art using Microsoft Agent Framework.

## Architecture

```
Input (trigger)
    → News Scout        — Scans news sources, collects top stories
    → News Analyst      — Filters, ranks, identifies themes
    → Creative Director  — Creates art concept brief
    → Art Generator     — Produces image generation prompts
    → Copywriter        — Crafts Instagram caption + hashtags
    → Quality Reviewer  — Approves or loops back for revisions
         ↑_________________________________|  (on REVISION_NEEDED)
```

## Agent Specs

Each agent's behavior is defined in a spec file under `specs/`:

| Agent | Spec | Purpose |
|-------|------|---------|
| News Scout | `specs/01_news_scout.md` | Collect 5-10 visually compelling daily news stories |
| News Analyst | `specs/02_news_analyst.md` | Curate top 3 stories, identify unifying theme |
| Creative Director | `specs/03_creative_director.md` | Design art concept with style, palette, symbolism |
| Art Generator | `specs/04_art_generator.md` | Create optimized image generation prompts |
| Copywriter | `specs/05_copywriter.md` | Write Instagram caption, hashtags, CTA |
| Quality Reviewer | `specs/06_quality_reviewer.md` | Score and approve/reject the final package |

## Setup

### 1. Configure your Foundry endpoint

Edit `.env` with your Microsoft Foundry credentials:

```env
FOUNDRY_PROJECT_ENDPOINT=<your-foundry-project-endpoint>
FOUNDRY_MODEL_DEPLOYMENT_NAME=<your-foundry-model-deployment-name>
```

**Recommended model:** `gpt-5.1` or `gpt-4.1` for best reasoning + creativity balance.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the server

```bash
python app.py
```

The HTTP server starts on port 8000 by default.

## Debugging with AI Toolkit

Press **F5** in VS Code to:
1. Start the HTTP server with debugpy
2. Open the AI Toolkit Agent Inspector
3. Interact with the workflow visually

The launch configuration is pre-configured in `.vscode/launch.json` and `.vscode/tasks.json`.

## How It Works

1. Send a message like *"Scan today's news and create an art quadro"*
2. The **News Scout** gathers stories from its training knowledge
3. The **News Analyst** curates the top 3 with visual potential
4. The **Creative Director** designs an art concept brief
5. The **Art Generator** produces DALL-E/Midjourney prompts
6. The **Copywriter** creates the Instagram content package
7. The **Quality Reviewer** scores everything (1-10 across 5 categories)
   - If score ≥ 7: **APPROVED** — ready to publish
   - If score < 7: **REVISION_NEEDED** — loops back to Creative Director (max 3 cycles)

## Customization

- **Edit specs** in `specs/` to adjust agent behavior, quality criteria, or output format
- **Change the model** in `.env` — different models produce different creative styles
- **Adjust review threshold** — modify `MAX_REVIEW_CYCLES` in `app.py`

## Project Structure

```
instagram-art-quadro/
├── app.py                          # Main workflow + HTTP server
├── requirements.txt                # Pinned dependencies
├── .env                            # Foundry configuration
├── specs/                          # Agent spec files (instructions)
│   ├── 01_news_scout.md
│   ├── 02_news_analyst.md
│   ├── 03_creative_director.md
│   ├── 04_art_generator.md
│   ├── 05_copywriter.md
│   └── 06_quality_reviewer.md
├── .vscode/
│   ├── launch.json                 # Debug configuration
│   └── tasks.json                  # Build/run tasks
└── README.md
```

## Next Steps

- **Add tracing** — Monitor agent interactions and performance with OpenTelemetry
- **Add evaluation** — Measure quality consistency across runs
- **Connect real news APIs** — Add a tool/function call for live news fetching
- **Add image generation** — Integrate DALL-E 3 API for actual image creation
- **Schedule daily runs** — Automate with Azure Functions or cron
