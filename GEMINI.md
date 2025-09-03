# GEMINI.md

This file provides guidance to Gemini when working with code in this repository.

## Project Overview

Obelisk is an AI-powered virtual try-on and image recontextualization system that allows users to:
1. Generate realistic images of people wearing clothing items
2. Recontextualize images using nano-banana (Gemini 2.5 image) to iteratively edit images from text
3. Create animated videos from the final results

The system consists of a backend agent powered by Google's Vertex AI models and a React-based frontend for easy interaction.

## Agent Flow
1.  **Upload Pictures**: Upload a picture of a person and a product through the frontend.
2.  **Generate Virtual Try-On Image**: The agent generates a virtual try-on image of the person wearing the product.
3.  **Image Editing**: The agent uses nano-banana (Gemini 2.5 image) to iteratively edit the generated image based on text prompts.
4.  **Animate**: Use Veo to animate the recontextualized image.

## Essential Commands

### Environment Setup
```bash
# Install dependencies (frontend + backend)
make install

# Activate virtual environment
poetry shell

# Set required environment variables
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"  # or your preferred region
export BUCKET="gs://your-bucket-name"

# Copy sample images to GCS (one-time setup)
gsutil cp -r img/*.png $BUCKET/products/
```

### Running the Application
```bash
# Run both frontend and backend in development mode
make dev
```

The application will be available at `http://localhost:5173`.

## Architecture Overview

### Core Components

1.  **Frontend** (`frontend/`):
    *   React-based web interface built with Vite.
    *   Uses TypeScript and Tailwind CSS.
    *   Provides components for image upload, virtual try-on, and image editing.

2.  **Backend**
    *   **Agent System** (`obelisk_recontext_agent/agent.py`):
        *   Uses Google ADK with Gemini model
        *   Implements async file upload callback for handling user artifacts
        *   Manages a multi-step workflow: virtual try-on, image editing, and video animation.
    *   **Tool Framework** (`obelisk_recontext_agent/tools.py`):
        *   `generate_virtual_try_on_images`: Wraps the virtual try-on model.
        *   `edit_image`: Uses the Imagen 3 edit model (`imagen-3.0-capability-001`) to edit the image based on a prompt.
        *   `generate_video`: Uses the Veo model to animate the final image.
    *   **API Servers**:
        *   `adk_wrapper.py`: A FastAPI wrapper to make the ADK API compatible with the frontend.
        *   `mock_api.py`: A mock FastAPI server for frontend testing without needing Google Cloud credentials.
        *   `obelisk_recontext_agent/api.py`: A FastAPI application to serve the Obelisk agent.
    *   **Prompt Engineering** (`obelisk_recontext_agent/prompts.py`):
        *   Contains `ROOT_INSTRUCTION` with detailed agent behavior specifications
        *   Defines the structured workflow for the entire process.

### Key Technical Details

- **AI Models**:
  - Agent: Gemini 2.5 Flash
  - Virtual Try-On: `virtual-try-on-preview-08-04`
  - Image Editing: `imagen-3.0-capability-001`
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

### Frontend
- The frontend is a React application built with Vite.
- It uses TypeScript and Tailwind CSS.
- Components are located in `frontend/src/components`.

### Testing
- `test_frontend.py`: A Python script to check if the frontend is running.
- `test_api.html`: A simple HTML file to test the virtual try-on API.
- The `tests/call_api_test.py` file contains commented-out code that may serve as a starting point for testing.

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
