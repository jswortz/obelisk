from google.adk.agents import Agent
from .prompts import ROOT_INSTRUCTION
from .tools import (
    generate_recontextualized_images,
)
from google.adk.agents.callback_context import CallbackContext
import uuid
from google.genai import types
from typing import Optional
from google.adk.tools import load_artifacts


async def before_agent_get_user_file(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Checks for a user-uploaded file before the agent runs.

    If a file is found in the user's message, this callback processes it,
    converts it to a PNG (if it's a PDF), and saves it as an artifact named
    'user_uploaded_file'. It then returns a direct confirmation message to the
    user and halts further agent processing for the current turn.

    If no file is found, it returns None, allowing the agent to proceed normally.
    """

    parts = []
    if callback_context.user_content and callback_context.user_content.parts:
        parts = [
            p for p in callback_context.user_content.parts if p.inline_data is not None
        ]

    # if no file then continue to agent by returning empty
    if not parts:
        return None

    # if file then save as artifact
    part = parts[-1]

    file_bytes = part.inline_data.data
    file_type = part.inline_data.mime_type
    artifact_key = f"{uuid.uuid4()}.{file_type.split('/')[-1]}"

    # create artifact
    artifact = types.Part.from_bytes(data=file_bytes, mime_type=file_type)

    # save artifact
    version = await callback_context.save_artifact(
        filename=artifact_key, artifact=artifact
    )

    # Formulate a confirmation message
    confirmation_message = (
        f"Thank you! I've successfully processed your uploaded file.\n\n"
        f"It's now ready for the next step and is stored as artifact with key "
        f"'{artifact_key}' (version: {version}, size: {len(file_bytes)} bytes).\n\n"
        f"What would you like to do with it?"
    )
    response = types.Content(
        parts=[types.Part(text=confirmation_message)], role="model"
    )

    return response


root_agent = Agent(
    model="gemini-2.5-flash",
    name="product_recontextualiztion_agent",
    description="An agent that recontextualizes product images into new scenes based on a prompt.",
    instruction=ROOT_INSTRUCTION,
    tools=[
        generate_recontextualized_images,
        load_artifacts
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,
    ),
    before_agent_callback=before_agent_get_user_file,
)
