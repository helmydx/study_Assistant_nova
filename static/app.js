// static/app.js

let ws;
const wsUrl = `ws://${window.location.host}/ws`;

// DOM Elements
const bodyEl = document.body;
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const userBubble = document.getElementById('userBubble');
const botBubble = document.getElementById('botBubble');
const textInput = document.getElementById('textInput');
const inputForm = document.getElementById('inputForm');
const btnMic = document.getElementById('btnMic');
const btnMicLocal = document.getElementById('btnMicLocal');
const btnMicAI = document.getElementById('btnMicAI');
const btnStopSpeak = document.getElementById('btnStopSpeak');
const clockDisplay = document.getElementById('clockDisplay');
const robotClock = document.getElementById('robotClock');
const dateDisplay = document.getElementById('dateDisplay');
const alarmOverlay = document.getElementById('alarmOverlay');
const alarmOverlayTime = document.getElementById('alarmOverlayTime');
const alarmOverlayLabel = document.getElementById('alarmOverlayLabel');
const btnDismissAlarm = document.getElementById('btnDismissAlarm');
const btnToggleSidebar = document.getElementById('btnToggleSidebar');
const captionsArea = document.querySelector('.captions-area');

// Sidebar counts & lists
const notesCount = document.getElementById('notesCount');
const notesList = document.getElementById('notesList');
const tasksCount = document.getElementById('tasksCount');
const tasksList = document.getElementById('tasksList');
const alarmsCount = document.getElementById('alarmsCount');
const alarmsList = document.getElementById('alarmsList');

// --- WebSocket Connection ---
function connectWebSocket() {
    console.log("Menghubungkan ke WebSocket...");
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log("WebSocket Terhubung.");
        updateStatusDisplay('idle');
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };

    ws.onclose = () => {
        console.log("WebSocket Terputus. Mencoba menghubungkan kembali...");
        updateStatusDisplay('offline');
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (err) => {
        console.error("WebSocket Error: ", err);
    };
}

function updateNoteTakingUI(sessionState) {
    if (sessionState === "recording_note") {
        textInput.placeholder = "Sedang mencatat... Ketik 'selesai catatan' untuk menyimpan.";
        textInput.classList.add("recording-note-mode");
    } else {
        textInput.placeholder = "Ketik perintah di sini...";
        textInput.classList.remove("recording-note-mode");
    }
}

function handleWebSocketMessage(msg) {
    switch (msg.type) {
        case 'state':
            updateStatusDisplay(msg.value);
            break;
            
        case 'user_speech':
            userBubble.textContent = msg.value;
            userBubble.style.opacity = 1;
            if (captionsArea) {
                captionsArea.scrollTop = captionsArea.scrollHeight;
            }
            break;
            
        case 'bot_response':
            let badgeHtml = '';
            if (msg.source === 'local') {
                badgeHtml = '<div class="source-badge badge-local">⚡ Lokal</div>';
            } else if (msg.source === 'gemini') {
                badgeHtml = '<div class="source-badge badge-gemini">✨ Gemini AI</div>';
            }
            botBubble.innerHTML = `${badgeHtml}<div class="bot-text">${formatMarkdown(msg.value)}</div>`;
            botBubble.style.opacity = 1;
            
            updateNoteTakingUI(msg.session_state);
            
            if (captionsArea && botBubble) {
                captionsArea.scrollTop = botBubble.offsetTop - captionsArea.offsetTop;
            }
            break;
            
        case 'session_state':
            updateNoteTakingUI(msg.value);
            break;
            
        case 'sidebar_data':
            renderSidebar(msg.notes, msg.tasks, msg.alarms);
            if (msg.songs && msg.music_status) {
                renderMusicList(msg.songs, msg.music_status);
            }
            break;
            
        case 'alarm_trigger':
            triggerAlarmOverlay(msg.time, msg.label);
            break;

        case 'system_stats':
            updateDeviceStats(msg.value);
            break;

        case 'start_pomodoro':
            startPomodoro(msg.study_time, msg.break_time);
            switchTab('pomodoro');
            bodyEl.classList.remove('sidebar-hidden');
            break;

        case 'start_timer':
            startPomodoro(msg.duration, 0);
            switchTab('pomodoro');
            bodyEl.classList.remove('sidebar-hidden');
            break;

        case 'stop_pomodoro':
            resetPomodoro();
            break;

        case 'open_app':
            switchTab(msg.app);
            bodyEl.classList.remove('sidebar-hidden');
            if (msg.app === 'catatan') {
                textInput.placeholder = "Sedang mencatat... Katakan 'selesai catatan' untuk menyimpan.";
            } else if (msg.app === 'tugas') {
                textInput.placeholder = "Tulis tugas baru Anda...";
            } else if (msg.app === 'alarm') {
                textInput.placeholder = "Format: 07:00 bangun pagi...";
            } else {
                textInput.placeholder = "Ketik perintah di sini...";
            }
            break;

        case 'close_app':
            bodyEl.classList.add('sidebar-hidden');
            document.querySelectorAll('.dock-btn').forEach(d => d.classList.remove('active'));
            textInput.placeholder = "Ketik perintah di sini...";
            break;
    }
}

