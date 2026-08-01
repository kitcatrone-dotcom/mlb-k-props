import { app, BrowserWindow, shell } from "electron";
import { spawn, ChildProcessWithoutNullStreams } from "child_process";
import path from "path";

// In development, the backend is started separately by the root `npm run
// dev` script (`uvicorn app.main:app --reload`), so Electron doesn't manage
// its lifecycle — this just points the window at the Vite dev server.
const isDev = !!process.env.VITE_DEV_SERVER_URL;

let backendProcess: ChildProcessWithoutNullStreams | null = null;
let mainWindow: BrowserWindow | null = null;

function startBackend(): void {
  if (isDev) return;

  // Packaged build: spawn the bundled backend (see the `extraResources`
  // entry in package.json's electron-builder config) as a local sidecar.
  // This assumes a Python interpreter with the backend's dependencies
  // available — see ARCHITECTURE.md's packaging phase for baking a fully
  // self-contained PyInstaller binary instead of relying on system Python.
  const backendDir = path.join(process.resourcesPath, "backend");
  const pythonBin = process.platform === "win32" ? "python" : "python3";

  backendProcess = spawn(pythonBin, ["-m", "uvicorn", "app.main:app", "--port", "8742"], {
    cwd: backendDir,
    env: process.env,
  });

  backendProcess.stdout?.on("data", (chunk) => console.log(`[backend] ${chunk}`));
  backendProcess.stderr?.on("data", (chunk) => console.error(`[backend] ${chunk}`));
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1120,
    minHeight: 720,
    backgroundColor: "#0d0d12",
    title: "AI DJ Edit Studio",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  if (isDev) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL as string);
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }
}

app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  backendProcess?.kill();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  backendProcess?.kill();
});
