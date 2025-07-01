// main.js
const { app, BrowserWindow, ipcMain, shell, clipboard, nativeImage} = require('electron');
const path = require('path'); 
const { spawn } = require('child_process');
const http = require('http');

let pyProc = null;
let mainWindow = null;

const isDev = !app.isPackaged;
const isWindows = process.platform === 'win32';
const isMac = process.platform === 'darwin';

// 为 Windows 设置 App User Model ID
if (isWindows) {
  app.setAppUserModelId('com.yourcompany.talktodata');
}

// 获取图标路径的辅助函数
function getIconPath() {
    if (isWindows) {
        return path.join(__dirname, 'assets', 'icon.ico');
    }
    if (isMac) {
        return path.join(__dirname, 'assets', 'icon.icns');
    }
    return path.join(__dirname, 'assets', 'icon.png');
}

function createPyProc() {
    let scriptPath = path.join(__dirname, 'app.py');
    let executable = 'python';

    if (!isDev) {
        if (isWindows) {
            executable = path.join(process.resourcesPath, 'app', 'py-backend', 'py-backend.exe');
        } else {
            executable = path.join(process.resourcesPath, 'app', 'py-backend', 'py-backend');
        }
    }

    console.log(`[Electron] Launching Python backend...`);
    console.log(`[Electron] Executable: ${executable}`);
    if(isDev) console.log(`[Electron] Script: ${scriptPath}`);

    pyProc = isDev ? spawn(executable, [scriptPath]) : spawn(executable);

    pyProc.stdout.on('data', (data) => console.log(`[Python] ${data.toString()}`));
    pyProc.stderr.on('data', (data) => console.error(`[Python ERROR] ${data.toString()}`));
    pyProc.on('close', (code) => console.log(`Python process exited with code ${code}`));
}

function checkBackendReady() {
    return new Promise((resolve) => {
        const tryConnect = () => {
            http.get('http://127.0.0.1:5001', (res) => {
                console.log('[Electron] Backend is ready!');
                resolve();
            }).on('error', () => {
                console.log('[Electron] Backend not ready, retrying in 1 second...');
                setTimeout(tryConnect, 1000);
            });
        };
        tryConnect();
    });
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1366,
    height: 840,
    minWidth: 1024,
    minHeight: 768,
    frame: false,
    titleBarStyle: 'hidden',
    icon: getIconPath(),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    titleBarOverlay: isWindows ? { color: 'rgba(0, 0, 0, 0)', symbolColor: '#74b1be', height: 40 } : undefined
  });

  if (isMac) {
    mainWindow.setTrafficLightPosition({ x: 15, y: 15 });
  }

  mainWindow.loadURL('http://127.0.0.1:5001');

  if (isDev) {
    mainWindow.webContents.openDevTools();
  }
  
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

app.on('ready', async () => {
  if (isMac) {
      app.dock.setIcon(getIconPath());
  }

  createPyProc();
  await checkBackendReady();
  createMainWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('will-quit', () => {
  if (pyProc) pyProc.kill();
});

app.on('activate', () => {
  if (mainWindow === null) createMainWindow();
});

ipcMain.on('close-window', () => mainWindow?.close());
ipcMain.on('minimize-window', () => mainWindow?.minimize());
ipcMain.on('toggle-maximize-window', () => { if (mainWindow?.isMaximized()) mainWindow.restore(); else mainWindow.maximize(); });
ipcMain.on('clipboard:write', (event, text) => clipboard.writeText(text));
ipcMain.handle('clipboard:read', async () => clipboard.readText());
ipcMain.on('clipboard:write-image', (event, buffer) => {
    const image = nativeImage.createFromBuffer(buffer);
    clipboard.writeImage(image);
});
