"""
HeadlineArt Pipeline — Multi-Agent Workflow

A 7-agent pipeline that transforms daily news into art:
  News Scout → News Analyst → Creative Director → Art Generator → Copywriter → Quality Reviewer → Image Creator

Uses Microsoft Agent Framework with spec-driven agent definitions.
Each agent's instructions are loaded from spec files in ./specs/.
"""

import asyncio
import base64
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from typing_extensions import Never

from agent_framework import (
    AgentRunResponseUpdate,
    AgentRunUpdateEvent,
    ChatAgent,
    ChatMessage,
    Executor,
    Role,
    TextContent,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowOutputEvent,
    WorkflowStatusEvent,
    WorkflowRunState,
    handler,
)
from agent_framework.azure import AzureAIClient
from azure.identity import DefaultAzureCredential as SyncDefaultAzureCredential
from azure.identity import get_bearer_token_provider
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncAzureOpenAI

load_dotenv(override=True)

ENDPOINT = os.environ.get("FOUNDRY_PROJECT_ENDPOINT", "")
MODEL = os.environ.get("FOUNDRY_MODEL_DEPLOYMENT_NAME", "")
IMAGE_MODEL = os.environ.get("FOUNDRY_IMAGE_MODEL_DEPLOYMENT_NAME", "gpt-image-1.5")
IMAGE_ENDPOINT = os.environ.get("FOUNDRY_IMAGE_ENDPOINT", "")
BING_CONNECTION_ID = os.environ.get("BING_CONNECTION_ID", "")
SPECS_DIR = Path(__file__).parent / "specs"
OUTPUT_DIR = Path(__file__).parent / "generated_images"

MAX_REVIEW_CYCLES = 3


def _load_spec(filename: str) -> str:
    """Load agent instructions from a spec markdown file."""
    spec_path = SPECS_DIR / filename
    content = spec_path.read_text(encoding="utf-8")
    # Extract the Instructions section as the agent prompt
    return content


# ---------------------------------------------------------------------------
# Executor 1: News Scout
# ---------------------------------------------------------------------------
class NewsScoutExecutor(Executor):
    """Scans news sources and collects top daily stories."""

    agent: ChatAgent

    def __init__(self, agent: ChatAgent, id: str = "NewsScout"):
        self.agent = agent
        super().__init__(id=id)

    @handler
    async def handle_trigger(
        self, messages: list[ChatMessage], ctx: WorkflowContext[list[ChatMessage]]
    ) -> None:
        response = await self.agent.run(messages)
        messages.extend(response.messages)
        # Emit update event for HTTP streaming
        for msg in response.messages:
            if msg.role == Role.ASSISTANT:
                await ctx.add_event(
                    AgentRunUpdateEvent(
                        self.id,
                        data=AgentRunResponseUpdate(
                            contents=[TextContent(text=f"[NewsScout] {msg.contents[-1].text[:200]}...")],
                            role=Role.ASSISTANT,
                            response_id=str(uuid4()),
                        ),
                    )
                )
        await ctx.send_message(messages)


# ---------------------------------------------------------------------------
# Executor 2: News Analyst
# ---------------------------------------------------------------------------
class NewsAnalystExecutor(Executor):
    """Curates, ranks, and identifies themes from collected news."""

    agent: ChatAgent

    def __init__(self, agent: ChatAgent, id: str = "NewsAnalyst"):
        self.agent = agent
        super().__init__(id=id)

    @handler
    async def handle_stories(
        self, messages: list[ChatMessage], ctx: WorkflowContext[list[ChatMessage]]
    ) -> None:
        response = await self.agent.run(messages)
        messages.extend(response.messages)
        for msg in response.messages:
            if msg.role == Role.ASSISTANT:
                await ctx.add_event(
                    AgentRunUpdateEvent(
                        self.id,
                        data=AgentRunResponseUpdate(
                            contents=[TextContent(text=f"[NewsAnalyst] {msg.contents[-1].text[:200]}...")],
                            role=Role.ASSISTANT,
                            response_id=str(uuid4()),
                        ),
                    )
                )
        await ctx.send_message(messages)


