"""Mock API for testing the frontend without Google Cloud credentials"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import tempfile
import shutil
from typing import Optional

app = FastAPI(title="Obelisk Virtual Try-On Mock API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a directory for serving images
os.makedirs("uploads", exist_ok=True)

# Mount static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

class RecontextualizeRequest(BaseModel):
    image_url: str
    prompt: str

@app.get("/")
async def root():
    return {"message": "Obelisk Virtual Try-On Mock API"}

@app.get("/api")
async def api_root():
    return {"message": "Obelisk Virtual Try-On Mock API"}

@app.post("/virtual-try-on")
async def virtual_try_on(
    person_image: UploadFile = File(...),
    product_image: UploadFile = File(...)
):
    print(f"Received request with person_image: {person_image.filename}, product_image: {product_image.filename}")
    """Mock virtual try-on - returns the product image as a placeholder"""
    try:
        # Save product image and return it as the "result"
        filename = f"vto_{product_image.filename}"
        file_path = os.path.join("uploads", filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(product_image.file, buffer)
        
        # In a real implementation, this would call the AI model
        return JSONResponse(content={
            "image_url": f"http://localhost:8000/uploads/{filename}",
            "message": "Mock virtual try-on result (showing product image)"
        })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recontextualize")
async def recontextualize(request: RecontextualizeRequest):
    """Mock recontextualization - returns the original image"""
    try:
        # In a real implementation, this would call the AI model
        return JSONResponse(content={
            "image_url": request.image_url,
            "message": f"Mock recontextualized with prompt: {request.prompt}"
        })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)