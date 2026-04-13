let mediaRecorder;
let audioChunks = [];

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.target !== "offscreen") {
    return true;
  }

  switch (request.command) {
    case "startRecording":
      startRecording(request.tabId)
        .then(() => sendResponse({ success: true }))
        .catch((err) => sendResponse({ success: false, error: err.message }));
      break;
    case "stopRecording":
      stopRecording();
      sendResponse({ success: true });
      break;
  }
  return true;
});

async function startRecording(tabId) {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    throw new Error("Recording is already in progress.");
  }

  console.log("Begin capturing...");
  const stream = await chrome.tabCapture.capture({
    audio: true,
    video: false,
  });
  console.log("Stream...");

  const audioContext = new AudioContext();
  const streamSource = audioContext.createMediaStreamSource(stream);

  mediaRecorder = new MediaRecorder(streamSource.stream);

  mediaRecorder.ondataavailable = (event) => {
    audioChunks.push(event.data);
  };

  mediaRecorder.onstop = () => {
    const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
    sendAudioToServer(audioBlob);
    audioChunks = [];
    stream.getTracks().forEach((track) => track.stop());
    audioContext.close();
  };

  mediaRecorder.start();
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
  }
}

function sendAudioToServer(audioBlob) {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");

  fetch("YOUR_SERVER_ENDPOINT", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => console.log("Server response:", data))
    .catch((error) => console.error("Error sending audio:", error));
}
