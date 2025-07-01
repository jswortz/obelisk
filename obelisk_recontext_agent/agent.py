from google.adk.agents import Agent
from .prompts import ROOT_INSTRUCTION
from .tools import (
    generate_recontextualized_images_from_gcs,
)
from google.adk.agents.callback_context import CallbackContext

from google.genai import types


root_agent = Agent(
    model="gemini-2.5-flash",
    name="product_recontextualiztion_agent",
    description="An agent that recontextualizes product images into new scenes based on a prompt.",
    instruction=ROOT_INSTRUCTION,
    tools=[
        generate_recontextualized_images_from_gcs,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
)
