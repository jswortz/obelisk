from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import tempfile
from typing import Optional
from .agent import ObeliskRecontextAgent

app = FastAPI(title="Obelisk Virtual Try-On API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agent will be initialized on first use
agent = None

def get_agent():
    global agent
    if agent is None:
        agent = ObeliskRecontextAgent(
            project_id=os.environ.get("GOOGLE_CLOUD_PROJECT"),
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
            gcs_bucket=os.environ.get("BUCKET"),
        )
    return agent

class RecontextualizeRequest(BaseModel):
    image_url: str
    prompt: str

@app.get("/")
async def root():
    return {"message": "Obelisk Virtual Try-On API"}

@app.post("/api/virtual-try-on")
async def virtual_try_on(
    person_image: UploadFile = File(...),
    product_image: UploadFile = File(...)
):
    """Generate a virtual try-on image"""
    try:
        # Save uploaded files temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as person_tmp:
            person_tmp.write(await person_image.read())
            person_path = person_tmp.name
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as product_tmp:
            product_tmp.write(await product_image.read())
            product_path = product_tmp.name
        
        # Generate virtual try-on
        result = get_agent().generate_virtual_try_on_images(
            person_image_path=person_path,
            product_image_path=product_path,
            number_of_images=1
        )
        
        # Clean up temp files
        os.unlink(person_path)
        os.unlink(product_path)
        
        if result and len(result) > 0:
            return JSONResponse(content={"image_url": result[0]})
        else:
            raise HTTPException(status_code=500, detail="Failed to generate virtual try-on")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recontextualize")
async def recontextualize(request: RecontextualizeRequest):
    """Recontextualize image background"""
    try:
        # Download image from URL or use local path
        result = get_agent().recontext_image_background(
            image_path=request.image_url,
            prompt=request.prompt,
            number_of_images=1
        )
        
        if result and len(result) > 0:
            return JSONResponse(content={"image_url": result[0]})
        else:
            raise HTTPException(status_code=500, detail="Failed to recontextualize image")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)