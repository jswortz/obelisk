# GEMINI.md

This file provides guidance to Gemini when working with code in this repository.

## Project Overview

Obelisk is a Python-based AI agent that first generates virtual try-on images and then recontextualizes them by changing the background using Google's Imagen 3 model. Finally, it animates the results using Veo. It takes product and person images (from GCS or local files) and generates new scenes based on prompts.

## Agent Flow
1.  **Upload Pictures**: Upload a picture of a person and a product.
2.  **Generate Virtual Try-On Image**: The agent generates a virtual try-on image of the person wearing the product.
3.  **Recontextualize Background**: The agent uses Imagen 3's background swap feature to place the person and product in a new scene based on a prompt.
4.  **Animate**: Use Veo to animate the recontextualized image.

## Virtual Try-On

Obelisk supports virtual try-on functionality using the Generative AI SDK. This allows you to generate images of a person wearing a specific clothing product.

### Using the GenAI SDK for Virtual Try-On

Here is a code snippet demonstrating how to use the `virtual-try-on-preview-08-04` model with the Python GenAI SDK:

```python
from google import genai
from google.genai.types import RecontextImageSource, ProductImage

client = genai.Client()

# TODO(developer): Update and un-comment below line
# output_file = "output-image.png"

image = client.models.recontext_image(
    model="virtual-try-on-preview-08-04",
    source=RecontextImageSource(
        person_image=Image.from_file(location="test_resources/man.png"),
        product_images=[ProductImage(product_image=Image.from_file(location="test_resources/sweater.jpg"))]
    )
)

image.generated_images[0].image.save(output_file)

print(f"Created output image using {len(image.generated_images[0].image.image_bytes)} bytes")
# Example response:
# Created output image using 1234567 bytes
```

This code snippet shows how to provide a person's image and a product image to the model to generate a virtual try-on image. You will need to replace the placeholder file paths with the actual paths to your images.

## Essential Commands

### Environment Setup
```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Set required environment variables
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"  # or your preferred region
export BUCKET="gs://your-bucket-name"

# Copy sample images to GCS (one-time setup)
gsutil cp -r img/*.png $BUCKET/products/
```

### Running the Agent
```bash
# Run the agent in the cli
poetry run adk run obelisk_recontext_agent
```

Then run some tests:

```bash
hello!
```

## Architecture Overview

### Core Components

1.  **Agent System** (`obelisk_recontext_agent/agent.py`):
    *   Uses Google ADK with Gemini model
    *   Implements async file upload callback for handling user artifacts
    *   Manages a multi-step workflow: virtual try-on, background recontextualization, and video animation.

2.  **Tool Framework** (`obelisk_recontext_agent/tools.py`):
    *   `generate_virtual_try_on_images`: Wraps the virtual try-on model.
    *   `recontext_image_background`: Uses the Imagen 3 edit model (`imagen-3.0-capability-001`) with background swap mode to change the background of the virtual try-on image.
    *   `generate_video`: Uses the Veo model to animate the final image.

3.  **Prompt Engineering** (`obelisk_recontext_agent/prompts.py`):
    *   Contains `ROOT_INSTRUCTION` with detailed agent behavior specifications
    *   Defines the structured workflow for the entire process.

### Key Technical Details

- **AI Models**:
  - Agent: Gemini 2.5 Flash
  - Virtual Try-On: `virtual-try-on-preview-08-04`
  - Image Editing (Background Swap): `imagen-3.0-capability-001`
  - Video Generation: `veo-3.0-generate-preview`

- **Image Handling**:
  - Supports both GCS URIs and local file uploads
  - Generated images are saved as artifacts and uploaded to GCS
  - Image size limit: 30MB

- **Authentication**: Uses Google Cloud default credentials

## Development Guidelines

### Code Style
- This is a Poetry-managed Python 3.12+ project
- Follow existing async patterns when adding new callbacks
- Use type hints for function parameters and returns
- Handle Google Cloud authentication errors gracefully

### Testing
Currently minimal test coverage. When adding tests:
- Place them in the `tests/` directory
- Consider using pytest (add to dependencies first)
- Test both GCS URI and artifact-based workflows

### Common Tasks

1.  **Adding New Tools**:
    *   Define tool functions in `tools.py`
    *   Register them in the agent configuration
    *   Follow the existing pattern of supporting both GCS and artifact inputs

2.  **Modifying Agent Behavior**:
    *   Update `ROOT_INSTRUCTION` in `prompts.py`
    *   Test with various prompt examples from README.md

3.  **Debugging**:
    *   Check environment variables are properly set
    *   Verify Google Cloud authentication
    *   Ensure GCS bucket permissions are correct
    *   Monitor image sizes (must be <30MB)

## Important Notes

- The project currently lacks linting, formatting, and comprehensive testing setup
- No CI/CD pipeline is configured
- Consider adding logging configuration for production use
- The `tests/call_api_test.py` file contains commented-out code that may serve as a starting point for testing