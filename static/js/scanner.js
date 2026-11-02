/**
 * Aircraft Maintenance Scanner - QR Scanner Engine
 * Integrates html5-qrcode with Flask backend lookup API
 */

let html5QrCode = null;
let isScanning = false;

document.addEventListener("DOMContentLoaded", () => {
  const startBtn = document.getElementById("startScanBtn");
  const stopBtn = document.getElementById("stopScanBtn");
  const cameraSelect = document.getElementById("cameraSelect");
  const scanStatus = document.getElementById("scanStatus");
  const scanFeedback = document.getElementById("scanFeedback");
  const manualForm = document.getElementById("manualLookupForm");
  const manualInput = document.getElementById("manualComponentId");
  const scannerOverlay = document.getElementById("scannerOverlay");

  // Populate available cameras
  if (window.Html5Qrcode) {
    Html5Qrcode.getCameras().then(devices => {
      if (devices && devices.length) {
        cameraSelect.innerHTML = "";
        devices.forEach((device, index) => {
          const option = document.createElement("option");
          option.value = device.id;
          option.text = device.label || `Camera ${index + 1}`;
          cameraSelect.appendChild(option);
        });
      } else {
        cameraSelect.innerHTML = `<option value="">No cameras detected</option>`;
      }
    }).catch(err => {
      console.warn("Camera enumeration error:", err);
      cameraSelect.innerHTML = `<option value="">Default Environment Camera</option>`;
    });
  }

  // Start Scanner
  if (startBtn) {
    startBtn.addEventListener("click", () => {
      startScanner();
    });
  }

  // Stop Scanner
  if (stopBtn) {
    stopBtn.addEventListener("click", () => {
      stopScanner();
    });
  }

  // Manual Form Submission
  if (manualForm) {
    manualForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const compId = manualInput.value.trim().toUpperCase();
      if (!compId) return;
      performLookup(compId);
    });
  }

  function updateStatus(message, type = "info") {
    if (!scanStatus) return;
    scanStatus.textContent = message;
    scanStatus.className = `status-text status-${type}`;
  }

  function showFeedback(message, type = "success") {
    if (!scanFeedback) return;
    scanFeedback.style.display = "block";
    scanFeedback.className = `alert alert-${type}`;
    scanFeedback.innerHTML = `<span>${message}</span>`;
  }

  function hideFeedback() {
    if (scanFeedback) scanFeedback.style.display = "none";
  }

  async function startScanner() {
    if (isScanning) return;
    hideFeedback();
    updateStatus("Requesting camera access...", "info");

    try {
      html5QrCode = new Html5Qrcode("qr-reader");

      const cameraId = cameraSelect.value ? { deviceId: { exact: cameraSelect.value } } : { facingMode: "environment" };

      const qrCodeSuccessCallback = (decodedText, decodedResult) => {
        // Successful decode
        console.log("Decoded QR:", decodedText);
        handleSuccessfulScan(decodedText.trim());
      };

      const config = {
        fps: 10,
        qrbox: { width: 220, height: 220 },
        aspectRatio: 1.0
      };

      await html5QrCode.start(
        cameraId,
        config,
        qrCodeSuccessCallback,
        (errorMessage) => {
          // Standard frame read without QR - no need to log
        }
      );

      isScanning = true;
      startBtn.style.display = "none";
      stopBtn.style.display = "inline-flex";
      if (scannerOverlay) scannerOverlay.style.display = "flex";
      updateStatus("Camera active. Point your camera at a component QR code.", "success");

    } catch (err) {
      console.error("Camera start failure:", err);
      let errorMsg = "Could not activate camera. ";

      if (err.name === "NotAllowedError" || err.message.includes("Permission")) {
        errorMsg += "Camera permission was denied. Please allow camera permissions in your browser address bar.";
      } else if (err.name === "NotFoundError" || err.message.includes("device")) {
        errorMsg += "No camera device was found on this system. You can use the manual lookup fallback below.";
      } else {
        errorMsg += "Make sure you are on localhost or HTTPS, or use the manual ID lookup below.";
      }

      showFeedback(errorMsg, "danger");
      updateStatus("Camera offline. Use manual lookup below.", "danger");
      isScanning = false;
    }
  }

  async function stopScanner() {
    if (!html5QrCode || !isScanning) return;
    try {
      await html5QrCode.stop();
      html5QrCode.clear();
    } catch (err) {
      console.warn("Stop scanner error:", err);
    } finally {
      isScanning = false;
      startBtn.style.display = "inline-flex";
      stopBtn.style.display = "none";
      if (scannerOverlay) scannerOverlay.style.display = "none";
      updateStatus("Camera stopped.", "info");
    }
  }

  async function handleSuccessfulScan(qrData) {
    // Prevent duplicate rapid triggers
    if (!isScanning) return;
    
    // Play subtle audio tone if supported
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.frequency.setValueAtTime(880, audioCtx.currentTime); // A5 note
      gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.15);
    } catch(e) {}

    // Temporary stop or pause camera while looking up
    stopScanner();
    performLookup(qrData);
  }

  async function performLookup(aircraftIdentifier) {
    updateStatus(`Looking up aircraft ${aircraftIdentifier}...`, "info");
    showFeedback(`Verifying aircraft <strong>${aircraftIdentifier}</strong> in digital fleet records...`, "info");

    try {
      const response = await fetch(`/api/lookup/${encodeURIComponent(aircraftIdentifier)}`);
      const data = await response.json();

      if (response.ok && data.success) {
        showFeedback(`<strong>Identified:</strong> ${data.component_name} &bull; Status: ${data.latest_status}. Opening maintenance history...`, "success");
        setTimeout(() => {
          window.location.href = data.redirect_url;
        }, 700);
      } else {
        showFeedback(`<strong>Aircraft Not Found:</strong> ${data.message || `No fleet record for ${aircraftIdentifier}`}. <br><a href="/aircraft/new" class="btn btn-secondary btn-sm" style="margin-top: 8px;">Register New Aircraft</a>`, "danger");
        updateStatus("Aircraft lookup failed.", "danger");
      }
    } catch (err) {
      console.error("Lookup network error:", err);
      showFeedback(`Lookup failed: Connection error contacting maintenance server.`, "danger");
      updateStatus("Network error.", "danger");
    }
  }

  // Quick-test demo buttons
  const demoButtons = document.querySelectorAll(".btn-quick-test");
  demoButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const cid = btn.getAttribute("data-id");
      if (manualInput) manualInput.value = cid;
      performLookup(cid);
    });
  });
});