// Update status bar UI
function updateStatusDisplay(state) {
    // Reset all status classes
    bodyEl.classList.remove('state-idle', 'state-listening', 'state-thinking', 'state-speaking', 'state-offline');
    bodyEl.classList.add(`state-${state}`);

    if (state !== 'listening') {
        bodyEl.removeAttribute('data-listening-mode');
    } else if (!bodyEl.hasAttribute('data-listening-mode')) {
        bodyEl.setAttribute('data-listening-mode', 'hybrid');
    }

    switch (state) {
        case 'idle':
            statusText.textContent = "STANDBY";
            break;
        case 'listening':
            statusText.textContent = "MENDENGARKAN...";
            userBubble.textContent = "...";
            break;
        case 'thinking':
            statusText.textContent = "BERPIKIR...";
            botBubble.textContent = "...";
            break;
        case 'speaking':
            statusText.textContent = "BERBICARA...";
            break;
        case 'offline':
            statusText.textContent = "OFFLINE";
            break;
    }
}

// --- Render Sidebar Data ---
function renderSidebar(notes, tasks, alarms) {
    // 1. Notes
    notesCount.textContent = notes.length;
    if (notes.length === 0) {
        notesList.innerHTML = '<div class="empty-state">Belum ada catatan. Katakan "Nova, catat..." untuk menyimpan.</div>';
    } else {
        notesList.innerHTML = notes.map(n => `
            <div class="item-card note-card">
                <div class="card-title">${escapeHTML(n.content)}</div>
                <div class="card-meta">
                    <span>ID: ${n.id}</span>
                    <span>${formatShortDate(n.created_at)}</span>
                </div>
            </div>
        `).join('');
    }

    // 2. Tasks
    tasksCount.textContent = tasks.length;
    if (tasks.length === 0) {
        tasksList.innerHTML = '<div class="empty-state">Bebas tugas! Katakan "Nova, tambah tugas..." untuk mencatat.</div>';
    } else {
        tasksList.innerHTML = tasks.map(t => `
            <div class="item-card task-card ${t.completed ? 'completed' : ''}">
                <div class="card-title">${escapeHTML(t.title)}</div>
                <div class="card-meta">
                    <span>ID: ${t.id}</span>
                    <span>${t.deadline ? 'Tenggat: ' + escapeHTML(t.deadline) : 'Tanpa Tenggat'}</span>
                </div>
            </div>
        `).join('');
    }

    // 3. Alarms
    alarmsCount.textContent = alarms.length;
    if (alarms.length === 0) {
        alarmsList.innerHTML = '<div class="empty-state">Tidak ada alarm. Katakan "Nova, buat alarm pukul..." untuk memasang.</div>';
    } else {
        alarmsList.innerHTML = alarms.map(a => `
            <div class="item-card alarm-card-item ${a.active ? '' : 'inactive'}">
                <div class="alarm-time-display">${escapeHTML(a.time)}</div>
                <div class="alarm-label-display">${escapeHTML(a.label || 'Alarm')}</div>
                <div class="card-meta">
                    <span>ID: ${a.id}</span>
                    <span>${a.active ? 'Aktif' : 'Nonaktif'}</span>
                </div>
            </div>
        `).join('');
    }
}

