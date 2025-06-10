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
   pip install -r requirements.txt
   ```

2. Generate a self‑signed certificate (required for using the camera on a phone):
   ```bash
   python camera-scanner/backend/generate_cert.py
   ```

3. Start the server from the repository root:
   ```bash
   python camera-scanner/backend/server.py
   ```
   It will run on `https://localhost:8443` if certificates are present or fallback to `http://localhost:8000`.

4. Open the same URL in your desktop or phone browser connected to the same network. Grant camera permissions and start capturing documents. Each capture is saved in the `saved_docs` directory.

