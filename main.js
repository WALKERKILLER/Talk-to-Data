// main.js (最终回归版 - 确保 npm start 可用)
const { app, BrowserWindow, ipcMain, shell, clipboard } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let pyProc = null;
let mainWindow = null;

// isDev 的判断方式保持不变
const isDev = !app.isPackaged;
const isWindows = process.platform === 'win32';

function createPyProc() {
    let scriptPath = path.join(__dirname, 'app.py');
    let executable = 'python';

    // 如果是打包后的生产环境
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

    // 在开发模式下，我们直接用'python'和脚本路径
    // 在生产模式下，我们直接运行可执行文件，不再需要脚本路径作为参数
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
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    titleBarOverlay: isWindows ? { color: 'rgba(0, 0, 0, 0)', symbolColor: '#74b1be', height: 40 } : undefined
  });

  if (process.platform === 'darwin') {
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

// IPC 事件监听保持不变
ipcMain.on('close-window', () => mainWindow?.close());
ipcMain.on('minimize-window', () => mainWindow?.minimize());
ipcMain.on('toggle-maximize-window', () => { if (mainWindow?.isMaximized()) mainWindow.restore(); else mainWindow.maximize(); });
ipcMain.on('clipboard:write', (event, text) => clipboard.writeText(text));
ipcMain.handle('clipboard:read', async () => clipboard.readText());