// --- Alarm Overlay Control ---
function triggerAlarmOverlay(time, label) {
    alarmOverlayTime.textContent = time;
    alarmOverlayLabel.textContent = label || "Waktunya bangun!";
    alarmOverlay.classList.add('active');
}

btnDismissAlarm.addEventListener('click', () => {
    alarmOverlay.classList.remove('active');
});

// --- Tab & Dock Switching ---
function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(b => {
        if (b.getAttribute('data-tab') === tabId) {
            b.classList.add('active');
        } else {
            b.classList.remove('active');
        }
    });
    
    document.querySelectorAll('.tab-pane').forEach(p => {
        if (p.getAttribute('id') === `tab-${tabId}`) {
            p.classList.add('active');
        } else {
            p.classList.remove('active');
        }
    });

    document.querySelectorAll('.dock-btn').forEach(d => {
        if (d.getAttribute('data-tab') === tabId) {
            d.classList.add('active');
        } else {
            d.classList.remove('active');
        }
    });
}

// Hook up dock buttons click
document.querySelectorAll('.dock-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabId = btn.getAttribute('data-tab');
        let commandName = "buka " + tabId;
        if (tabId === "pomodoro") commandName = "buka fokus";
        sendWSMessage('user_input', { value: commandName });
    });
});

// Hook up close button
const btnClosePanel = document.getElementById('btnClosePanel');
if (btnClosePanel) {
    btnClosePanel.addEventListener('click', () => {
        sendWSMessage('user_input', { value: 'keluar' });
    });
}

// --- Input Interactions ---
inputForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const val = textInput.value.trim();
    if (!val) return;

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'user_input',
            value: val
        }));
        textInput.value = '';
    }
});

if (btnMicLocal) {
    btnMicLocal.addEventListener('click', () => {
        triggerMicListening('local');
    });
}

if (btnMicAI) {
    btnMicAI.addEventListener('click', () => {
        triggerMicListening('ai');
    });
}

if (btnMic) {
    btnMic.addEventListener('click', () => {
        triggerMicListening('hybrid');
    });
}

if (btnStopSpeak) {
    btnStopSpeak.addEventListener('click', () => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'stop_speak'
            }));
        }
    });
}

function triggerMicListening(mode) {
    const isBusy = bodyEl.classList.contains('state-listening') || 
                   bodyEl.classList.contains('state-thinking') || 
                   bodyEl.classList.contains('state-speaking');
    if (isBusy) return;

    if (ws && ws.readyState === WebSocket.OPEN) {
        bodyEl.setAttribute('data-listening-mode', mode);
        ws.send(JSON.stringify({
            type: 'trigger_listen',
            mode: mode
        }));
    }
}

// Bind spacebar key for mic trigger
window.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && document.activeElement !== textInput) {
        e.preventDefault(); // Prevent page scrolling
        triggerMicListening('hybrid');
    } else if (e.code === 'Escape') {
        if (btnStopSpeak) {
            btnStopSpeak.click();
        }
    }
});

// --- Clock & Date Display ---
function updateClock() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    
    const timeStr = `${hours}:${minutes}:${seconds}`;
    if (clockDisplay) clockDisplay.textContent = timeStr;
    if (robotClock) robotClock.textContent = timeStr;

    // Formatting date
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    if (dateDisplay) dateDisplay.textContent = now.toLocaleDateString('id-ID', options);
}
setInterval(updateClock, 1000);
updateClock();

// --- Eyes Animations (Blinking & Pupils) ---
const leftEye = document.getElementById('leftEye');
const rightEye = document.getElementById('rightEye');

