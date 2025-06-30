// static/script.js
document.addEventListener('DOMContentLoaded', () => {
    // --- ELEMENT HOOKS ---
    const getEl = (id) => document.getElementById(id);
    const ui = {
        analysisForm: getEl('analysis-form'), taskInput: getEl('task-input'), fileInput: getEl('file-input'),
        fileName: getEl('file-name'), submitBtn: getEl('submit-btn'), settingsForm: getEl('settings-form'),
        apiBaseUrl: getEl('api-base-url'), apiKey: getEl('api-key'), modelName: getEl('model-name'),
        saveSettingsBtn: getEl('save-settings-btn'), testConnectionBtn: getEl('test-connection-btn'),
        connectionStatus: getEl('connection-status'), exportBtn: getEl('export-btn'), themeToggle: getEl('theme-toggle'),
        messageContainer: getEl('message-container'), menuToggle: getEl('menu-toggle'), sidebar: getEl('sidebar'),
        overlay: getEl('background-overlay'), progressBadge: getEl('progress-badge'),
        progressCircle: document.querySelector('.progress-circle'), progressPercent: getEl('progress-percent'),
        progressStatusText: getEl('progress-status-text'), minimizeBtn: getEl('minimize-btn'),
        maximizeBtn: getEl('maximize-btn'), closeBtn: getEl('close-btn'), contextMenu: getEl('context-menu'),
        newChatBtn: getEl('new-chat-btn'), newAnalysisSection: getEl('new-analysis-section'), sessionList: getEl('session-list'),
        chatInputContainer: getEl('chat-input-container'), continueChatForm: getEl('continue-chat-form'), chatInput: getEl('chat-input'),
    };
    
    // --- STATE MANAGEMENT ---
    let currentSessionId = null;
    let sessions = {};
    let rightClickedElement = null;
    let currentProgress = { percent: 0, text: '' };

    const icons = {
        system: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M11.07 2.24a.75.75 0 00-1.06-.04l-7.5 7.5a.75.75 0 000 1.06l7.5 7.5a.75.75 0 101.06-1.06l-6.22-6.22H17a.75.75 0 000-1.5H4.81l6.22-6.22a.75.75 0 00.04-1.06z" clip-rule="evenodd" /></svg>`,
        thought: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path d="M10 3.75a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0V4.5A.75.75 0 0110 3.75zM5.992 6.49a.75.75 0 01.363-1.044l3.5-2a.75.75 0 011.044.363l2 3.5a.75.75 0 01-1.044.364l-3.5-2a.75.75 0 01-.363-1.043zM15.044 11.364a.75.75 0 011.044-.364l2-3.5a.75.75 0 01-.363-1.044l-3.5-2a.75.75 0 01-1.044.364l-2 3.5a.75.75 0 01.363 1.044z" /><path fill-rule="evenodd" d="M3 10a7 7 0 1114 0 7 7 0 01-14 0zm7-5a5 5 0 100 10 5 5 0 000-10z" clip-rule="evenodd" /></svg>`,
        action: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M11.78 2.22a.75.75 0 011.06 0l4.25 4.25a.75.75 0 010 1.06l-4.25 4.25a.75.75 0 01-1.06-1.06L14.44 8 2.75 8a.75.75 0 010-1.5l11.69 0-2.67-2.67a.75.75 0 010-1.06z" clip-rule="evenodd" /><path fill-rule="evenodd" d="M2 4a.75.75 0 01.75.75v10.5a.75.75 0 01-1.5 0V4.75A.75.75 0 012 4z" clip-rule="evenodd" /></svg>`,
        observation: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path d="M10 12.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" /><path fill-rule="evenodd" d="M.664 10.59a1.651 1.651 0 010-1.18l.88-3.862A1.651 1.651 0 013.203 4.23l3.862-.88a1.651 1.651 0 011.18 0l3.862.88a1.651 1.651 0 011.658 1.658l.88 3.862a1.651 1.651 0 010 1.18l-.88 3.862a1.651 1.651 0 01-1.658 1.658l-3.862.88a1.651 1.651 0 01-1.18 0l-3.862-.88A1.651 1.651 0 011.544 14.45l-.88-3.862zM10 15a5 5 0 100-10 5 5 0 000 10z" clip-rule="evenodd" /></svg>`,
        final_summary: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-13a.75.75 0 00-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 000-1.5h-3.25V5z" clip-rule="evenodd" /></svg>`,
        evaluation: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10.868 2.884c.321-.772 1.305-.772 1.626 0l.404 1.006c.246.614.878 1.033 1.55.992l1.09-.06c.81-.043 1.28.99.633 1.588l-.83-.648a1.51 1.51 0 00-.564 1.39l.21 1.127c.178.953-.69 1.69-1.554 1.21l-.974-.54a1.51 1.51 0 00-1.416 0l-.974.54c-.864.48-1.732-.257-1.554-1.21l.21-1.127a1.51 1.51 0 00-.564-1.39l-.83-.648c-.647-.598-.177-1.631.633-1.588l1.09.06c.672.04 1.304-.378 1.55-.992l.404-1.006z" clip-rule="evenodd" /></svg>`,
        user_request: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 256 256"><path d="M230.92,212c-15.23-26.33-38.7-45.21-66.09-54.16a72,72,0,1,0-73.66,0C63.78,166.78,40.31,185.66,25.08,212a8,8,0,1,0,13.85,8c18.84-32.56,52.14-52,89.07-52s70.23,19.44,89.07,52a8,8,0,1,0,13.85-8Z"></path></svg>`
    };

    const init = () => {
        loadSettings();
        loadSessionsFromStorage();
        renderSessionList();
        switchToNewChat();
        if (window.api) {
            ui.minimizeBtn.addEventListener('click', () => window.api.minimizeWindow());
            ui.maximizeBtn.addEventListener('click', () => window.api.toggleMaximizeWindow());
            ui.closeBtn.addEventListener('click', () => window.api.closeWindow());
        }
        ui.analysisForm.addEventListener('submit', handleNewAnalysisSubmit);
        ui.continueChatForm.addEventListener('submit', handleContinueChatSubmit);
        ui.newChatBtn.addEventListener('click', switchToNewChat);
        ui.fileInput.addEventListener('change', () => {
            const files = ui.fileInput.files;
            ui.fileName.textContent = files.length > 1 ? `${files.length} 个文件已选择` : (files.length === 1 ? files[0].name : '未选择文件');
            ui.fileName.style.color = 'var(--text-primary)';
        });
        ui.chatInput.addEventListener('input', () => {
            ui.chatInput.style.height = 'auto';
            ui.chatInput.style.height = `${ui.chatInput.scrollHeight}px`;
        });
        ui.saveSettingsBtn.addEventListener('click', saveSettings);
        ui.testConnectionBtn.addEventListener('click', testConnection);
        ui.themeToggle.addEventListener('click', toggleTheme);
        ui.exportBtn.addEventListener('click', handleExport);
        ui.menuToggle.addEventListener('click', toggleSidebar);
        ui.overlay.addEventListener('click', toggleSidebar);
        window.addEventListener('contextmenu', handleContextMenu);
        window.addEventListener('click', hideContextMenu);
    };

    const loadSessionsFromStorage = () => { const storedSessions = localStorage.getItem('talkToDataSessions'); sessions = storedSessions ? JSON.parse(storedSessions) : {}; };
    const saveSessionsToStorage = () => { localStorage.setItem('talkToDataSessions', JSON.stringify(sessions)); };
    const createNewSession = (sessionId, task) => { const newSession = { id: sessionId, task: task, history: [], timestamp: Date.now() }; sessions[sessionId] = newSession; currentSessionId = sessionId; saveSessionsToStorage(); renderSessionList(); };
    const addMessageToCurrentSession = (message) => { if (currentSessionId && sessions[currentSessionId]) { sessions[currentSessionId].history.push(message); saveSessionsToStorage(); } };
    
    const switchToNewChat = () => {
        currentSessionId = null;
        ui.messageContainer.innerHTML = '';
        createWelcomeMessage();
        ui.newAnalysisSection.classList.remove('hidden');
        ui.chatInputContainer.classList.add('hidden');
        ui.exportBtn.classList.add('hidden');
        ui.analysisForm.reset();
        ui.fileName.textContent = '未选择文件';
        document.querySelectorAll('.session-item.active').forEach(item => item.classList.remove('active'));
    };

    const switchToSession = (sessionId) => {
        if (!sessions[sessionId]) return;
        currentSessionId = sessionId;
        const session = sessions[sessionId];
        ui.messageContainer.innerHTML = '';
        session.history.forEach(data => renderMessageBubble(data, false));
        ui.newAnalysisSection.classList.add('hidden');
        ui.chatInputContainer.classList.remove('hidden');
        const hasEvaluation = session.history.some(m => m.type === 'evaluation');
        ui.exportBtn.classList.toggle('hidden', !hasEvaluation);
        renderSessionList();
        scrollToBottom();
    };
    
    const renderSessionList = () => {
        ui.sessionList.innerHTML = '';
        const sortedSessions = Object.values(sessions).sort((a, b) => b.timestamp - a.timestamp);
        if (sortedSessions.length === 0) {
            ui.sessionList.innerHTML = `<li class="no-sessions" style="padding: 12px; color: var(--text-muted); font-size: 0.9em;">没有历史记录</li>`;
            return;
        }
        sortedSessions.forEach(session => {
            const li = document.createElement('li');
            li.className = `session-item ${session.id === currentSessionId ? 'active' : ''}`;
            li.dataset.sessionId = session.id;
            li.innerHTML = `
                <div class="session-content">
                    <span class="session-icon"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 256 256"><path d="M128,24A104,104,0,0,0,36.18,176.88L24.83,210.94a16,16,0,0,0,20.23,20.23l34.06-11.35A104,104,0,1,0,128,24Zm0,192a88,88,0,0,1-45.42-13.22,8,8,0,0,0-9.13-1.33L36,211.17l9.7-27.58a8,8,0,0,0-1.33-9.13A88,88,0,1,1,128,216Z"></path></svg></span>
                    <div class="session-details">
                        <div class="session-title">${DOMPurify.sanitize(session.task)}</div>
                        <div class="session-timestamp">${new Date(session.timestamp).toLocaleString()}</div>
                    </div>
                </div>
                <button class="delete-session-btn" title="删除会话"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 256 256"><path d="M216,48H176V40a24,24,0,0,0-24-24H104A24,24,0,0,0,80,40v8H40a8,8,0,0,0,0,16h8V208a16,16,0,0,0,16,16H192a16,16,0,0,0,16-16V64h8a8,8,0,0,0,0-16ZM96,40a8,8,0,0,1,8-8h48a8,8,0,0,1,8,8v8H96Zm96,168H64V64H192Z"></path></svg></button>
            `;
            li.addEventListener('click', (e) => { if (!e.target.closest('.delete-session-btn')) switchToSession(session.id); });
            li.querySelector('.delete-session-btn').addEventListener('click', async (e) => {
                e.stopPropagation();
                if (confirm(`确定要删除这个会话吗？\n"${session.task}"\n\n此操作将同时删除服务器上的相关文件，且不可恢复。`)) {
                    try {
                        const response = await fetch('/delete_session', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ session_id: session.id })
                        });
                        const result = await response.json();
                        if (!response.ok || !result.success) { throw new Error(result.message || '从服务器删除会话失败'); }
                        delete sessions[session.id];
                        saveSessionsToStorage();
                        if (currentSessionId === session.id) { switchToNewChat(); }
                        renderSessionList();
                    } catch (error) { alert(`删除失败: ${error.message}`); }
                }
            });
            ui.sessionList.appendChild(li);
        });
    };

    const renderMessageBubble = (data, isStreaming) => {
        if (!data.type || !data.content) return;
        if (isStreaming) addMessageToCurrentSession(data);
        const { type, content } = data;
        const titles = { system: '系统消息', thought: '思考', action: '工具调用', observation: '观察', final_summary: '最终总结', evaluation: '任务评估', user_request: '用户请求' };
        const bubble = createBubble(``, `${type}-message`, true);
        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'content-wrapper';
        bubble.appendChild(contentWrapper);
        const iconKey = type === 'user_request' ? 'user_request' : type;
        contentWrapper.innerHTML = `<h3>${icons[iconKey] || ''} ${titles[type] || '消息'}</h3>`; 
        
        let formattedContent, isHtml = false;
        
        // --- 修改：增加内容格式化逻辑 ---
        if (type === 'action') {
            formattedContent = renderActionCard(content);
            isHtml = true;
        } else if (type === 'evaluation') {
            formattedContent = renderEvaluation(content);
            isHtml = true;
        } else if (type === 'observation' && typeof content === 'string' && content.includes('<div class="table-wrapper">')) {
            // 直接渲染从后端接收的HTML表格
            formattedContent = content;
            isHtml = true;
        } else if (type === 'system' && typeof content === 'string') {
            // 渲染系统消息，并将文件名替换为<code class="file-tag">
            formattedContent = content.replace(/'([^']+\.[a-zA-Z0-9]+)'/g, '<code class="file-tag">$1</code>');
            isHtml = true;
        } else if (type === 'observation' && typeof content === 'string' && content.includes('图表已生成并保存于:')) {
            const path = content.split(':').pop().trim();
            formattedContent = `<p>图表已生成。</p><a href="${path}" target="_blank"><img src="${path}" alt="生成的图表" style="max-width: 100%; border-radius: 8px; cursor: pointer;"></a>`;
            isHtml = true;
        } else if (type === 'user_request') {
             const filenames = content.files || [];
             const fileListHtml = filenames.map(name => `<div class="file-info">📄 ${DOMPurify.sanitize(name)}</div>`).join('');
             formattedContent = `${DOMPurify.sanitize(marked.parse(content.task))}${fileListHtml}`;
             isHtml = true;
        } else {
            // 默认行为：将内容作为Markdown解析
            formattedContent = String(content);
        }
        // --- 结束修改 ---

        renderContent(contentWrapper, formattedContent, isHtml);
        if (type === 'evaluation') ui.exportBtn.classList.remove('hidden');
    };
    
    const getStatusTextForType = (type, content = '') => {
        switch(type) {
            case 'thought': return "正在思考...";
            case 'action':
                const toolMatch = typeof content === 'string' && content.match(/调用工具: ([\w_]+)/);
                return toolMatch ? `调用工具: ${toolMatch[1]}` : "执行行动...";
            case 'observation': return "处理观察结果...";
            case 'final_summary': return "生成最终总结...";
            case 'evaluation': return "任务完成！";
            default: return null;
        }
    };

    const handleNewAnalysisSubmit = async (e) => {
        e.preventDefault();
        const task = ui.taskInput.value.trim();
        const files = ui.fileInput.files;
        if (!task || files.length === 0) { alert('请填写分析任务并选择至少一个数据文件。'); return; }
        const modelSettings = { api_base_url: ui.apiBaseUrl.value.trim(), api_key: ui.apiKey.value.trim(), model_name: ui.modelName.value.trim() };
        if (!modelSettings.api_key || !modelSettings.api_base_url || !modelSettings.model_name) { alert('请在“模型设置”中填写完整的 API 信息。'); return; }
        resetUIForAnalysis();
        const startFormData = new FormData();
        for (let i = 0; i < files.length; i++) { startFormData.append('file', files[i]); }
        for (const key in modelSettings) { startFormData.append(key, modelSettings[key]); }
        try {
            const startResponse = await fetch('/start_session', { method: 'POST', body: startFormData });
            const startResult = await startResponse.json();
            if (!startResponse.ok || !startResult.success) { throw new Error(startResult.error || '创建会话失败'); }
            createNewSession(startResult.session_id, task);
            switchToSession(startResult.session_id);
            renderMessageBubble(startResult.initial_message, true);
            const userRequestMessage = { type: 'user_request', content: { task: task, files: Array.from(files).map(f => f.name) }};
            renderMessageBubble(userRequestMessage, true);
            await streamAnalysis(task);
        } catch (error) { createBubble(`<h3>会话启动失败</h3><p>${error.message}</p>`, 'system-message', true); setFormState(true); }
    };

    const handleContinueChatSubmit = async (e) => {
        e.preventDefault();
        const task = ui.chatInput.value.trim();
        if (!task || !currentSessionId) return;
        ui.chatInput.value = '';
        ui.chatInput.style.height = 'auto';
        const userRequestMessage = { type: 'user_request', content: { task: task, files: [] } };
        renderMessageBubble(userRequestMessage, true);
        await streamAnalysis(task);
    };

    const streamAnalysis = async (task) => {
        const modelSettings = { api_base_url: ui.apiBaseUrl.value.trim(), api_key: ui.apiKey.value.trim(), model_name: ui.modelName.value.trim() };
        const body = JSON.stringify({ session_id: currentSessionId, task: task, ...modelSettings });
        try {
            setFormState(false);
            showProgressBadge();
            const response = await fetch('/continue_analysis', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body });
            if (!response.ok) { const errData = await response.json().catch(() => ({ error: `服务器错误: ${response.status}` })); throw new Error(errData.error); }
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n');
                buffer = parts.pop();
                for (const part of parts) {
                    if (part.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(part.substring(6));
                            if (data.type === 'progress') {
                                currentProgress.percent = data.value;
                            } else {
                                const statusText = getStatusTextForType(data.type, data.content);
                                if (statusText) {
                                    currentProgress.text = statusText;
                                }
                                renderMessageBubble(data, true);
                            }
                            updateProgressBadge(currentProgress.percent, currentProgress.text);

                        } catch (error) {
                            console.error("解析JSON失败:", error, part);
                        }
                    }
                }
            }
        } catch (error) { createBubble(`<h3>请求失败</h3><p>${error.message}</p>`, 'system-message', true);
        } finally {
            currentProgress.text = "任务完成！";
            updateProgressBadge(currentProgress.percent, currentProgress.text);
            setTimeout(hideProgressBadge, 2000);
            setFormState(true);
        }
    };
    
    const resetUIForAnalysis = () => { ui.messageContainer.innerHTML = ''; ui.exportBtn.classList.add('hidden'); setFormState(false); };
    const setFormState = (enabled) => { ui.submitBtn.disabled = !enabled; ui.submitBtn.textContent = enabled ? '开始分析' : '分析中...'; ui.chatInput.disabled = !enabled; document.getElementById('send-chat-btn').disabled = !enabled; };
    const handleContextMenu = (e) => { e.preventDefault(); rightClickedElement = e.target; const menuItems = []; const selection = window.getSelection().toString().trim(); const isEditable = rightClickedElement.tagName === 'INPUT' || rightClickedElement.tagName === 'TEXTAREA'; if (window.api) { if (isEditable) { menuItems.push({ label: '剪切', action: () => { const selectedText = rightClickedElement.value.substring(rightClickedElement.selectionStart, rightClickedElement.selectionEnd); if (selectedText) { window.api.writeToClipboard(selectedText); document.execCommand('delete'); } } }); menuItems.push({ label: '复制', action: () => { const selectedText = rightClickedElement.value.substring(rightClickedElement.selectionStart, rightClickedElement.selectionEnd); if (selectedText) window.api.writeToClipboard(selectedText); } }); menuItems.push({ label: '粘贴', action: async () => { const text = await window.api.readFromClipboard(); if (text && rightClickedElement) { const start = rightClickedElement.selectionStart; const end = rightClickedElement.selectionEnd; const newText = rightClickedElement.value.substring(0, start) + text + rightClickedElement.value.substring(end); rightClickedElement.value = newText; rightClickedElement.focus(); rightClickedElement.selectionStart = rightClickedElement.selectionEnd = start + text.length; } } }); menuItems.push({ type: 'separator' }); menuItems.push({ label: '全选', action: () => rightClickedElement.select() }); } else if (selection) { menuItems.push({ label: '复制', action: () => window.api.writeToClipboard(selection) }); } else { hideContextMenu(); return; } } else { if (selection) { menuItems.push({ label: '复制 (浏览器)', action: () => document.execCommand('copy') }); } } if (menuItems.length > 0) { showContextMenu(menuItems, e.clientX, e.clientY); } else { hideContextMenu(); } };
    const showContextMenu = (items, x, y) => { const menu = ui.contextMenu; menu.innerHTML = ''; items.forEach(item => { if (item.type === 'separator') { const separator = document.createElement('div'); separator.className = 'context-menu-separator'; menu.appendChild(separator); } else { const menuItem = document.createElement('div'); menuItem.className = 'context-menu-item'; menuItem.textContent = item.label; menuItem.addEventListener('click', (e) => { e.stopPropagation(); item.action(); hideContextMenu(); }); menu.appendChild(menuItem); } }); const { innerWidth, innerHeight } = window; menu.style.display = 'block'; const { offsetWidth, offsetHeight } = menu; menu.style.left = `${x + offsetWidth > innerWidth ? innerWidth - offsetWidth - 5 : x}px`; menu.style.top = `${y + offsetHeight > innerHeight ? innerHeight - offsetHeight - 5 : y}px`; };
    const hideContextMenu = () => { if (ui.contextMenu) ui.contextMenu.style.display = 'none'; };
    const saveSettings = () => { const settings = { apiBaseUrl: ui.apiBaseUrl.value.trim(), apiKey: ui.apiKey.value.trim(), modelName: ui.modelName.value.trim() }; localStorage.setItem('talkToDataSettings', JSON.stringify(settings)); ui.saveSettingsBtn.textContent = '已保存!'; setTimeout(() => { ui.saveSettingsBtn.textContent = '保存设置'; }, 2000); };
    const loadSettings = () => { const savedSettings = localStorage.getItem('talkToDataSettings'); if (savedSettings) { const settings = JSON.parse(savedSettings); ui.apiBaseUrl.value = settings.apiBaseUrl || 'https://api.deepseek.com/v1'; ui.apiKey.value = settings.apiKey || ''; ui.modelName.value = settings.modelName || 'deepseek-chat'; } else { ui.apiBaseUrl.value = 'https://api.deepseek.com/v1'; ui.modelName.value = 'deepseek-chat'; } const theme = localStorage.getItem('theme') || 'dark'; document.body.setAttribute('data-theme', theme); };
    const testConnection = async () => { const apiKey = ui.apiKey.value.trim(); const apiBaseUrl = ui.apiBaseUrl.value.trim(); const statusDiv = ui.connectionStatus; if (!apiKey || !apiBaseUrl) { alert('请先填写 API Key 和 API 地址。'); return; } statusDiv.textContent = '正在测试...'; statusDiv.className = 'connection-status'; try { const response = await fetch('/test_connection', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ api_key: apiKey, api_base_url: apiBaseUrl }) }); const result = await response.json(); if (response.ok && result.success) { statusDiv.textContent = result.message; statusDiv.classList.add('success'); } else { statusDiv.textContent = result.message || '连接失败，请检查控制台获取更多信息。'; statusDiv.classList.add('error'); } } catch (error) { statusDiv.textContent = `客户端错误: ${error.message}`; statusDiv.classList.add('error'); } };
    
    const renderContent = (element, text, isHtml) => {
        const contentDiv = document.createElement('div');
        if (isHtml) {
            // 使用DOMPurify清理HTML，但允许表格相关标签和样式类
            contentDiv.innerHTML = DOMPurify.sanitize(text, {
                ADD_TAGS: ['table', 'thead', 'tbody', 'tr', 'th', 'td', 'div'],
                ADD_ATTR: ['class']
            });
        } else {
            // 解析Markdown
            contentDiv.innerHTML = DOMPurify.sanitize(marked.parse(text));
        }
        element.appendChild(contentDiv);
        
        // 数学公式和代码高亮
        if (window.renderMathInElement) {
            renderMathInElement(element, {
                delimiters: [{left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}],
                throwOnError: false
            });
        }
        element.querySelectorAll('pre code').forEach(el => {
             // 确保没有被高亮两次
            if (!el.classList.contains('hljs')) {
                hljs.highlightElement(el);
            }
        });
        scrollToBottom();
    };

    const showProgressBadge = () => {
        currentProgress = { percent: 0, text: '正在初始化...' };
        updateProgressBadge(currentProgress.percent, currentProgress.text);
        ui.progressBadge.classList.remove('hidden');
    };
    const hideProgressBadge = () => { ui.progressBadge.classList.add('hidden'); };
    const updateProgressBadge = (percent, statusText) => {
        if (percent !== null && percent !== undefined) {
            const angle = percent * 3.6;
            ui.progressCircle.style.background = `conic-gradient(var(--accent-green) ${angle}deg, var(--progress-bar-bg) ${angle}deg)`;
            ui.progressPercent.textContent = `${Math.round(percent)}%`;
        }
        if (statusText) {
            ui.progressStatusText.textContent = statusText;
        }
    };
    
    // --- 修改：美化Action Card的代码块显示 ---
    const renderActionCard = (actionData) => {
        const toolMatch = actionData.match(/调用工具: ([\w_]+)/);
        const argsMatch = actionData.match(/参数: (\{.*\})$/s);
    
        if (!toolMatch || !argsMatch) {
            return `<div class="action-card"><div class="param-item">${actionData}</div></div>`;
        }
    
        const toolName = toolMatch[1];
        let args = {};
        try {
            args = JSON.parse(argsMatch[1]);
        } catch (e) {
            // 如果解析失败，直接显示原始字符串
            return `<div class="action-card"><div class="tool-name">${toolName}</div><div class="param-item"><pre><code>${argsMatch[1]}</code></pre></div></div>`;
        }
    
        const argKeys = Object.keys(args);
        let paramsHtml;
        if (argKeys.length === 0) {
            paramsHtml = '<div class="param-item">无参数</div>';
        } else {
            paramsHtml = argKeys.map(key => {
                const value = args[key];
                let valueHtml;
                // 如果参数是 'code'，则特殊处理为Python代码块
                if (key === 'code') {
                    const codeElement = document.createElement('code');
                    codeElement.className = 'language-python';
                    codeElement.textContent = value; // 使用 textContent 防止 XSS
                    const preElement = document.createElement('pre');
                    preElement.appendChild(codeElement);
                    valueHtml = preElement.outerHTML;
                } else {
                    // 其他参数格式化为JSON
                    const valueStr = JSON.stringify(value, null, 2);
                    const codeElement = document.createElement('code');
                    codeElement.className = 'language-json';
                    codeElement.textContent = valueStr;
                    const preElement = document.createElement('pre');
                    preElement.appendChild(codeElement);
                    valueHtml = preElement.outerHTML;
                }
                return `<div class="param-item"><strong>${key}:</strong>${valueHtml}</div>`;
            }).join('');
        }
    
        return `<div class="action-card"><div class="tool-name">${toolName}</div>${paramsHtml}</div>`;
    };
    // ------------------------------------

    const createWelcomeMessage = () => { ui.messageContainer.innerHTML = ''; const welcomeHtml = `<h3>${icons.system} 欢迎使用 Talk to Data</h3><p>这是一个基于大语言模型的对话式数据分析工具。请在左侧侧边栏中：</p><ol><li>输入您的分析任务，例如：<em>"请分析数据，找出销售额最高的三个产品，并绘制柱状图"</em>。</li><li>上传您的数据文件（支持CSV, Excel, JSON, Shapefile等）。</li><li>点击“开始分析”按钮，在此处查看实时分析过程。</li></ol><p>或者，您可以从“会话历史”中加载之前的分析。</p>`; createBubble(welcomeHtml, 'system-message', true); };
    const createBubble = (content, type, isHtml) => { const bubble = document.createElement('div'); bubble.className = `message-bubble ${type}`; if (isHtml) bubble.innerHTML = content; else bubble.textContent = content; ui.messageContainer.appendChild(bubble); scrollToBottom(); return bubble; };
    const toggleTheme = () => { const newTheme = document.body.dataset.theme === 'dark' ? 'light' : 'dark'; document.body.dataset.theme = newTheme; localStorage.setItem('theme', newTheme); };
    const toggleSidebar = () => { ui.sidebar.classList.toggle('open'); ui.overlay.classList.toggle('open'); };
    const scrollToBottom = () => { ui.messageContainer.scrollTop = ui.messageContainer.scrollHeight; };
    const handleExport = () => { if (!currentSessionId || !sessions[currentSessionId]) { alert("没有可导出的分析内容。"); return; } const historyToExport = sessions[currentSessionId].history; fetch('/export_markdown', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(historyToExport) }).then(res => { if (!res.ok) throw new Error("导出失败"); const disposition = res.headers.get('Content-Disposition'); const filenameMatch = disposition && disposition.match(/filename="(.+?)"/); const filename = filenameMatch ? filenameMatch[1] : 'report.md'; return Promise.all([res.blob(), filename]); }).then(([blob, filename]) => { const url = window.URL.createObjectURL(blob); const a = document.createElement('a'); a.style.display = 'none'; a.href = url; a.download = filename; document.body.appendChild(a); a.click(); window.URL.revokeObjectURL(url); document.body.removeChild(a); }).catch(err => { console.error('Export failed:', err); alert(`导出报告失败: ${err.message}`); }); };
    const renderEvaluation = (evalData) => { return `<div><h4>综合评分: ${evalData.score || 0}/10</h4><p><strong>评语:</strong> ${evalData.justification || '无'}</p>${evalData.chart_path ? `<div><img src="${evalData.chart_path}" alt="Performance Chart" style="max-width: 100%; border-radius: 8px;"></div>` : ''}</div>`; };
    
    init();
});