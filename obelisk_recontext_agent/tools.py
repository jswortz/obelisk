import requests
from google.auth import default
from google.auth.transport.requests import Request
import os
import json
from google.adk.tools import ToolContext
import uuid
from google.genai import types
from google.cloud import storage
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest
import logging

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "gcp-obelisk-dev")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")


class ImageGeneratorTool:
    def __init__(self, project_id: str, region: str):
        self.project_id = project_id
        self.region = region
        self.api_endpoint = f"https://{self.region}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.region}/publishers/google/models/imagen-product-recontext-preview-06-30:predict"

    def get_access_token(self):
        credentials, _ = default()
        credentials.refresh(Request())
        return credentials.token

    def call_gcs_location(
        self,
        prompt: str,
        product_image_gcs_uri: str,
        product_description: str,
        sample_count: int = 1,
        person_image_gcs_uri: str = None,
    ):
        access_token = self.get_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        data = {
            "instances": [
                {
                    "prompt": prompt,
                    "productImages": [
                        {
                            "image": {"gcsUri": product_image_gcs_uri},
                            "productConfig": {
                                "productDescription": product_description,
                            },
                        }
                    ],
                }
            ],
            "parameters": {"sampleCount": sample_count},
        }
        if person_image_gcs_uri is not "":
            data["instances"][0].update(
                {"personImage": {"image": {"gcsUri": person_image_gcs_uri}}}
            )

        response = requests.post(self.api_endpoint, headers=headers, json=data)
        response.raise_for_status()

        return response.json()

    def return_local_image_from_artifact(
        self,
        prompt: str,
        image_bytes: bytes,
        product_description: str,
        sample_count: int = 1,
    ):
        access_token = self.get_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        data = {
            "instances": [
                {
                    "prompt": prompt,
                    "productImages": [
                        {
                            "image": {"bytesBase64Encoded": image_bytes},
                            "productConfig": {
                                "productDescription": product_description,
                            },
                        }
                    ],
                }
            ],
            "parameters": {"sampleCount": sample_count},
        }

        response = requests.post(self.api_endpoint, headers=headers, json=data)
        response.raise_for_status()

        return response.json()


async def generate_recontextualized_images_from_gcs(
    prompt: str,
    gcs_uri: str,
    product_description: str,
    sample_count: int,
    tool_context: ToolContext,
    person_gcs_uri: str = "",
):
    """Generates recontextualized images using the ImageGeneratorTool from a gcs file location.

    Args:
        prompt (str): The prompt for image generation.
        gcs_uri (str): The GCS URI of the product image.
        product_description (str): The description of the product.
        sample_count (int, optional): The number of samples to generate.
        person_gcs_uri (str, optional): The GCS URI of the person image. Defaults to blank.

    Returns:
        dict: The JSON response from the image generation API.
    """
    try:
        image_generator = ImageGeneratorTool(project_id=PROJECT_ID, region=LOCATION)
    except Exception as e:
        return {"Status": "generation_error", "Error": str(e)}

    returned_data = image_generator.call_gcs_location(
        prompt, gcs_uri, product_description, sample_count, person_gcs_uri
    )

    # save artifacts - expected schema:
    #     {
    # "predictions": [
    #     {
    #     "mimeType": "image/png",
    #     "bytesBase64Encoded": <generated image as encoded byte string>,
    #     }, ...

    predictions = returned_data["predictions"]
    # iterate over predictions, save to artifacts
    for prediction in predictions:
        image_bytes = prediction["bytesBase64Encoded"]
        filename = uuid.uuid4()
        await tool_context.save_artifact(
            f"{filename}.png",
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        )
        # save the file locally for gcs upload
        upload_file_to_gcs(file_path=f"{filename}.png", file_data=image_bytes)
    return {"status": "complete", "image_filename": f"{filename}.png"}


def upload_file_to_gcs(
    file_path: str,
    file_data: bytes,
    content_type: str = "image/png",
    gcs_bucket: str = os.environ.get("BUCKET"),
):
    """
    Uploads a file to a GCS bucket.
    Args:
        file_path (str): The path to the file to upload.
        gcs_bucket (str): The name of the GCS bucket.
    Returns:
        str: The GCS URI of the uploaded file.
    """
    gcs_bucket = gcs_bucket.replace("gs://", "")
    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket)
    blob = bucket.blob(os.path.basename(file_path))
    blob.upload_from_string(file_data, content_type=content_type)
    return f"gs://{gcs_bucket}/{os.path.basename(file_path)}"