function blinkEyes() {
    if (leftEye && rightEye) {
        leftEye.style.transform = 'scaleY(0.08)';
        rightEye.style.transform = 'scaleY(0.08)';
        setTimeout(() => {
            leftEye.style.transform = 'scaleY(1)';
            rightEye.style.transform = 'scaleY(1)';
        }, 150);
    }
    // Random blink interval (between 3 and 7 seconds)
    const nextBlink = 3000 + Math.random() * 4000;
    setTimeout(blinkEyes, nextBlink);
}
setTimeout(blinkEyes, 3000);

// Slowly drift pupils to make them look alive
let angle = 0;
function driftPupils() {
    const isIdle = bodyEl.classList.contains('state-idle');
    if (isIdle && leftEye && rightEye) {
        angle += 0.02;
        const dx = Math.cos(angle) * 3;
        const dy = Math.sin(angle * 1.5) * 2;
        leftEye.querySelector('.pupil').style.transform = `translate(${dx}px, ${dy}px)`;
        rightEye.querySelector('.pupil').style.transform = `translate(${dx}px, ${dy}px)`;
    } else {
        // Reset translate during listening/thinking
        leftEye.querySelector('.pupil').style.transform = `translate(0px, 0px)`;
        rightEye.querySelector('.pupil').style.transform = `translate(0px, 0px)`;
    }
    requestAnimationFrame(driftPupils);
}
driftPupils();

// --- Mouth Waveform Animation ---
const mouthPath = document.getElementById('mouthPath');
let phase = 0;

function drawMouth() {
    let amp = 0;
    let freq = 0.05;

    // Get current state
    const states = ['idle', 'listening', 'thinking', 'speaking'];
    let currentState = 'idle';
    for (let s of states) {
        if (bodyEl.classList.contains(`state-${s}`)) {
            currentState = s;
            break;
        }
    }

    // Configure wave params based on robot status
    if (currentState === 'speaking') {
        amp = 18 + Math.random() * 15;
        freq = 0.15;
    } else if (currentState === 'thinking') {
        amp = 5 + Math.sin(Date.now() / 150) * 3;
        freq = 0.08;
    } else if (currentState === 'listening') {
        amp = 3;
        freq = 0.04;
    } else {
        amp = 0;
        freq = 0;
    }

    phase += freq;
    let pathData = "M 10 50";
    
    // Draw smooth sine wave with border damping (windowing)
    for (let x = 10; x <= 290; x += 5) {
        const windowFactor = Math.sin((x - 10) / 280 * Math.PI); // 0 at start/end, 1 in middle
        const y = 50 + Math.sin(x * 0.07 + phase) * amp * windowFactor;
        pathData += ` L ${x} ${y}`;
    }

    mouthPath.setAttribute('d', pathData);
    
    // Color changes based on state
    let strokeColor = 'var(--neon-cyan)';
    if (currentState === 'speaking') strokeColor = 'var(--color-speaking)';
    else if (currentState === 'thinking') strokeColor = 'var(--color-thinking)';
    else if (currentState === 'listening') strokeColor = 'var(--color-listening)';
    mouthPath.setAttribute('stroke', strokeColor);

    requestAnimationFrame(drawMouth);
}
drawMouth();

// --- Helpers ---
function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
}

function formatMarkdown(text) {
    if (!text) return '';
    let html = escapeHTML(text);
    
    // 1. Headers
    html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
    
    // 2. Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // 3. Italic
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    html = html.replace(/_(.*?)_/g, '<em>$1</em>');
    
    // 4. Code Blocks
    html = html.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // 5. Bullet Lists
    html = html.replace(/^[-*] (.*?)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*?<\/li>)+/gs, '<ul>$&</ul>');
    
    // 6. Paragraphs and line breaks
    let lines = html.split('\n');
    let processedLines = lines.map(line => {
        let trimmed = line.trim();
        if (trimmed === '') return '<div class="spacer"></div>';
        if (/^<(h1|h2|h3|ul|li|div)/.test(trimmed)) return line;
        return `<p>${line}</p>`;
    });
    
    return processedLines.join('\n');
}

