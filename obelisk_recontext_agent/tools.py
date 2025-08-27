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
from google.genai.types import GenerateVideosConfig, RecontextImageConfig, Image
from google.genai.types import (
    RawReferenceImage,
    MaskReferenceImage,
    MaskReferenceConfig,
    EditImageConfig,
)


client = genai.Client()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "gcp-obelisk-dev")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")


async def edit_image(prompt: str, tool_context: ToolContext):
    """Recontextualizes an image by changing its background.

    Args:
        image_selection (int): The index (zero-based)of the image to edit
        prompt (str): The prompt describing the new background.
        tool_context (ToolContext): The tool context.
    """
    client = genai.Client(
        vertexai=True,
        project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        location="global",
    )
    try:
        image_location = tool_context.state["selected_file"]
    except:
        return {
            "status": "error",
            "message": "select the file for editing first using the file selection tool",
        }
    bucket = os.environ.get("BUCKET", "default").split("gs://")[1]
    logging.info(f"Selected bucket: {bucket}")
    blob_name = image_location.split("/")[3]  # gs://bucket-name/blob
    logging.info(f"Selected blob: {blob_name}")
    image_to_edit = download_blob(bucket_name=bucket, source_blob_name=blob_name)
    image_part = types.Part.from_bytes(data=image_to_edit, mime_type="image/png")
    edit_contents = [
        types.Content(
            role="user", parts=[image_part, types.Part.from_text(text=prompt)]
        )
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        max_output_tokens=8192,
        response_modalities=["TEXT", "IMAGE"],
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash-image-preview",
        contents=edit_contents,
        config=generate_content_config,
    )
    logging.info(f"Received response from the model.")
    filenames = []
    if (
        response
        and response.candidates
        and response.candidates[0].content
        and response.candidates[0].content.parts
    ):
        image_parts = [
            part for part in response.candidates[0].content.parts if part.inline_data
        ]
        logging.info(f"Successfully generated {len(image_parts)} image(s).")
        for part in image_parts:
            if part.inline_data and part.inline_data.data:
                generated_image_bytes = part.inline_data.data
                filename = f"{uuid.uuid4()}.png"
                logging.info(f"Saving generated image as artifact: {filename}")
                filenames.append(filename)
                await tool_context.save_artifact(
                    filename,
                    types.Part.from_bytes(
                        data=generated_image_bytes,
                        mime_type="image/png",
                    ),
                )
                gcs_upload_result = await upload_file_to_gcs(
                    file_path=filename,
                    tool_context=tool_context,
                    state_var_name="recontextualized_image_gcs_uri",
                )
                # save the last edited image for continuity
                tool_context.state["selected_file"] = gcs_upload_result["gcs_uri"]
                logging.info(f"Successfully saved artifact '{filename}'.")
            else:
                logging.warning(f"Skipping an empty part in the response.")
        return {
            "status": "complete",
            "image_filenames": filenames,
        }


