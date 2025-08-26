# Obelisk Virtual Try-On and Recontextualization Agent

<img src="img/maebelle1.png" width=300px/>
<img src="img/75f4cb7b-bbba-4306-b498-9994df85dee4.png" width=300px/>
<img src="img/088045D8-B45D-4B1F-857F-A4C3FD27140E_4_5005_c.jpeg">

This agent first generates a virtual try-on image of a person wearing a product, then recontextualizes the image by changing its background based on a user's prompt.

## Features

- **Virtual Try-On:** The agent's primary function is to generate a realistic image of a person wearing a clothing item.
- **Background Recontextualization:** After the virtual try-on, the agent can replace the background of the generated image with a new scene described by a prompt, using Imagen 3's image editing capabilities.
- **GCS and Local Image Support:** The agent can accept person and product images from either a GCS URI or a local file upload (artifact).
- **Multiple Image Generation:** The agent can generate multiple images in a single request.

## How it Works

The agent follows a two-step process:

1.  **Virtual Try-On:** It uses the `virtual-try-on-preview-08-04` model to generate an image of a person wearing a product. This is handled by the `generate_virtual_try_on_images` tool.
2.  **Background Swap:** It then uses the `imagen-3.0-capability-001` model to edit the background of the virtual try-on image. This is done with the `recontext_image_background` tool, which leverages the background swap mode.

All generated images are saved as artifacts and uploaded to a GCS bucket.

Setup:

```
gsutil cp -r img/*.png $BUCKET/products/
```

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

1.  **First, upload a person image and a product image.**
2.  **Then, generate the virtual try-on image:**
    `"Use the uploaded person and sweater images to generate a virtual try-on image."`
3.  **Finally, recontextualize the background:**
    `"Take the generated image and place the person on top of Mt. Everest."`


# Deployment to Agentspace
![image](img/agentspace-output.png)

Make sure to add the Vertex AI Admin and Service Agent roles to the Service Agent for Reasoning Engine:
`service-YOURPROJECTNUMBER@gcp-sa-aiplatform-re.iam.gserviceaccount.com`

Also make sure the above service account has access to read/write from the `BUCKET` location


Create an Agent Engine using the `deployment_guide.ipynb` notebook

Then note the Agent Engine ID (last numeric portion of the Resource Name). e.g.:

```bash
agent_engine = vertexai.agent_engines.get('projects/679926387543/locations/us-central1/reasoningEngines/1093257605637210112')
```

Update the `agent_config_example.json`, then run:

```bash
./publish_to_agentspace_v2.sh --action create --config agent_config.json
```

Usage: `./publish_to_agentspace_v2.sh [OPTIONS]`

```bash
Options:
  -a, --action <create|update|list|delete>  Action to perform (required)
  -c, --config <file>              JSON configuration file
  -p, --project-id <id>            Google Cloud project ID
  -n, --project-number <number>    Google Cloud project number
  -e, --app-id <id>                Agent Space application ID
  -r, --reasoning-engine <id>      Reasoning Engine ID (required for create/update)
  -d, --display-name <name>        Agent display name (required for create/update)
  -s, --description <desc>         Agent description (required for create)
  -i, --agent-id <id>              Agent ID (required for update/delete)
  -t, --instructions <text>        Agent instructions, use the root agent instructions here (required for create)
  -u, --icon-uri <uri>             Icon URI (optional)
  -l, --location <location>        Agent Space location (default: us)
      --agent-engine-location <location> Agent Engine location (default: us-central1)
  -h, --help                       Display this help message
```

### Example with config file:
```bash
./publish_to_agentspace_v2.sh --action create --config agent_config.json
./publish_to_agentspace_v2.sh --action update --config agent_config.json
./publish_to_agentspace_v2.sh --action list --config agent_config.json
./publish_to_agentspace_v2.sh --action delete --config agent_config.json
```
### Example with command line args:

Create agent:
```bash
./publish_to_agentspace_v2.sh --action create --project-id my-project --project-number 12345 \
--app-id my-app --reasoning-engine 67890 --display-name 'My Agent' \
--description 'Agent description' --instructions 'Agent instructions here'
```
  Update agent:
```bash
./publish_to_agentspace_v2.sh --action update --project-id my-project --project-number 12345 \
--app-id my-app --reasoning-engine 67890 --display-name 'My Agent' \
--agent-id 123456789 --description 'Updated description'
```
  List agents:
```bash
./publish_to_agentspace_v2.sh --action list --project-id my-project --project-number 12345 \
--app-id my-app
```

  Delete agent:
```bash
./publish_to_agentspace_v2.sh --action delete --project-id my-project --project-number 12345 \
--app-id my-app --agent-id 123456789
```