function formatShortDate(dateStr) {
    try {
        const d = new Date(dateStr);
        return d.toLocaleDateString('id-ID', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
        return dateStr;
    }
}

// Start WebSocket connection
connectWebSocket();

// Toggle Sidebar click listener (deprecated)

// --- WebSocket Helper ---
function sendWSMessage(type, payload = {}) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type, ...payload }));
    }
}

// ==========================================================================
// THEME SWITCHING SYSTEM
// ==========================================================================
const btnThemeSelector = document.getElementById('btnThemeSelector');
const themeDropdown = document.getElementById('themeDropdown');

if (btnThemeSelector && themeDropdown) {
    btnThemeSelector.addEventListener('click', (e) => {
        e.stopPropagation();
        themeDropdown.classList.toggle('show');
    });

    document.addEventListener('click', () => {
        themeDropdown.classList.remove('show');
    });

    themeDropdown.querySelectorAll('.theme-opt').forEach(opt => {
        opt.addEventListener('click', () => {
            const theme = opt.getAttribute('data-theme');
            setTheme(theme);
        });
    });
}

function setTheme(themeName) {
    bodyEl.classList.remove('theme-cyber', 'theme-arduino', 'theme-brutalist', 'theme-female', 'theme-male');
    bodyEl.classList.add(`theme-${themeName}`);
    localStorage.setItem('nova-theme', themeName);
    
    if (themeDropdown) {
        themeDropdown.querySelectorAll('.theme-opt').forEach(opt => {
            if (opt.getAttribute('data-theme') === themeName) {
                opt.classList.add('active');
            } else {
                opt.classList.remove('active');
            }
        });
    }
}

// Load saved theme on boot
const savedTheme = localStorage.getItem('nova-theme') || 'cyber';
setTheme(savedTheme);

// ==========================================================================
// POMODORO & TIMER TIMER SYSTEM
// ==========================================================================
let pomoInterval = null;
let pomoTimeRemaining = 1500; // default 25 min
let pomoIsRunning = false;
let pomoCurrentState = 'study'; // 'study' or 'break'
let pomoStudyDuration = 25;
let pomoBreakDuration = 5;

const pomoTime = document.getElementById('pomoTime');
const pomoLabel = document.getElementById('pomoLabel');
const pomoStatusText = document.getElementById('pomoStatusText');
const btnPomoStart = document.getElementById('btnPomoStart');
const btnPomoPause = document.getElementById('btnPomoPause');
const btnPomoReset = document.getElementById('btnPomoReset');

function updatePomoDisplay() {
    if (!pomoTime) return;
    const minutes = Math.floor(pomoTimeRemaining / 60);
    const seconds = pomoTimeRemaining % 60;
    pomoTime.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    pomoLabel.textContent = pomoCurrentState === 'study' ? 'Belajar' : 'Istirahat';
    pomoStatusText.textContent = pomoIsRunning ? 'AKTIF' : 'JEDA';
    
    if (pomoIsRunning) {
        btnPomoStart.disabled = true;
        btnPomoPause.disabled = false;
    } else {
        btnPomoStart.disabled = false;
        btnPomoPause.disabled = true;
    }
}

function startPomodoro(studyMin = 25, breakMin = 5) {
    pomoStudyDuration = studyMin;
    pomoBreakDuration = breakMin;
    
    if (pomoInterval) clearInterval(pomoInterval);
    
    pomoTimeRemaining = pomoStudyDuration * 60;
    pomoCurrentState = 'study';
    pomoIsRunning = true;
    
    pomoInterval = setInterval(() => {
        if (pomoTimeRemaining > 0) {
            pomoTimeRemaining--;
            updatePomoDisplay();
        } else {
            clearInterval(pomoInterval);
            pomoIsRunning = false;
            
            if (pomoCurrentState === 'study') {
                sendWSMessage('speak_text', { value: `Sesi belajar selesai. Silakan istirahat selama ${pomoBreakDuration} menit.` });
                if (pomoBreakDuration > 0) {
                    pomoCurrentState = 'break';
                    pomoTimeRemaining = pomoBreakDuration * 60;
                    startBreak();
                } else {
                    resetPomodoro();
                }
            } else {
                sendWSMessage('speak_text', { value: "Waktu istirahat selesai. Mari kembali fokus belajar." });
                pomoCurrentState = 'study';
                pomoTimeRemaining = pomoStudyDuration * 60;
                updatePomoDisplay();
            }
        }
    }, 1000);
    
    updatePomoDisplay();
}

