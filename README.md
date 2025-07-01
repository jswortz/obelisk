# Obelisk Recontextualization Agent

This agent recontextualizes product images into new scenes based on a user's prompt. It can take a product image from a Google Cloud Storage (GCS) URI or a local file artifact, and then generate a new image with the product in a different setting.

## Features

- **Recontextualize Product Images:**  The core functionality of this agent is to take a product image and place it into a new scene described by a prompt.
- **GCS and Local Image Support:** The agent can accept product images from either a GCS URI or a local file upload (artifact).
- **Person Image Support:** The agent can optionally take a person's image and include it in the generated scene.
- **Multiple Image Generation:** The agent can generate multiple images in a single request.

Setup:

```
gsutil cp -r img/*.png $BUCKET/products/
```

## How it Works

The agent uses the `imagen-product-recontext-preview-06-30` model on Google Cloud's AI Platform to perform the image generation. It has two main tools:

- `generate_recontextualized_images_from_gcs`: This tool is used when the product image is provided as a GCS URI.
- `generate_recontextualized_images_from_artifact`: This tool is used when the product image is provided as a local file artifact.

The agent will automatically select the appropriate tool based on the user's input. After generating the images, they are saved as artifacts and uploaded to a GCS bucket.

## Prerequisites

- **Google Cloud Project:** You need a Google Cloud project with the AI Platform API enabled.
- **Authentication:** You need to be authenticated with Google Cloud.
- **Environment Variables:** The following environment variables need to be set:
    - `GOOGLE_CLOUD_PROJECT`: Your Google Cloud project ID.
    - `GOOGLE_CLOUD_LOCATION`: The Google Cloud region to use (e.g., `us-central1`).
    - `BUCKET`: The GCS bucket to upload the generated images to.

## Example Prompts

#### Important
Make sure images are less than 30 mb

#### Without a person
`use gs://prism-research-25/products/cup.png and put it on top of mt. everest. the product caption is: orange stanley cup 32 oz with straw`

#### With a person
`Generate a picture of me in a desert running with these shoes: gs://prism-research-25/products/shoe.png. These are black running shoes. The picture of me is here: gs://prism-research-25/products/a_guy.png`
