import cv2
import numpy as np
from PIL import Image
import io
import base64
from typing import Optional, Tuple, List

def decode_base64_image(base64_string: str) -> np.ndarray:
    """Decode base64 string to OpenCV image"""
    # Remove data URL prefix if present
    if ',' in base64_string:
        base64_string = base64_string.split(',')[1]
    
    # Decode base64
    img_bytes = base64.b64decode(base64_string)
    
    # Convert to numpy array
    nparr = np.frombuffer(img_bytes, np.uint8)
    
    # Decode image
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def encode_image_to_base64(image: np.ndarray, quality: int = 95) -> str:
    """Encode OpenCV image to base64 string"""
    # Encode image to JPEG
    _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    
    # Convert to base64
    base64_bytes = base64.b64encode(buffer)
    base64_string = base64_bytes.decode('utf-8')
    
    # Add data URL prefix
    return f"data:image/jpeg;base64,{base64_string}"

def order_points(pts: np.ndarray) -> np.ndarray:
    """Order points in clockwise order: top-left, top-right, bottom-right, bottom-left"""
    rect = np.zeros((4, 2), dtype="float32")
    
    # Sum and diff of points
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    
    # Top-left has smallest sum, bottom-right has largest sum
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    # Top-right has smallest diff, bottom-left has largest diff
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect

def detect_document(image: np.ndarray) -> Optional[np.ndarray]:
    """Detect document edges and return corner points"""
    # Get image dimensions
    height, width = image.shape[:2]
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Edge detection with auto-threshold
    v = np.median(blurred)
    lower = int(max(0, (1.0 - 0.33) * v))
    upper = int(min(255, (1.0 + 0.33) * v))
    edges = cv2.Canny(blurred, lower, upper)
    
    # Dilate edges to close gaps
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Sort contours by area (largest first)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    # Find the largest rectangular contour
    for contour in contours[:5]:  # Check top 5 largest contours
        # Approximate polygon
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        
        # Check if it's a quadrilateral
        if len(approx) == 4:
            # Check if area is significant (at least 20% of image)
            area = cv2.contourArea(approx)
            if area > (width * height * 0.2):
                # Reshape and return corners
                return approx.reshape(4, 2)
    
    return None

def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Apply perspective transform to get top-down view"""
    # Order points
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    
    # Calculate width of new image
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    
    # Calculate height of new image
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    
    # Destination points for transform
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")
    
    # Calculate perspective transform matrix
    M = cv2.getPerspectiveTransform(rect, dst)
    
    # Apply transform
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    
    return warped

def enhance_document(image: np.ndarray, doc_type: str = 'mixed') -> np.ndarray:
    """Enhance document for better readability"""
    enhanced = image.copy()
    
    if doc_type == 'text':
        # Convert to grayscale for text documents
        if len(enhanced.shape) == 3:
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive threshold for text
        enhanced = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 21, 10
        )
        
        # Convert back to BGR for consistency
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        
    else:  # 'mixed' or 'photo'
        # Enhance contrast and brightness
        lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Merge channels
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        # Slight sharpening
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        enhanced = cv2.filter2D(enhanced, -1, kernel)
        
        # Ensure values are in valid range
        enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)
    
    return enhanced

def auto_rotate(image: np.ndarray) -> np.ndarray:
    """Detect and correct image rotation"""
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Detect edges
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Detect lines using Hough transform
    lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
    
    if lines is not None:
        # Calculate angles of detected lines
        angles = []
        for rho, theta in lines[:, 0]:
            angle = np.degrees(theta) - 90
            angles.append(angle)
        
        # Find median angle
        median_angle = np.median(angles)
        
        # Only rotate if angle is significant but small (likely skew)
        if 0.5 < abs(median_angle) < 10:
            # Get image center
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            
            # Rotate image
            M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h), 
                                   flags=cv2.INTER_CUBIC,
                                   borderMode=cv2.BORDER_REPLICATE)
            return rotated
    
    return image

def process_document_image(base64_image: str, 
                         enhance: bool = True,
                         doc_type: str = 'mixed',
                         auto_crop: bool = True,
                         auto_rotate_enabled: bool = True) -> str:
    """
    Main processing pipeline for document images
    
    Args:
        base64_image: Base64 encoded image string
        enhance: Whether to apply enhancement
        doc_type: Type of document ('text', 'mixed', 'photo')
        auto_crop: Whether to detect and crop to document
        auto_rotate_enabled: Whether to auto-rotate skewed images
    
    Returns:
        Base64 encoded processed image
    """
    try:
        # Decode image
        image = decode_base64_image(base64_image)
        
        if image is None:
            print("Failed to decode image")
            return base64_image
        
        # Auto-rotate if enabled
        if auto_rotate_enabled:
            image = auto_rotate(image)
        
        # Detect and crop document if enabled
        if auto_crop:
            corners = detect_document(image)
            if corners is not None:
                print(f"Document detected, cropping...")
                image = four_point_transform(image, corners)
            else:
                print("No document detected, processing full image")
        
        # Enhance image if enabled
        if enhance:
            print(f"Enhancing image as {doc_type} document")
            image = enhance_document(image, doc_type)
        
        # Encode and return
        return encode_image_to_base64(image)
        
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return original image if processing fails
        return base64_image

def process_pil_image(pil_image: Image.Image, **kwargs) -> Image.Image:
    """Process a PIL Image object"""
    # Convert PIL to base64
    buffered = io.BytesIO()
    pil_image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    base64_image = f"data:image/jpeg;base64,{img_str}"
    
    # Process
    processed_base64 = process_document_image(base64_image, **kwargs)
    
    # Convert back to PIL
    img_data = base64.b64decode(processed_base64.split(',')[1])
    return Image.open(io.BytesIO(img_data))

# Optional: Batch processing function
def process_multiple_pages(pages: List[str], **kwargs) -> List[str]:
    """Process multiple pages with same settings"""
    processed_pages = []
    for i, page in enumerate(pages):
        print(f"Processing page {i + 1} of {len(pages)}...")
        processed = process_document_image(page, **kwargs)
        processed_pages.append(processed)
    return processed_pages
