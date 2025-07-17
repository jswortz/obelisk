from google.adk.agents import Agent
from .prompts import ROOT_INSTRUCTION, VEO3_INSTR
from .tools import (
    generate_recontextualized_images,
    before_agent_get_user_file,
    generate_video,
    concatenate_videos,
    upload_file_to_gcs,
)
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from google.adk.tools import load_artifacts
from google.adk.planners import BuiltInPlanner


visual_generator = Agent(
    model="gemini-2.5-pro",
    name="visual_generator",
    description="Generate final visuals using image and video generation tools",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction=f"""You are an expert at prompting for VEO3. 
    Use the existing recontextualized image to create dynamic videos prompted from the user. 
    Think about the best practices when constructing the prompt for the `generate_video` tool.
    Think about how to block each scene which is 8 seconds long"""
    + VEO3_INSTR,
    tools=[generate_video, upload_file_to_gcs],
    generate_content_config=types.GenerateContentConfig(temperature=1.2),
)


root_agent = Agent(
    model="gemini-2.5-flash",
    name="product_recontextualiztion_agent",
    description="An agent that recontextualizes product images into new scenes based on a prompt.",
    instruction=ROOT_INSTRUCTION,
    tools=[generate_recontextualized_images, upload_file_to_gcs, load_artifacts],
    sub_agents=[visual_generator],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    before_agent_callback=before_agent_get_user_file,
)
