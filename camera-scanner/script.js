navigator.mediaDevices.getUserMedia({ video: true })
  .then(stream => {
    const video = document.getElementById('video');
    video.srcObject = stream;
    video.play();
  })
  .catch(err => console.error('Error accessing camera:', err));

const snapBtn = document.getElementById('snap');

snapBtn.onclick = () => {
  const canvas = document.getElementById('canvas');
  const video = document.getElementById('video');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0);

  const dataURL = canvas.toDataURL('image/png');
  fetch('/save-image', {
    method: 'POST',
    body: JSON.stringify({ image: dataURL }),
    headers: { 'Content-Type': 'application/json' }
  })
  .then(resp => resp.json())
  .then(data => console.log('Saved', data))
  .catch(err => console.error('Error saving image:', err));
};