async def upload_file_to_gcs(
    file_path: str,
    tool_context: ToolContext,
    state_var_name: str,
) -> dict[str, str]:
    """
    Uploads a file to a GCS bucket.
    Args:
        file_path (str): The path to the file to upload.
        tool_context (ToolContext): The tool context.
        state_var_name (str): The name of the state variable to store the GCS URI.

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
        if not tool_context.state.get(state_var_name, False):
            tool_context.state[state_var_name] = []
        tool_context.state[state_var_name].append(f"gs://{bucket_name}/{file_path}")

        return {
            "status": "ok",
            "gcs_uri": f"gs://{bucket_name}/{file_path}",
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


def file_selector(state_variable: str, index: int, tool_context: ToolContext):
    """
    Selects a file from a state variable by index.

    Args:
        state_variable (str): The name of the state variable containing the list of files.
        index (int): The zero-based index of the file to select.
        tool_context (ToolContext): The tool context.

    Returns:
        dict: A dictionary containing the status and the selected file, or an error message.
    """
    try:
        selected_file = tool_context.state[state_variable][index]
        tool_context.state["selected_file"] = selected_file
        return {"status": "ok", "selected_file": selected_file}
    except KeyError:
        return {"status": "error", "error": "State variable not found"}
    except IndexError:
        return {"status": "error", "error": "Index out of range"}


async def generate_video(
    prompt: str,
    tool_context: ToolContext,
    number_of_videos: int,
    # aspect_ratio: str = "16:9",
    negative_prompt: str,
):
    f"""Generates a video based on the prompt for VEO3.

    Args:
        prompt (str): The prompt to generate the video from.
        tool_context (ToolContext): The tool context.
        number_of_videos (int, optional): The number of videos to generate.
        negative_prompt (str, optional): The negative prompt to use. 
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
    try:
        existing_image_gcs_uri = tool_context.state["selected_file"]
    except KeyError:
        return {
            "status": "error",
            "error": "State variable not found, be sure the file_selector tool was run",
        }

    existing_image = types.Image(gcs_uri=existing_image_gcs_uri, mime_type="image/png")
    operation = client.models.generate_videos(
        model="veo-3.0-generate-preview",
        prompt=prompt,
        image=existing_image,
        config=gen_config,
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


async def generate_virtual_try_on_images(
    person_uri: str,
    product_uri: str,
    number_of_images: int,
    tool_context: ToolContext,
):
    """Generates a virtual try-on image from a person and product image.

    Args:
        person_uri (str): The URI for the person's image. This could be a gs:// location or a local artifact uri.
        product_uri (str): The URI for the product image. This could be a gs:// location or a local artifact uri.
        number_of_images (int): The number of images to generate.
        tool_context (ToolContext): The tool context.

    Returns:
        dict: The JSON response with status and generated image filename.
    """
    logging.info(
        f"Starting virtual try-on generation with person_uri: {person_uri} and product_uri: {product_uri}"
    )
    try:
        # Load person artifact
        logging.info(f"Loading person artifact: {person_uri}")
        # check if the person uri is a gcs one
        if person_uri.startswith("gs://"):
            person_gcs_uri = person_uri
        else:
            person_upload_result = await upload_file_to_gcs(
                file_path=person_uri,
                tool_context=tool_context,
                state_var_name="person_gcs_uri",
            )
            person_gcs_uri = person_upload_result["gcs_uri"]
        logging.info(f"Loading product artifact: {product_uri}")
        if product_uri.startswith("gs://"):
            product_gcs_uri = product_uri
        else:
            product_upload_result = await upload_file_to_gcs(
                file_path=product_uri,
                tool_context=tool_context,
                state_var_name="product_gcs_uri",
            )
            product_gcs_uri = product_upload_result["gcs_uri"]
        logging.info("Calling the virtual try-on model 'virtual-try-on-preview-08-04'")
        image = client.models.recontext_image(
            model="virtual-try-on-preview-08-04",
            source=types.RecontextImageSource(
                person_image=Image.from_file(location=f"{person_gcs_uri}"),
                # person_image=person_part,
                product_images=[
                    types.ProductImage(
                        product_image=Image.from_file(location=f"{product_gcs_uri}")
                    )
                ],
            ),
            config=RecontextImageConfig(number_of_images=number_of_images),
        )
        logging.info(f"Received response from the model.")

        filenames = []
        if image and image.generated_images:
            logging.info(
                f"Successfully generated {len(image.generated_images)} image(s)."
            )
            for generated_image in image.generated_images:
                if generated_image.image and generated_image.image.image_bytes:
                    generated_image_bytes = generated_image.image.image_bytes
                    filename = f"{uuid.uuid4()}.png"
                    logging.info(f"Saving generated image as artifact: {filename}")
                    filenames.append(filename)
                    await tool_context.save_artifact(
                        filename,
                        types.Part.from_bytes(
                            data=generated_image_bytes,
                            mime_type="image/png",
                        ),
                    )
                    await upload_file_to_gcs(
                        file_path=filename,
                        tool_context=tool_context,
                        state_var_name="virtual_product_try_on_gcs_uri",
                    )
                    logging.info(f"Successfully saved artifact '{filename}'.")
                else:
                    logging.warning(
                        f"Skipping an empty generated image in the response."
                    )
            return {
                "status": "complete",
                "image_filenames": filenames,
            }
    except Exception as e:
        logging.error(
            f"An unexpected error occurred in generate_virtual_try_on_image: {e}",
            exc_info=True,
        )
        return {"Status": "generation_error", "Error": str(e)}
