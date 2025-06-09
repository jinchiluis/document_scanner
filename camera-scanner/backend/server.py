from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import base64
from datetime import datetime
from pathlib import Path
import uvicorn
import ssl
import numpy as np
import cv2
import io
from PIL import Image

app = FastAPI()

# Get the project root directory (parent of backend folder)
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Setup paths
SAVE_DIR = BACKEND_DIR / "saved_docs"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# Serve the HTML file at root
@app.get("/")
async def serve_index():
    index_path = PROJECT_ROOT / "index.html"
    return FileResponse(index_path)

# Serve CSS file
@app.get("/static/styles.css")
async def serve_styles():
    styles_path = PROJECT_ROOT / "styles.css"
    return FileResponse(styles_path)

# Serve JS file
@app.get("/static/script.js")
async def serve_script():
    script_path = PROJECT_ROOT / "script.js"
    return FileResponse(script_path)

def order_points(pts):
    """Order points in clockwise order starting from top-left"""
    rect = np.zeros((4, 2), dtype="float32")
    
    # Top-left point will have the smallest sum
    # Bottom-right point will have the largest sum
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    # Top-right point will have the smallest difference
    # Bottom-left will have the largest difference
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect

def four_point_transform(image, pts):
    """Apply perspective transform to extract document"""
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    
    # Compute width of the new image
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    
    # Compute height of the new image
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    
    # Construct destination points
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")
    
    # Compute perspective transform matrix and apply it
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    
    return warped

def detect_document(image):
    """Detect document edges in the image"""
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply edge detection
    edged = cv2.Canny(blurred, 50, 150)
    
    # Apply morphological operations to close gaps
    kernel = np.ones((5, 5), np.uint8)
    closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Sort contours by area (largest first)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    # Find the document contour
    for contour in contours[:5]:  # Check top 5 largest contours
        # Approximate the contour
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        
        # If we have 4 points, we likely have our document
        if len(approx) == 4:
            # Check if it's large enough (at least 20% of image area)
            area = cv2.contourArea(approx)
            img_area = gray.shape[0] * gray.shape[1]
            if area > img_area * 0.2:
                return approx.reshape(4, 2)
    
    return None

def enhance_document(image):
    """Apply enhancements to make document more readable"""
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Apply adaptive thresholding for better text clarity
    enhanced = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
