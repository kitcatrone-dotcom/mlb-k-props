import { contextBridge } from "electron";

// The backend always listens locally on a fixed port (see
// backend/app/config.py); exposing it this way keeps renderer code from
// needing direct Node/Electron API access (nodeIntegration stays off).
contextBridge.exposeInMainWorld("aiDjEditStudio", {
  backendBaseUrl: "http://127.0.0.1:8742",
});
