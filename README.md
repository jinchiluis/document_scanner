# Document Scanner

Simple web-based document scanner that captures images from your device camera and saves them to a local folder using a small FastAPI backend.

## Folder Structure

```
camera-scanner/
├── index.html        # Frontend UI
├── script.js         # Camera access and capture logic
├── styles.css        # Basic styles
└── backend/
    ├── server.py     # FastAPI backend server
    └── saved_docs/   # Folder where images are stored
```

## Running

1. Install dependencies (preferably in a virtual environment):
   ```bash
   pip install fastapi uvicorn
   ```

2. Start the backend server from the `camera-scanner/backend` directory:
   ```bash
   uvicorn server:app --reload
   ```
   The server will run on `http://localhost:8000/` by default.

3. Open the same URL in your desktop or phone browser connected to the same network. Grant camera permissions and start capturing documents. Each capture is saved in the `saved_docs` directory.