function startBreak() {
    pomoIsRunning = true;
    pomoInterval = setInterval(() => {
        if (pomoTimeRemaining > 0) {
            pomoTimeRemaining--;
            updatePomoDisplay();
        } else {
            clearInterval(pomoInterval);
            pomoIsRunning = false;
            sendWSMessage('speak_text', { value: "Sesi istirahat selesai. Silakan mulai sesi belajar berikutnya." });
            pomoCurrentState = 'study';
            pomoTimeRemaining = pomoStudyDuration * 60;
            updatePomoDisplay();
        }
    }, 1000);
    updatePomoDisplay();
}

function pausePomodoro() {
    if (pomoInterval) {
        clearInterval(pomoInterval);
        pomoIsRunning = false;
        updatePomoDisplay();
    }
}

function resetPomodoro() {
    pausePomodoro();
    pomoCurrentState = 'study';
    pomoTimeRemaining = pomoStudyDuration * 60;
    updatePomoDisplay();
    if (pomoStatusText) pomoStatusText.textContent = 'STANDBY';
}

// Preset button handlers
document.querySelectorAll('.btn-preset').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-preset').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        pomoStudyDuration = parseInt(btn.getAttribute('data-study'));
        pomoBreakDuration = parseInt(btn.getAttribute('data-break'));
        resetPomodoro();
    });
});

if (btnPomoStart) {
    btnPomoStart.addEventListener('click', () => {
        pomoIsRunning = true;
        if (pomoInterval) clearInterval(pomoInterval);
        
        pomoInterval = setInterval(() => {
            if (pomoTimeRemaining > 0) {
                pomoTimeRemaining--;
                updatePomoDisplay();
            } else {
                clearInterval(pomoInterval);
                pomoIsRunning = false;
                
                if (pomoCurrentState === 'study') {
                    sendWSMessage('speak_text', { value: `Sesi belajar selesai. Silakan istirahat ${pomoBreakDuration} menit.` });
                    if (pomoBreakDuration > 0) {
                        pomoCurrentState = 'break';
                        pomoTimeRemaining = pomoBreakDuration * 60;
                        startBreak();
                    } else {
                        resetPomodoro();
                    }
                } else {
                    sendWSMessage('speak_text', { value: "Waktu istirahat selesai. Kembali belajar." });
                    pomoCurrentState = 'study';
                    pomoTimeRemaining = pomoStudyDuration * 60;
                    updatePomoDisplay();
                }
            }
        }, 1000);
        updatePomoDisplay();
        sendWSMessage('trigger_pomodoro_ws', { action: 'start', study_time: pomoStudyDuration, break_time: pomoBreakDuration });
    });
}

if (btnPomoPause) {
    btnPomoPause.addEventListener('click', () => {
        pausePomodoro();
        sendWSMessage('trigger_pomodoro_ws', { action: 'stop' });
    });
}

if (btnPomoReset) {
    btnPomoReset.addEventListener('click', () => {
        resetPomodoro();
        sendWSMessage('trigger_pomodoro_ws', { action: 'stop' });
    });
}

// ==========================================================================
// MUSIC PLAYER SYSTEM
// ==========================================================================
const btnMusicPrev = document.getElementById('btnMusicPrev');
const btnMusicPlay = document.getElementById('btnMusicPlay');
const btnMusicStop = document.getElementById('btnMusicStop');
const btnMusicNext = document.getElementById('btnMusicNext');
const volumeRange = document.getElementById('volumeRange');
const volumeValue = document.getElementById('volumeValue');
const nowPlayingText = document.getElementById('nowPlayingText');
const musicCount = document.getElementById('musicCount');
const musicList = document.getElementById('musicList');
const playPauseIcon = document.getElementById('playPauseIcon');

