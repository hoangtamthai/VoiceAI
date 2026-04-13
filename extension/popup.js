document.addEventListener('DOMContentLoaded', function () {
  const startBtn = document.getElementById('startBtn');
  const stopBtn = document.getElementById('stopBtn');
  const statusDiv = document.getElementById('status');
  const errorDiv = document.getElementById('error');

  // Check the initial recording state
  chrome.runtime.sendMessage({ command: "getRecordingState" }, (response) => {
    if (response && response.recording) {
      setRecordingState();
    } else {
      setIdleState();
    }
  });

  startBtn.addEventListener('click', function () {
    chrome.runtime.sendMessage({ command: "startRecording" }, (response) => {
      if (response && response.success) {
        setRecordingState();
      } else {
        errorDiv.textContent = (response && response.message) || "Error starting recording.";
      }
    });
  });

  stopBtn.addEventListener('click', function () {
    chrome.runtime.sendMessage({ command: "stopRecording" }, (response) => {
      if (response && response.success) {
        setIdleState("Recording stopped.");
      } else {
        errorDiv.textContent = "Error stopping recording.";
      }
    });
  });

  // Listen for recording state changes from the background script
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.command === "recordingStateChanged") {
      if (request.recording) {
        setRecordingState();
      } else {
        setIdleState("Recording stopped.");
      }
    }
  });

  function setRecordingState() {
    startBtn.disabled = true;
    stopBtn.disabled = false;
    statusDiv.textContent = "Recording...";
    errorDiv.textContent = "";
  }

  function setIdleState(message = "Ready to record.") {
    startBtn.disabled = false;
    stopBtn.disabled = true;
    statusDiv.textContent = message;
    errorDiv.textContent = "";
  }
});
