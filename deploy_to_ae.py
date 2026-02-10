
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import os

load_dotenv()  # take environment variables

import vertexai
from vertexai import agent_engines

from obelisk_recontext_agent import agent

# create the app


env_vars = {  "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
  "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
  # "GOOGLE_CLOUD_LOCATION": "global" #for gemini 3 endpoints
  }

env_vars["GOOGLE_GENAI_USE_VERTEXAI"] = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
env_vars["BUCKET"] = os.getenv("BUCKET")
if not env_vars["BUCKET"]:
    env_vars["BUCKET"] = "gs://zghost-media-center" # Fallback

print(env_vars)

# create the app

my_agent = agent_engines.AdkApp(
    agent=agent.root_agent,
    enable_tracing=True,
    # env_vars=env_vars,
)


client = vertexai.Client(
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION"),
)

remote_agent = client.agent_engines.create(
    agent=my_agent,
    config=dict(
    requirements=[
        "google-cloud-aiplatform>=1.38.0",
        "google-adk>=0.0.1",
        "google-genai>=0.3.0",
        "typing-extensions>=4.0.0",
        "pydantic>=2.0.0"
    ],
    display_name="Obelisk Agent",
    description="Agent for virtual try-on and image recontextualization",
    extra_packages=[
        "obelisk_recontext_agent", 
    ],
    staging_bucket=env_vars["BUCKET"],
    env_vars=env_vars,
    ),
)

print(f"Deployed Agent Resource Name: {remote_agent.name}")
# Extract just the ID for easier copy-pasting
agent_id = remote_agent.name.split("/")[-1]
print(f"Deployed Agent Resource Name (ID): {agent_id}")