# ---------------------------------------------------------------------------
# Executor 3: Creative Director
# ---------------------------------------------------------------------------
class CreativeDirectorExecutor(Executor):
    """Translates curated news into an art concept brief."""

    agent: ChatAgent
    review_count: int = 0

    def __init__(self, agent: ChatAgent, id: str = "CreativeDirector"):
        self.agent = agent
        super().__init__(id=id)

    @handler
    async def handle_analysis(
        self, messages: list[ChatMessage], ctx: WorkflowContext[list[ChatMessage]]
    ) -> None:
        # Skip if this is a final approval routed from QualityReviewer
        for msg in reversed(messages):
            if msg.role == Role.USER and msg.contents:
                if "[FINAL_APPROVED]" in (msg.contents[-1].text if hasattr(msg.contents[-1], 'text') else ""):
                    return
                break

        response = await self.agent.run(messages)
        messages.extend(response.messages)
        for msg in response.messages:
            if msg.role == Role.ASSISTANT:
                await ctx.add_event(
                    AgentRunUpdateEvent(
                        self.id,
                        data=AgentRunResponseUpdate(
                            contents=[TextContent(text=f"[CreativeDirector] {msg.contents[-1].text[:200]}...")],
                            role=Role.ASSISTANT,
                            response_id=str(uuid4()),
                        ),
                    )
                )
        await ctx.send_message(messages)


# ---------------------------------------------------------------------------
# Executor 4: Art Generator
# ---------------------------------------------------------------------------
class ArtGeneratorExecutor(Executor):
    """Produces image generation prompts from the art concept brief."""

    agent: ChatAgent

    def __init__(self, agent: ChatAgent, id: str = "ArtGenerator"):
        self.agent = agent
        super().__init__(id=id)

    @handler
    async def handle_brief(
        self, messages: list[ChatMessage], ctx: WorkflowContext[list[ChatMessage]]
    ) -> None:
        response = await self.agent.run(messages)
        messages.extend(response.messages)
        for msg in response.messages:
            if msg.role == Role.ASSISTANT:
                await ctx.add_event(
                    AgentRunUpdateEvent(
                        self.id,
                        data=AgentRunResponseUpdate(
                            contents=[TextContent(text=f"[ArtGenerator] {msg.contents[-1].text[:200]}...")],
                            role=Role.ASSISTANT,
                            response_id=str(uuid4()),
                        ),
                    )
                )
        await ctx.send_message(messages)


# ---------------------------------------------------------------------------
# Executor 5: Copywriter
# ---------------------------------------------------------------------------
class CopywriterExecutor(Executor):
    """Crafts Instagram caption, hashtags, and CTA."""

    agent: ChatAgent

    def __init__(self, agent: ChatAgent, id: str = "Copywriter"):
        self.agent = agent
        super().__init__(id=id)

    @handler
    async def handle_prompts(
        self, messages: list[ChatMessage], ctx: WorkflowContext[list[ChatMessage]]
    ) -> None:
        response = await self.agent.run(messages)
        messages.extend(response.messages)
        for msg in response.messages:
            if msg.role == Role.ASSISTANT:
                await ctx.add_event(
                    AgentRunUpdateEvent(
                        self.id,
                        data=AgentRunResponseUpdate(
                            contents=[TextContent(text=f"[Copywriter] {msg.contents[-1].text[:200]}...")],
                            role=Role.ASSISTANT,
                            response_id=str(uuid4()),
                        ),
                    )
                )
        await ctx.send_message(messages)


