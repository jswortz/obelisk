from google.adk.agents import Agent
from .prompts import (
    ROOT_INSTRUCTION,
    VEO3_INSTR,
    VISUAL_GENERATOR_INSTRUCTIONS,
    GLOBAL_INSTRUCTIONS,
)
from .tools import (
    recontext_image_background,
    before_agent_get_user_file,
    generate_video,
    generate_virtual_try_on_images,
)
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from google.adk.tools import load_artifacts
from google.adk.planners import BuiltInPlanner
from google.adk.agents.callback_context import CallbackContext
from google.genai import types  # For types.Content
from typing import Optional

visual_generator = Agent(
    model="gemini-2.5-pro",
    name="visual_generator",
    description="Generate final visuals using image and video generation tools",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction=VISUAL_GENERATOR_INSTRUCTIONS + VEO3_INSTR,
    tools=[generate_video],
    generate_content_config=types.GenerateContentConfig(temperature=1.2),
)


root_agent = Agent(
    model="gemini-2.5-flash",
    name="product_recontextualiztion_agent",
    description="An agent that recontextualizes product images into new scenes based on a prompt.",
    global_instruction=GLOBAL_INSTRUCTIONS,
    instruction=ROOT_INSTRUCTION,
    tools=[
        recontext_image_background,
        load_artifacts,
        generate_virtual_try_on_images,
    ],
    sub_agents=[visual_generator],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    before_agent_callback=before_agent_get_user_file,
)
