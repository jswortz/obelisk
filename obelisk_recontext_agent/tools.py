import requests
from google.auth import default
from google.auth.transport.requests import Request
from google.adk.tools import ToolContext
import uuid
from google.genai import types
from google.cloud import storage
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
import logging
import base64
from typing import Optional
from google import genai
import os
import uuid
import time
import subprocess
import tempfile
from typing import List
from google.genai.types import GenerateVideosConfig


client = genai.Client()

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
        product_bytes_list: list[bytes],
        product_description: str,
        sample_count: int = 1,
        mime_type_product_images: Optional[list[str]] = None,
        mime_type_person_image: str = "image/png",
        person_bytes: bytes = b"",
    ):

        # Set default mime types if not provided
        if mime_type_product_images is None:
            mime_type_product_images = ["image/png"] * len(product_bytes_list)

        # Base64 encode the product images
        product_images_data = []
        for product_bytes, mime_type in zip(
            product_bytes_list, mime_type_product_images
        ):
            encoded_product_image = base64.b64encode(product_bytes)
            encoded_product_image_b64 = encoded_product_image.decode("utf-8")
            product_images_data.append(
                {
                    "image": {
                        "bytesBase64Encoded": encoded_product_image_b64,
                        "mimeType": mime_type,
                    },
                    "productConfig": {
                        "productDescription": product_description,
                    },
                }
            )

        # Base64 encode the person image
        encoded_person_image = base64.b64encode(person_bytes)
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
                    "productImages": product_images_data,
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
        logging.info(f"Raw Request: {response.request}")
        response.raise_for_status()

        return response.json()

    def call_gcs_location(
        self,
        prompt: str,
        product_image_gcs_uris: list[str],
        product_description: str,
        sample_count: int = 1,
        mime_type_product_images: Optional[list[str]] = None,
        mime_type_person_image: str = "image/png",
        person_image_gcs_uri: str = "",
    ):
        access_token = self.get_access_token()

        # Set default mime types if not provided
        if mime_type_product_images is None:
            mime_type_product_images = ["image/png"] * len(product_image_gcs_uris)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Build product images data
        product_images_data = []
        for gcs_uri, mime_type in zip(product_image_gcs_uris, mime_type_product_images):
            product_images_data.append(
                {
                    "image": {
                        "gcsUri": gcs_uri,
                        "mimeType": mime_type,
                    },
                    "productConfig": {
                        "productDescription": product_description,
                    },
                }
            )

        data = {
            "instances": [
                {
                    "prompt": prompt,
                    "productImages": product_images_data,
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
        logging.info(f"Raw Request: {response.request}")
        response.raise_for_status()

        return response.json()


async def generate_recontextualized_images(
    prompt: str,
    product_uris: list[str],
    product_description: str,
    sample_count: int,
    tool_context: ToolContext,
    mime_type_product_images: Optional[list[str]] = None,
    mime_type_person_image: str = "image/png",
    person_uri: str = "",
):
    """Generates recontextualized images using the ImageGeneratorTool from gcs file locations or artifacts.

    Args:
        prompt (str): The prompt for image generation.
        product_uris (list[str]): List of product uris (1-3 images). Can be local artifacts or gcs uris.
        product_description (str): The description of the product (applies to all images).
        sample_count (int): The number of samples to generate.
        tool_context (ToolContext): The tool context.
        mime_type_product_images (list[str], optional): List of mime types for product images. Defaults to "image/png" for all.
        mime_type_person_image (str): The mime type of the provided person image. Defaults to "image/png".
        person_uri (str, optional): The person uri. Can either be a local artifact or a gcs uri. Defaults to blank.

    Returns:
        dict: The JSON response from the image generation API.
    """
    # Validate inputs
    if not product_uris or len(product_uris) > 3:
        return {
            "Status": "validation_error",
            "Error": "Please provide 1-3 product images",
        }

    # Set default mime types if not provided
    if mime_type_product_images is None:
        mime_type_product_images = ["image/png"] * len(product_uris)

    try:
        image_generator = ImageGeneratorTool(project_id=PROJECT_ID, region=LOCATION)
    except Exception as e:
        return {"Status": "generation_error", "Error": str(e)}

    try:
        # Check if all product URIs are GCS URIs
        all_gcs = all(uri.startswith("gs://") for uri in product_uris)

        if all_gcs:
            returned_data = image_generator.call_gcs_location(
                prompt,
                product_uris,
                product_description,
                sample_count,
                mime_type_product_images,
                mime_type_person_image,
                person_uri,
            )
        else:
            # Load product artifacts
            product_bytes_list = []
            for uri in product_uris:
                if uri.startswith("gs://"):
                    return {
                        "Status": "validation_error",
                        "Error": "Cannot mix GCS URIs and artifacts. Please use all GCS URIs or all artifacts.",
                    }
                product_artifact = await tool_context.load_artifact(uri)
                if product_artifact and product_artifact.inline_data:
                    product_bytes_list.append(product_artifact.inline_data.data)

            # Load person artifact if provided
            if person_uri != "":
                person_artifact = await tool_context.load_artifact(person_uri)
                if (
                    person_artifact
                    and person_artifact.inline_data
                    and person_artifact.inline_data.data
                ):
                    person_bytes = person_artifact.inline_data.data
                else:
                    return {"status": "error", "error": "Person image not found"}
            else:
                person_bytes = b""

            returned_data = image_generator.call_artifacts(
                prompt,
                product_bytes_list,
                product_description,
                sample_count,
                mime_type_product_images,
                mime_type_person_image,
                person_bytes,
            )
    except Exception as e:
        return {"Status": "generation_error", "Error": str(e)}
    image_filenames = []
    predictions = returned_data["predictions"]
    # iterate over predictions, save to artifacts
    for prediction in predictions:
        image_bytes = prediction["bytesBase64Encoded"]
        # decode the bytes:
        image_bytes = base64.b64decode(image_bytes)
        filename = uuid.uuid4()
        await tool_context.save_artifact(
            f"{filename}.png",
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        )
        image_filenames.append(f"{filename}.png")
        # save the file locally for gcs upload
        # upload_file_to_gcs(file_path=f"{filename}.png", file_data=image_bytes)
    return {"status": "complete", "image_filenames": image_filenames}


async def upload_file_to_gcs(
    file_path: str,
    tool_context: ToolContext,
) -> dict[str, str]:
    """
    Uploads a file to a GCS bucket.
    Args:
        file_path (str): The path to the file to upload.
    Returns:
        dict: A dictionary containing the status of the upload and the GCS URI if successful.
    """
    gcs_bucket = os.environ.get("BUCKET", "default")
    bucket_name = gcs_bucket.split("gs://")[1]
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(os.path.basename(file_path))
    # get the file bytes:
    file_artifact = await tool_context.load_artifact(filename=file_path)
    if (
        file_artifact
        and file_artifact.inline_data
        and file_artifact.inline_data.mime_type
    ):
        file_data = file_artifact.inline_data.data
        content_type = file_artifact.inline_data.mime_type
        blob.upload_from_string(file_data, content_type=content_type)
        # setup the gcs uri state variable if empty:
        if not tool_context.state.get("recontextualized_image_gcs_uri"):
            tool_context.state["recontextualized_image_gcs_uri"] = []
        tool_context.state["recontextualized_image_gcs_uri"].append(
            f"gs://{bucket_name}/{file_path}"
        )

        return {
            "status": "ok",
            "gsc_uri": f"gs://{bucket_name}/{file_path}",
        }
    else:
        return {"status": "error", "error": "File not found"}


# Example usage with multiple product images
args = {
    "sample_count": 1,
    "prompt": "An orange Stanley cup 32 oz with straw shown from multiple angles, prominently displayed on the snowy, windswept summit of Mount Everest, with a breathtaking panoramic view of the Himalayan peaks in the background under a clear, bright sky.",
    "product_description": "orange stanley cup 32 oz with straw",
    "product_uris": [
        "gs://prism-research-25/products/cup.png",
        "gs://prism-research-25/products/cup_side.png",
    ],
}


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

    saved_artifacts = []
    for part in parts:
        if part.inline_data and part.inline_data.data and part.inline_data.mime_type:
            file_bytes = part.inline_data.data
            file_type = part.inline_data.mime_type
            artifact_key = f"{uuid.uuid4()}.{file_type.split('/')[-1]}"

            # create artifact
            artifact = types.Part.from_bytes(data=file_bytes, mime_type=file_type)

            # save artifact
            version = await callback_context.save_artifact(
                filename=artifact_key, artifact=artifact
            )
            saved_artifacts.append(
                {"key": artifact_key, "version": version, "size": len(file_bytes)}
            )

    # Formulate a confirmation message
    if len(saved_artifacts) == 1:
        artifact_info = saved_artifacts[0]
        confirmation_message = (
            f"Thank you! I've successfully processed your uploaded file.\n\n"
            f"It's now ready for the next step and is stored as artifact with key "
            f"'{artifact_info['key']}' (version: {artifact_info['version']}, size: {artifact_info['size']} bytes).\n\n"
            f"What would you like to do with it?"
        )
    else:
        artifact_details = "\n".join(
            f"- '{info['key']}' (version: {info['version']}, size: {info['size']} bytes)"
            for info in saved_artifacts
        )
        confirmation_message = (
            f"Thank you! I've successfully processed your {len(saved_artifacts)} uploaded files.\n\n"
            f"They are now ready for the next step and are stored as artifacts:\n"
            f"{artifact_details}\n\n"
            f"What would you like to do with them?"
        )

    response = types.Content(
        parts=[types.Part(text=confirmation_message)], role="model"
    )

    return response


def download_blob(bucket_name, source_blob_name):
    """
    Downloads a blob from the bucket.
    Args:
        bucket_name (str): The ID of your GCS bucket
        source_blob_name (str): The ID of your GCS object
    Returns:
        Blob content as bytes.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob = bucket.blob(source_blob_name)
    return blob.download_as_bytes()


async def generate_video(
    prompt: str,
    tool_context: ToolContext,
    number_of_videos: int = 1,
    # aspect_ratio: str = "16:9",
    negative_prompt: str = "",
    existing_image_gcs_uri: str = "",
):
    f"""Generates a video based on the prompt for VEO3.

    Args:
        prompt (str): The prompt to generate the video from.
        tool_context (ToolContext): The tool context.
        number_of_videos (int, optional): The number of videos to generate. Defaults to 1.
        negative_prompt (str, optional): The negative prompt to use. Defaults to "".
        existing_image_gcs_uri (str, optional): The existing image filename, use the saved gcs locations from the `recontextualized_image_gcs_uri` state variable

    Returns:
        dict: status dict

    """
    gen_config = GenerateVideosConfig(
        aspect_ratio="16:9",
        number_of_videos=number_of_videos,
        output_gcs_uri=os.environ["BUCKET"],
        negative_prompt=negative_prompt,
    )
    if existing_image_gcs_uri != "":
        existing_image = types.Image(gcs_uri=existing_image_gcs_uri, mime_type="image/png")
        operation = client.models.generate_videos(
            model="veo-2.0-generate-001",
            prompt=prompt,
            image=existing_image,
            config=gen_config,
        )
    else:
        operation = client.models.generate_videos(
            model="veo-2.0-generate-001", prompt=prompt, config=gen_config
        )
    while not operation.done:
        time.sleep(15)
        operation = client.operations.get(operation)
        print(operation)

    if operation.error:
        return {"status": f"failed due to error: {operation.error}"}

    if operation.response and operation.result and operation.result.generated_videos:

        for generated_video in operation.result.generated_videos:
            if generated_video and generated_video.video and generated_video.video.uri:
                video_uri = generated_video.video.uri
                filename = uuid.uuid4()
                BUCKET = os.getenv("BUCKET")
                if BUCKET:
                    video_bytes = download_blob(
                        BUCKET.replace("gs://", ""),
                        video_uri.replace(BUCKET, "")[1:],  # get rid of slash
                    )
                    print(f"The location for this video is here: {filename}.mp4")
                    await tool_context.save_artifact(
                        f"{filename}.mp4",
                        types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
                    )
                else:
                    return {"status": "error", "error": "BUCKET not set"}
        return {"status": "ok", "video_filename": f"{filename}.mp4"}


async def concatenate_videos(
    video_filenames: List[str],
    tool_context: ToolContext,
    concept_name: str,
):
    """Concatenates multiple videos into a single longer video for a concept.

    Args:
        video_filenames (List[str]): List of video filenames from tool_context artifacts.
        tool_context (ToolContext): The tool context.
        concept_name (str, optional): The name of the concept.

    Returns:
        dict: Status and the location of the concatenated video file.
    """
    if not video_filenames:
        return {"status": "failed", "error": "No video filenames provided"}

    try:
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Load videos from artifacts and save locally
            local_video_paths = []
            for idx, video_filename in enumerate(video_filenames):
                # Load artifact
                video_part = await tool_context.load_artifact(video_filename)
                if not video_part:
                    return {
                        "status": "failed",
                        "error": f"Could not load artifact: {video_filename}",
                    }
                if video_part.inline_data and video_part.inline_data.data:
                    # Extract bytes from the Part object
                    video_bytes = video_part.inline_data.data

                    # Save locally for ffmpeg processing
                    local_path = os.path.join(temp_dir, f"video_{idx}.mp4")
                    with open(local_path, "wb") as f:
                        f.write(video_bytes)
                    local_video_paths.append(local_path)

            # Create output filename
            if concept_name:
                output_filename = f"{concept_name}.mp4"
            else:
                output_filename = f"{uuid.uuid4()}.mp4"

            output_path = os.path.join(temp_dir, output_filename)

            if len(local_video_paths) == 1:
                # If only one video, just copy it
                subprocess.run(["cp", local_video_paths[0], output_path], check=True)
            else:
                # Create ffmpeg filter complex for concatenation with transitions
                # Simple concatenation without transitions
                concat_file = os.path.join(temp_dir, "concat_list.txt")
                with open(concat_file, "w") as f:
                    for video_path in local_video_paths:
                        f.write(f"file '{video_path}'\n")

                subprocess.run(
                    [
                        "ffmpeg",
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        concat_file,
                        "-c",
                        "copy",
                        output_path,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )

            # Read the output video
            with open(output_path, "rb") as f:
                video_bytes = f.read()

            # Save as artifact
            await tool_context.save_artifact(
                output_filename,
                types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
            )

            return {
                "status": "ok",
                "video_filename": output_filename,
                "num_videos_concatenated": len(video_filenames),
            }

    except subprocess.CalledProcessError as e:
        return {
            "status": "failed",
            "error": f"FFmpeg error: {e.stderr if hasattr(e, 'stderr') else str(e)}",
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}