# ---------------------------------------------------------------------------
# Executor 6: Quality Reviewer (with feedback loop)
# ---------------------------------------------------------------------------
class QualityReviewerExecutor(Executor):
    """Reviews full package; approves or sends back for revision."""

    agent: ChatAgent
    review_count: int = 0

    def __init__(self, agent: ChatAgent, id: str = "QualityReviewer"):
        self.agent = agent
        super().__init__(id=id)

    @handler
    async def handle_package(
        self, messages: list[ChatMessage], ctx: WorkflowContext[list[ChatMessage], str]
    ) -> None:
        self.review_count += 1

        # Add review instruction
        review_prompt = ChatMessage(
            role=Role.USER,
            text=(
                f"[Review cycle {self.review_count}/{MAX_REVIEW_CYCLES}] "
                "Review the complete content package above. "
                "Respond with APPROVED or REVISION_NEEDED as the first word, "
                "followed by your detailed assessment."
            ),
        )
        review_messages = messages + [review_prompt]

        response = await self.agent.run(review_messages)
        review_text = response.text or ""

        for msg in response.messages:
            if msg.role == Role.ASSISTANT:
                await ctx.add_event(
                    AgentRunUpdateEvent(
                        self.id,
                        data=AgentRunResponseUpdate(
                            contents=[TextContent(text=f"[QualityReviewer] {msg.contents[-1].text[:200]}...")],
                            role=Role.ASSISTANT,
                            response_id=str(uuid4()),
                        ),
                    )
                )

        if "APPROVED" in review_text.upper() or self.review_count >= MAX_REVIEW_CYCLES:
            # Package approved — route to ImageCreator for final image generation
            status = 'APPROVED' if 'APPROVED' in review_text.upper() else 'APPROVED (max cycles reached)'
            approved_summary = (
                f"Review cycle: {self.review_count}\n"
                f"Status: {status}\n\n"
                f"{review_text}"
            )
            approved_msg = ChatMessage(
                role=Role.USER,
                text=f"[FINAL_APPROVED]\n\n{approved_summary}",
            )
            messages.extend(response.messages)
            messages.append(approved_msg)
            await ctx.send_message(messages)
        else:
            # Send back to Creative Director with revision feedback
            revision_msg = ChatMessage(
                role=Role.USER,
                text=(
                    f"[REVISION REQUESTED — Cycle {self.review_count}]\n"
                    f"The quality reviewer has requested revisions. "
                    f"Please revise your work based on this feedback:\n\n{review_text}"
                ),
            )
            messages.extend(response.messages)
            messages.append(revision_msg)
            await ctx.send_message(messages)


