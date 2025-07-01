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
import base64

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

    def call_artifacts(
        self,
        prompt: str,
        product_bytes: bytes,
        product_description: str,
        sample_count: int = 1,
        mime_type_product_image: str = "image/png",
        mime_type_person_image: str = "image/png",
        person_bytes: bytes = b"",
    ):

        # Base64 encode the video data
        encoded_product_image = base64.b64encode(product_bytes)
        encoded_person_image = base64.b64encode(person_bytes)

        # Convert the encoded bytes to a string
        encoded_product_image_b64 = encoded_product_image.decode("utf-8")
        encoded_person_image_b64 = encoded_person_image.decode("utf-8")

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
                            "image": {
                                "bytesBase64Encoded": encoded_product_image_b64,
                                "mimeType": mime_type_product_image,
                            },
                            "productConfig": {
                                "productDescription": product_description,
                            },
                        }
                    ],
                }
            ],
            "parameters": {"sampleCount": sample_count},
        }
        if person_bytes != b"":
            data["instances"][0].update(
                {
                    "personImage": {
                        "image": {
                            "bytesBase64Encoded": encoded_person_image_b64,
                            "mimeType": mime_type_person_image,
                        }
                    }
                }
            )

        response = requests.post(self.api_endpoint, headers=headers, json=data)
        response.raise_for_status()

        return response.json()

    def call_gcs_location(
        self,
        prompt: str,
        product_image_gcs_uri: str,
        product_description: str,
        sample_count: int = 1,
        mime_type_product_image: str = "image/png",
        mime_type_person_image: str = "image/png",
        person_image_gcs_uri: str = "",
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
                            "image": {
                                "gcsUri": product_image_gcs_uri,
                                "mime_type": mime_type_product_image,
                            },
                            "productConfig": {
                                "productDescription": product_description,
                            },
                        }
                    ],
                }
            ],
            "parameters": {"sampleCount": sample_count},
        }
        if person_image_gcs_uri != "":
            data["instances"][0].update(
                {
                    "personImage": {
                        "image": {
                            "gcsUri": person_image_gcs_uri,
                            "mimeType": mime_type_person_image,
                        }
                    }
                }
            )

        response = requests.post(self.api_endpoint, headers=headers, json=data)
        response.raise_for_status()

        return response.json()


async def generate_recontextualized_images(
    prompt: str,
    product_uri: str,
    product_description: str,
    sample_count: int,
    tool_context: ToolContext,
    mime_type_product_image: str = "image/png",
    mime_type_person_image: str = "image/png",
    person_uri: str = "",
):
    """Generates recontextualized images using the ImageGeneratorTool from a gcs file location.

    Args:
        prompt (str): The prompt for image generation.
        product_uri (str): The product uri. Can either be a local artifact or a gcs uri.
        product_description (str): The description of the product.
        sample_count (int, optional): The number of samples to generate.
        tool_context (ToolContext): The tool context.
        mime_type_product_image: str = "image/png" the mime type of the provided product image
        mime_type_person_image: str = "image/png" the mime type of the provided person image
        mime_type_person_image: str = "image/png",
        person_uri (str, optional): The person uri. Can either be a local artifact or a gcs uri. Defaults to blank.

    Returns:
        dict: The JSON response from the image generation API.
    """
    try:
        image_generator = ImageGeneratorTool(project_id=PROJECT_ID, region=LOCATION)
    except Exception as e:
        return {"Status": "generation_error", "Error": str(e)}

    try:
        if "gs://" == product_uri[:5]:
            returned_data = image_generator.call_gcs_location(
                prompt,
                product_uri,
                product_description,
                sample_count,
                mime_type_product_image,
                mime_type_person_image,
                person_uri,
            )
        else:
            product_artifact = await tool_context.load_artifact(product_uri)
            product_bytes = product_artifact.inline_data.data
            if person_uri is not "":
                person_artifact = await tool_context.load_artifact(person_uri)
                person_bytes = person_artifact.inline_data.data
            else:
                person_bytes = b""
            returned_data = image_generator.call_artifacts(
                prompt,
                product_bytes,
                product_description,
                sample_count,
                mime_type_product_image,
                mime_type_person_image,
                person_bytes,
            )
    except Exception as e:
        return {"Status": "generation_error", "Error": str(e)}

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


args = {
    "sample_count": 1,
    "prompt": "An orange Stanley cup 32 oz with straw, prominently displayed on the snowy, windswept summit of Mount Everest, with a breathtaking panoramic view of the Himalayan peaks in the background under a clear, bright sky. The cup is standing upright, perhaps with a slight dusting of snow, suggesting it has been there for a moment.",
    "product_description": "orange stanley cup 32 oz with straw",
    "product_uri": "gs://prism-research-25/products/cup.png",
}
