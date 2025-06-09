from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import base64
from datetime import datetime
from pathlib import Path

app = FastAPI()

# Serve frontend files
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent, html=True), name="static")

SAVE_DIR = Path(__file__).resolve().parent / "saved_docs"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/save-image")
async def save_image(req: Request):
    data = await req.json()
    img_data = data['image'].split(',')[1]
    img_bytes = base64.b64decode(img_data)
    filename = SAVE_DIR / f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    with open(filename, 'wb') as f:
        f.write(img_bytes)
    return {"status": "saved", "file": str(filename)}
