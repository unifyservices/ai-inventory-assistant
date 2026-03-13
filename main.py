import os
import uuid
import shutil
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import config
from inventory.ai_agent import InventoryAgent

app = FastAPI(title="AI Inventory Assistant")
agent = InventoryAgent()

# Ensure data directory exists
os.makedirs(config.DATA_DIR, exist_ok=True)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    filename: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send a message to the inventory assistant."""
    session_id = req.session_id or str(uuid.uuid4())

    # Find the Excel file
    if req.filename:
        filepath = os.path.join(config.DATA_DIR, req.filename)
    else:
        # Use the first available file
        files = [f for f in os.listdir(config.DATA_DIR) if f.endswith((".xlsx", ".xls"))]
        if not files:
            return ChatResponse(
                reply="No Excel file loaded yet. Please upload an inventory file first.",
                session_id=session_id,
            )
        filepath = os.path.join(config.DATA_DIR, files[0])

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"File '{req.filename}' not found.")

    try:
        reply = agent.chat(session_id, req.message, filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(reply=reply, session_id=session_id)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload an Excel file."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xls files are supported.")

    filepath = os.path.join(config.DATA_DIR, file.filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Clear cached data for this file
    agent.reload_file(filepath)

    return {"filename": file.filename, "message": "File uploaded successfully."}


@app.get("/files")
async def list_files():
    """List available Excel files."""
    files = [f for f in os.listdir(config.DATA_DIR) if f.endswith((".xlsx", ".xls"))]
    return {"files": files}


# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
