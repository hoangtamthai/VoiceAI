let recording = false;
const OFFSCREEN_DOCUMENT_PATH = "offscreen.html";

// A function to create and manage the offscreen document
async function setupOffscreenDocument() {
  const existingContexts = await chrome.runtime.getContexts({
    contextTypes: ["OFFSCREEN_DOCUMENT"],
  });
  if (existingContexts.length > 0) {
    return;
  }
  await chrome.offscreen.createDocument({
    url: OFFSCREEN_DOCUMENT_PATH,
    reasons: ["USER_MEDIA"],
    justification: "Audio recording requires a document context.",
  });
}

// Listener for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.command === "startRecording") {
    console.log("Start recording...");
    handleStartRecording(sendResponse);
  } else if (request.command === "stopRecording") {
    handleStopRecording(sendResponse);
  } else if (request.command === "getRecordingState") {
    sendResponse({ recording });
  }
  return true;
});

async function handleStartRecording(sendResponse) {
  if (recording) {
    sendResponse({ success: false, message: "Already recording." });
    return;
  }

  await setupOffscreenDocument();

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs.length > 0) {
      const tabId = tabs[0].id;
      chrome.runtime.sendMessage(
        {
          command: "startRecording",
          target: "offscreen",
          tabId: tabId,
        },
        (response) => {
          if (response && response.success) {
            recording = true;
            chrome.runtime.sendMessage({
              command: "recordingStateChanged",
              recording: true,
            });
            sendResponse({ success: true });
          } else {
            sendResponse({
              success: false,
              message: response ? response.error : "Unknown error",
            });
          }
        }
      );
    } else {
      sendResponse({ success: false, message: "No active tab found." });
    }
  });
}

async function handleStopRecording(sendResponse) {
  if (!recording) {
    sendResponse({ success: false, message: "Not recording." });
    return;
  }

  chrome.runtime.sendMessage(
    {
      command: "stopRecording",
      target: "offscreen",
    },
    (response) => {
      recording = false;
      chrome.runtime.sendMessage({
        command: "recordingStateChanged",
        recording: false,
      });
      sendResponse({ success: true });
    }
  );
}