# ---------------------------------------------------------------------------
# Executor 7: Image Creator (generates the final artwork)
# ---------------------------------------------------------------------------
class ImageCreatorExecutor(Executor):
    """Generates the final artwork image using gpt-image-1.5."""

    agent: ChatAgent
    image_client: AsyncAzureOpenAI

    def __init__(self, agent: ChatAgent, image_client: AsyncAzureOpenAI, id: str = "ImageCreator"):
        self.agent = agent
        self.image_client = image_client
        super().__init__(id=id)

    @handler
    async def handle_final(
        self, messages: list[ChatMessage], ctx: WorkflowContext[list[ChatMessage], str]
    ) -> None:
        # Only process approved packages, skip revision requests
        for msg in reversed(messages):
            if msg.role == Role.USER and msg.contents:
                last_text = msg.contents[-1].text if hasattr(msg.contents[-1], 'text') else ""
                if "[REVISION" in last_text:
                    return  # Not for us — this is a revision going to CreativeDirector
                break

        # Step 1: Use the agent to extract a safe, simplified image prompt
        extract_msg = ChatMessage(
            role=Role.USER,
            text=(
                "Based on the entire conversation above, create a SHORT image generation "
                "prompt (max 150 words) for creating the HeadlineArt artwork. "
                "IMPORTANT RULES:\n"
                "- Describe ONLY abstract art, colors, shapes, textures, and artistic styles\n"
                "- Do NOT mention any real people, public figures, brands, or company names\n"
                "- Do NOT reference violence, conflict, weapons, or political events\n"
                "- Do NOT include any text or words to render in the image\n"
                "- Focus on: artistic style, color palette, composition, mood, and visual metaphors\n"
                "- Use terms like 'abstract', 'digital art', 'surreal', 'impressionist' etc.\n"
                "Return ONLY the prompt text, nothing else."
            ),
        )
        prompt_messages = messages + [extract_msg]
        response = await self.agent.run(prompt_messages)
        image_prompt = response.text or "Abstract digital art with flowing gradients of blue and gold, surreal landscape, dreamy atmosphere"

        # Truncate to avoid overly complex prompts that trigger moderation
        if len(image_prompt) > 800:
            image_prompt = image_prompt[:800]

        await ctx.add_event(
            AgentRunUpdateEvent(
                self.id,
                data=AgentRunResponseUpdate(
                    contents=[TextContent(text=f"[ImageCreator] Extracting prompt and generating image...")],
                    role=Role.ASSISTANT,
                    response_id=str(uuid4()),
                ),
            )
        )

        # Step 2: Generate the image with gpt-image-1.5 (with moderation retry)
        image_path_str = "(image generation failed)"
        prompts_to_try = [
            image_prompt,
            # Fallback: a generic abstract art prompt if the first one is blocked
            (
                "Abstract digital artwork with flowing organic shapes, vibrant gradients "
                "of teal, coral, and gold, surreal dreamlike atmosphere, soft glowing light, "
                "modern contemporary art style, Instagram aesthetic, 1024x1024"
            ),
        ]

        for attempt, prompt in enumerate(prompts_to_try):
            try:
                print(f"[ImageCreator] Attempt {attempt + 1}: endpoint={IMAGE_ENDPOINT}")
                print(f"[ImageCreator] Attempt {attempt + 1}: model={IMAGE_MODEL}")
                print(f"[ImageCreator] Attempt {attempt + 1}: prompt (first 200 chars): {prompt[:200]}")
                img_response = await self.image_client.images.generate(
                    model=IMAGE_MODEL,
                    prompt=prompt,
                    size="1024x1024",
                    n=1,
                )
                print(f"[ImageCreator] API response received, data items: {len(img_response.data)}")

                # Save the image
                OUTPUT_DIR.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_path = OUTPUT_DIR / f"quadro_{timestamp}.png"

                image_data = base64.b64decode(img_response.data[0].b64_json)
                image_path.write_bytes(image_data)
                image_path_str = str(image_path)
                print(f"[ImageCreator] Image saved: {image_path_str} ({len(image_data)} bytes)")

                await ctx.add_event(
                    AgentRunUpdateEvent(
                        self.id,
                        data=AgentRunResponseUpdate(
                            contents=[TextContent(text=f"[ImageCreator] Image saved to: {image_path_str}")],
                            role=Role.ASSISTANT,
                            response_id=str(uuid4()),
                        ),
                    )
                )
                break  # Success — stop retrying
            except Exception as e:
                import traceback
                print(f"[ImageCreator] Attempt {attempt + 1} ERROR: {type(e).__name__}: {e}")
                traceback.print_exc()
                if attempt == len(prompts_to_try) - 1:
                    # All attempts failed
                    await ctx.add_event(
                        AgentRunUpdateEvent(
                            self.id,
                            data=AgentRunResponseUpdate(
                                contents=[TextContent(text=f"[ImageCreator] Image generation error after {attempt + 1} attempts: {type(e).__name__}: {e}")],
                                role=Role.ASSISTANT,
                                response_id=str(uuid4()),
                            ),
                        )
                    )
                else:
                    print(f"[ImageCreator] Retrying with fallback prompt...")
                    await ctx.add_event(
                        AgentRunUpdateEvent(
                            self.id,
                            data=AgentRunResponseUpdate(
                                contents=[TextContent(text=f"[ImageCreator] Prompt was blocked by content filter, retrying with safer prompt...")],
                                role=Role.ASSISTANT,
                                response_id=str(uuid4()),
                            ),
                        )
                    )

        # Step 3: Yield final output
        # Extract the approved summary from the last [FINAL_APPROVED] message
        approved_text = ""
        for msg in reversed(messages):
            if msg.role == Role.USER and msg.contents:
                t = msg.contents[-1].text if hasattr(msg.contents[-1], 'text') else ""
                if "[FINAL_APPROVED]" in t:
                    approved_text = t.replace("[FINAL_APPROVED]", "").strip()
                    break

        final_output = (
            f"=== HEADLINEART — FINAL PACKAGE ===\n\n"
            f"Image: {image_path_str}\n"
            f"Prompt: {image_prompt[:300]}\n\n"
            f"{approved_text}"
        )
        await ctx.yield_output(final_output)


