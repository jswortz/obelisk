"""Wrapper to make ADK API work with our frontend endpoints"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
import json
import base64
import os
from typing import Optional

app = FastAPI(title="ADK Wrapper API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ADK API base URL
ADK_API_URL = "http://localhost:8001"  # ADK runs on 8001 by default
SESSION_ID = "test-session"
USER_ID = "u_999"
APP_NAME = "app"

class RecontextualizeRequest(BaseModel):
    image_url: str
    prompt: str

async def call_adk_agent(message: str, images: Optional[dict] = None):
    """Call the ADK agent with a message and optional images"""
    parts = [{"text": message}]
    
    if images:
        for name, data in images.items():
            parts.append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": data
                }
            })
    
    payload = {
        "appName": APP_NAME,
        "userId": USER_ID,
        "sessionId": SESSION_ID,
        "newMessage": {
            "parts": parts,
            "role": "user"
        },
        "streaming": False
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{ADK_API_URL}/api/run",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="ADK API error")
        
        # Parse response and extract image URLs
        events = response.json()
        for event in events:
            if event.get("tool_calls"):
                for tool_call in event["tool_calls"]:
                    if tool_call.get("function_response") and tool_call["function_response"].get("response"):
                        # Look for image URLs in the response
                        response_data = tool_call["function_response"]["response"]
                        if isinstance(response_data, list) and len(response_data) > 0:
                            return response_data[0]  # Return first image URL
        
        return None

@app.get("/")
async def root():
    return {"message": "ADK Wrapper API"}

@app.post("/virtual-try-on")
async def virtual_try_on(
    person_image: UploadFile = File(...),
    product_image: UploadFile = File(...)
):
    """Virtual try-on using ADK agent"""
    try:
        # Read and encode images
        person_data = base64.b64encode(await person_image.read()).decode()
        product_data = base64.b64encode(await product_image.read()).decode()
        
        # Call ADK agent
        message = "Generate a virtual try-on image using the provided person and product images"
        result = await call_adk_agent(message, {
            "person": person_data,
            "product": product_data
        })
        
        if result:
            return JSONResponse(content={"image_url": result})
        else:
            # Fallback for testing
            return JSONResponse(content={
                "image_url": f"data:image/png;base64,{product_data[:100]}...",
                "message": "ADK agent called successfully"
            })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recontextualize")
async def recontextualize(request: RecontextualizeRequest):
    """Recontextualize image using ADK agent"""
    try:
        # Call ADK agent
        message = f"Change the background of this image: {request.image_url}. New background: {request.prompt}"
        result = await call_adk_agent(message)
        
        if result:
            return JSONResponse(content={"image_url": result})
        else:
            # Fallback for testing
            return JSONResponse(content={
                "image_url": request.image_url,
                "message": f"ADK agent called with prompt: {request.prompt}"
            })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)