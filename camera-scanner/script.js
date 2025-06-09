// Enhanced script with better error handling and debugging
console.log('Starting camera initialization...');

async function initCamera() {
  try {
    console.log('Requesting camera access...');
    const stream = await navigator.mediaDevices.getUserMedia({ 
      video: { 
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'environment' // Use back camera on mobile
      } 
    });
    
    const video = document.getElementById('video');
    video.srcObject = stream;
    
    // Wait for video to be ready
    video.onloadedmetadata = () => {
      console.log('Video metadata loaded, starting playback...');
      video.play().then(() => {
        console.log('Video is now playing');
      }).catch(err => {
        console.error('Error playing video:', err);
      });
    };
    
    // Debug video dimensions
    video.onloadeddata = () => {
      console.log(`Video dimensions: ${video.videoWidth}x${video.videoHeight}`);
    };
    
  } catch (err) {
    console.error('Error accessing camera:', err);
    
    // Show user-friendly error message
    const video = document.getElementById('video');
    video.style.display = 'none';
    
    const errorDiv = document.createElement('div');
    errorDiv.style.color = 'red';
    errorDiv.style.padding = '20px';
    errorDiv.innerHTML = `
      <h3>Camera Error</h3>
      <p>Error: ${err.message}</p>
      <p>Please check:</p>
      <ul style="text-align: left; display: inline-block;">
        <li>Camera permissions are granted</li>
        <li>No other app is using the camera</li>
        <li>You're using HTTPS (required for camera access)</li>
        <li>Your browser supports camera access</li>
      </ul>
    `;
    video.parentNode.insertBefore(errorDiv, video);
  }
}

// Initialize camera when page loads
initCamera();

// Enhanced capture function
const snapBtn = document.getElementById('snap');
snapBtn.onclick = () => {
  const canvas = document.getElementById('canvas');
  const video = document.getElementById('video');
  
  if (video.videoWidth === 0 || video.videoHeight === 0) {
    alert('Video not ready yet. Please wait for camera to initialize.');
    return;
  }
  
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0);

  const dataURL = canvas.toDataURL('image/png');
  
  // Show preview (optional)
  console.log('Captured image, sending to server...');
  
  fetch('/save-image', {
    method: 'POST',
    body: JSON.stringify({ image: dataURL }),
    headers: { 'Content-Type': 'application/json' }
  })
  .then(resp => {
    if (!resp.ok) {
      throw new Error(`HTTP error! status: ${resp.status}`);
    }
    return resp.json();
  })
  .then(data => {
    console.log('Saved successfully:', data);
    alert('Document captured and saved!');
  })
  .catch(err => {
    console.error('Error saving image:', err);
    alert('Error saving image. Check console for details.');
  });
};