# ---------------------------------------------------------------------------
# Build the workflow
# ---------------------------------------------------------------------------
async def build_workflow():
    """Create and return the multi-agent workflow."""

    credential = DefaultAzureCredential()

    # Create Azure OpenAI client for image generation (gpt-image-1.5)
    # Key-based auth is disabled; use Entra ID token auth instead
    sync_credential = SyncDefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        sync_credential, "https://cognitiveservices.azure.com/.default"
    )
    image_client = AsyncAzureOpenAI(
        azure_endpoint=IMAGE_ENDPOINT,
        api_version="2025-04-01-preview",
        azure_ad_token_provider=token_provider,
    )

    # Create 7 AzureAI clients + agents, each with spec-driven instructions
    async def create_agent(spec_file: str, name: str, tools: list | None = None) -> ChatAgent:
        instructions = _load_spec(spec_file)
        client = AzureAIClient(
            project_endpoint=ENDPOINT,
            model_deployment_name=MODEL,
            credential=credential,
        )
        kwargs: dict = {"name": name, "instructions": instructions}
        if tools:
            kwargs["tools"] = tools
        return client.create_agent(**kwargs)

    # Create Bing Grounding search tool for real-time news
    bing_tools: list | None = None
    if BING_CONNECTION_ID:
        from agent_framework.azure import AzureAIClient as _AzureAIClient
        bing_search_tool = _AzureAIClient.get_web_search_tool(bing_connection_id=BING_CONNECTION_ID)
        bing_tools = [bing_search_tool]
        print(f"[Setup] Bing Grounding enabled for NewsScout (connection: {BING_CONNECTION_ID[:40]}...)")
    else:
        print("[Setup] BING_CONNECTION_ID not set — NewsScout will use LLM knowledge only (no live web search)")

    news_scout_agent = await create_agent("01_news_scout.md", "NewsScout", tools=bing_tools)
    news_analyst_agent = await create_agent("02_news_analyst.md", "NewsAnalyst")
    creative_director_agent = await create_agent("03_creative_director.md", "CreativeDirector")
    art_generator_agent = await create_agent("04_art_generator.md", "ArtGenerator")
    copywriter_agent = await create_agent("05_copywriter.md", "Copywriter")
    quality_reviewer_agent = await create_agent("06_quality_reviewer.md", "QualityReviewer")
    image_creator_agent = await create_agent("07_image_creator.md", "ImageCreator")

    # Create executors
    news_scout = NewsScoutExecutor(news_scout_agent)
    news_analyst = NewsAnalystExecutor(news_analyst_agent)
    creative_director = CreativeDirectorExecutor(creative_director_agent)
    art_generator = ArtGeneratorExecutor(art_generator_agent)
    copywriter = CopywriterExecutor(copywriter_agent)
    quality_reviewer = QualityReviewerExecutor(quality_reviewer_agent)
    image_creator = ImageCreatorExecutor(image_creator_agent, image_client)

    # Build workflow with review loop + image generation:
    # NewsScout → NewsAnalyst → CreativeDirector → ArtGenerator → Copywriter → QualityReviewer → ImageCreator
    #                           ↑_______________________________________________|  (on REVISION_NEEDED)
    workflow = (
        WorkflowBuilder()
        .set_start_executor(news_scout)
        .add_edge(news_scout, news_analyst)
        .add_edge(news_analyst, creative_director)
        .add_edge(creative_director, art_generator)
        .add_edge(art_generator, copywriter)
        .add_edge(copywriter, quality_reviewer)
        # Review loop: Quality Reviewer → Creative Director (on revision)
        .add_edge(quality_reviewer, creative_director)
        # Final step: Quality Reviewer → Image Creator (on approval)
        .add_edge(quality_reviewer, image_creator)
        .build()
    )

    return workflow


# ---------------------------------------------------------------------------
# HTTP Server entrypoint
# ---------------------------------------------------------------------------
async def main():
    """Run the workflow as an HTTP server."""
    from azure.ai.agentserver.agentframework import from_agent_framework

    workflow = await build_workflow()
    agent = workflow.as_agent()
    await from_agent_framework(agent).run_async()


if __name__ == "__main__":
    asyncio.run(main())
