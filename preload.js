// preload.js (最终完整版)
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  // 窗口控制
  closeWindow: () => ipcRenderer.send('close-window'),
  minimizeWindow: () => ipcRenderer.send('minimize-window'),
  toggleMaximizeWindow: () => ipcRenderer.send('toggle-maximize-window'),
  
  // 可靠的剪贴板操作
  writeToClipboard: (text) => ipcRenderer.send('clipboard:write', text),
  readFromClipboard: () => ipcRenderer.invoke('clipboard:read'),
  writeImageToClipboard: (buffer) => ipcRenderer.send('clipboard:write-image', buffer),
});