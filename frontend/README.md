# Obelisk Frontend

React-based frontend for the Obelisk Virtual Try-On and Image Editor application.

## Technology Stack

- React 19 + TypeScript
- Vite for fast development and building
- Tailwind CSS v4 for styling
- Radix UI for accessible components
- React Dropzone for file uploads

## Quick Start

```bash
# Install dependencies
make frontend-install

# Run development server
make frontend-dev

# Build for production
make frontend-build
```

## Features

### Virtual Try-On
- Drag & drop or click to upload person and product images
- Real-time virtual try-on generation
- Maximum file size: 30MB per image

### Image Editor
- Recontextualize generated images with custom backgrounds
- Enter natural language prompts for background changes
- Download edited images

## API Integration

The frontend communicates with the backend API at `http://localhost:8000`. The Vite proxy configuration automatically forwards `/api` requests to the backend.

## Development

The application is structured with:
- `/src/components` - Reusable UI components
- `/src/components/ui` - Base UI components (Button, Card, etc.)
- `/src/lib` - Utility functions

## Environment

No environment variables are required for the frontend. The API proxy is configured in `vite.config.ts`.