if (btnMusicPlay) {
    btnMusicPlay.addEventListener('click', () => {
        sendWSMessage('music_control', { action: 'play' });
    });
}
if (btnMusicStop) {
    btnMusicStop.addEventListener('click', () => {
        sendWSMessage('music_control', { action: 'stop' });
    });
}
if (btnMusicPrev) {
    btnMusicPrev.addEventListener('click', () => {
        sendWSMessage('music_control', { action: 'prev' });
    });
}
if (btnMusicNext) {
    btnMusicNext.addEventListener('click', () => {
        sendWSMessage('music_control', { action: 'next' });
    });
}
if (volumeRange) {
    volumeRange.addEventListener('input', () => {
        const val = volumeRange.value;
        if (volumeValue) volumeValue.textContent = `${val}%`;
        sendWSMessage('set_volume_system', { value: parseInt(val) });
    });
}

function renderMusicList(songs, status) {
    if (!musicList) return;
    if (musicCount) musicCount.textContent = songs.length;
    
    // Update play/pause icon
    if (playPauseIcon) {
        if (status.playing && !status.paused) {
            playPauseIcon.innerHTML = `<rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect>`;
        } else {
            playPauseIcon.innerHTML = `<polygon points="5 3 19 12 5 21 5 3"></polygon>`;
        }
    }
    
    // Update Now Playing Title
    if (nowPlayingText) {
        if (status.playing) {
            nowPlayingText.textContent = `Memutar: ${status.song}`;
        } else {
            nowPlayingText.textContent = "Tidak ada musik diputar";
        }
    }

    if (songs.length === 0) {
        musicList.innerHTML = '<div class="empty-state">Tidak ada file musik (.mp3, .wav, .ogg) di folder music/.</div>';
        return;
    }

    musicList.innerHTML = songs.map((song, index) => {
        const isActive = status.playing && status.song === song;
        return `
            <div class="music-item ${isActive ? 'active' : ''}" data-song="${escapeHTML(song)}">
                <span class="song-name">${escapeHTML(song)}</span>
                ${isActive ? '<span class="play-indicator">▶</span>' : ''}
            </div>
        `;
    }).join('');

    // Click on song item to play
    musicList.querySelectorAll('.music-item').forEach(item => {
        item.addEventListener('click', () => {
            const song = item.getAttribute('data-song');
            sendWSMessage('music_control', { action: 'play', song: song });
        });
    });
}

// ==========================================================================
// SYSTEM PERFORMANCE MONITOR
// ==========================================================================
const cpuFill = document.getElementById('cpuFill');
const cpuVal = document.getElementById('cpuVal');
const ramFill = document.getElementById('ramFill');
const ramVal = document.getElementById('ramVal');
const batFill = document.getElementById('batFill');
const batVal = document.getElementById('batVal');
const batteryContainer = document.getElementById('batteryContainer');

function updateDeviceStats(stats) {
    // CPU Load (Load average 1 min is mapped roughly to cores, e.g. 4 cores = 100%)
    if (cpuFill && cpuVal) {
        const load = parseFloat(stats.cpu) || 0.0;
        const loadPercent = Math.min(100, Math.round(load * 25));
        cpuFill.style.width = `${loadPercent}%`;
        cpuVal.textContent = stats.cpu;
    }
    
    // RAM usage percent
    if (ramFill && ramVal) {
        const ramPercent = stats.ram; // e.g. "57%"
        ramFill.style.width = ramPercent;
        ramVal.textContent = ramPercent;
    }
    
    // Battery Status
    if (batFill && batVal && batteryContainer) {
        if (stats.battery === "N/A" || stats.battery.includes("Tidak") || stats.battery.includes("Error")) {
            batteryContainer.style.display = "none";
        } else {
            batteryContainer.style.display = "flex";
            const batPercent = stats.battery; // e.g. "85%"
            batFill.style.width = batPercent;
            batVal.textContent = batPercent;
            
            if (stats.battery_charging) {
                batteryContainer.classList.add('charging');
            } else {
                batteryContainer.classList.remove('charging');
            }
        }
    }
}

