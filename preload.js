// preload.js (����������)
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  // ���ڿ���
  closeWindow: () => ipcRenderer.send('close-window'),
  minimizeWindow: () => ipcRenderer.send('minimize-window'),
  toggleMaximizeWindow: () => ipcRenderer.send('toggle-maximize-window'),
  
  // �ɿ��ļ��������
  writeToClipboard: (text) => ipcRenderer.send('clipboard:write', text),
  readFromClipboard: () => ipcRenderer.invoke('clipboard:read'),
  writeImageToClipboard: (buffer) => ipcRenderer.send('clipboard:write-image', buffer),
});