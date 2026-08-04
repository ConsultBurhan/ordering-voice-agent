import { WebSocketTransport } from '@pipecat-ai/websocket-transport';
import { AggregationType, PipecatClient, } from '@pipecat-ai/client-js';
class WebSocketApp {
    debugLog = null;
    statusSpan = null;
    statusBadge = null;
    voiceOrb = null;
    stateCaption = null;
    transcriptBox = null;
    emptyState = null;
    constructor() {
        this.setupEnvironmentVariables();
        this.setupDOMElements();
        this.setupDOMEventListeners();
        this.initializePipecatClient();
    }
    setupEnvironmentVariables() {
        this.baseUrl = import.meta.env.VITE_PIPECAT_BASE_URL || 'http://localhost:7860';
        this.startUrl = `${this.baseUrl}/start`;
        this.apiKey = import.meta.env.VITE_PIPECAT_PUBLIC_API;
    }
    initializePipecatClient() {
        const opts = {
            transport: new WebSocketTransport(),
            enableMic: true,
            enableCam: false,
            callbacks: {
                onTransportStateChanged: (state) => {
                    this.log(`Transport state: ${state}`);
                },
                onConnected: () => {
                    this.onConnectedHandler();
                },
                onBotReady: () => {
                    this.log('Bot is ready.');
                    this.setOrbState('connected', 'Bot ready — speak into mic');
                },
                onDisconnected: () => {
                    this.onDisconnectedHandler();
                },
                onUserStartedSpeaking: () => {
                    this.log('User started speaking.');
                    this.setOrbState('user-speaking', 'Listening to you...');
                },
                onUserStoppedSpeaking: () => {
                    this.log('User stopped speaking.');
                    this.setOrbState('connected', 'Processing...');
                },
                onBotStartedSpeaking: () => {
                    this.log('Bot started speaking.');
                    this.setOrbState('bot-speaking', 'Agent speaking...');
                },
                onBotStoppedSpeaking: () => {
                    this.log('Bot stopped speaking.');
                    this.setOrbState('connected', 'Listening...');
                },
                onUserTranscript: (transcript) => {
                    if (transcript.final) {
                        this.log(`User transcript: ${transcript.text}`);
                        this.addTranscriptBubble('user', transcript.text);
                    }
                },
                onBotOutput: (data) => {
                    if (data.aggregated_by === AggregationType.SENTENCE) {
                        this.log(`Bot output: ${data.text}`);
                        this.addTranscriptBubble('bot', data.text);
                    }
                },
                onTrackStarted: (track, participant) => {
                    if (!participant?.local) {
                        this.onBotTrackStarted(track);
                    }
                },
                onServerMessage: (msg) => {
                    this.log(`Server message: ${JSON.stringify(msg)}`);
                },
            },
        };
        this.pcClient = new PipecatClient(opts);
        // @ts-ignore
        window.webapp = this;
        // @ts-ignore
        window.client = this.pcClient;
    }
    setupDOMElements() {
        this.connectBtn = document.getElementById('connect-btn');
        this.disconnectBtn = document.getElementById('disconnect-btn');
        this.debugLog = document.getElementById('debug-log');
        this.statusSpan = document.getElementById('connection-status');
        this.statusBadge = document.getElementById('status-badge');
        this.botAudioElement = document.getElementById('bot-audio');
        this.voiceOrb = document.getElementById('voice-orb');
        this.stateCaption = document.getElementById('state-caption');
        this.transcriptBox = document.getElementById('transcript-box');
        this.emptyState = document.getElementById('empty-state');
    }
    setupDOMEventListeners() {
        this.connectBtn.addEventListener('click', () => this.start());
        this.disconnectBtn.addEventListener('click', () => this.stop());
    }
    log(message) {
        if (!this.debugLog)
            return;
        const entry = document.createElement('div');
        entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        if (message.startsWith('User transcript: ')) {
            entry.style.color = '#818cf8';
        }
        else if (message.startsWith('Bot output: ') || message.startsWith('Bot transcript: ')) {
            entry.style.color = '#f472b6';
        }
        this.debugLog.appendChild(entry);
        this.debugLog.scrollTop = this.debugLog.scrollHeight;
    }
    clearAllLogs() {
        if (this.debugLog)
            this.debugLog.innerText = '';
    }
    setOrbState(state, caption) {
        if (!this.voiceOrb || !this.stateCaption || !this.statusBadge)
            return;
        this.voiceOrb.className = 'orb';
        this.statusBadge.className = 'status-badge';
        if (state === 'connected') {
            this.voiceOrb.classList.add('state-connected');
            this.statusBadge.classList.add('connected');
        }
        else if (state === 'user-speaking') {
            this.voiceOrb.classList.add('state-user-speaking');
            this.statusBadge.classList.add('user-speaking');
        }
        else if (state === 'bot-speaking') {
            this.voiceOrb.classList.add('state-bot-speaking');
            this.statusBadge.classList.add('speaking');
        }
        this.stateCaption.textContent = caption;
    }
    updateStatus(status) {
        if (this.statusSpan) {
            this.statusSpan.textContent = status;
        }
        this.log(`Status: ${status}`);
    }
    addTranscriptBubble(role, text) {
        if (!this.transcriptBox)
            return;
        if (this.emptyState) {
            this.emptyState.style.display = 'none';
        }
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${role}`;
        bubble.textContent = text;
        this.transcriptBox.appendChild(bubble);
        this.transcriptBox.scrollTop = this.transcriptBox.scrollHeight;
    }
    onConnectedHandler() {
        this.updateStatus('Connected');
        if (this.connectBtn)
            this.connectBtn.disabled = true;
        if (this.disconnectBtn)
            this.disconnectBtn.disabled = false;
        this.setOrbState('connected', 'Connected — Waiting for bot');
    }
    onDisconnectedHandler() {
        this.updateStatus('Disconnected');
        if (this.connectBtn)
            this.connectBtn.disabled = false;
        if (this.disconnectBtn)
            this.disconnectBtn.disabled = true;
        this.setOrbState('disconnected', 'Click Connect to Start');
    }
    onBotTrackStarted(track) {
        if (track.kind === 'audio') {
            this.botAudioElement.srcObject = new MediaStream([track]);
        }
    }
    async start() {
        this.clearAllLogs();
        this.setOrbState('connected', 'Connecting device & bot...');
        await this.pcClient.initDevices();
        this.connectBtn.disabled = true;
        try {
            this.updateStatus('Starting bot session...');
            const headers = new Headers();
            if (this.apiKey) {
                headers.append("Authorization", `Bearer ${this.apiKey}`);
            }
            const startBotResponseTransformerWebsocket = ({ token, wsUrl }) => {
                return {
                    wsUrl: token ? `${wsUrl}?token=${encodeURIComponent(token)}` : wsUrl,
                };
            };
            const startBotResult = await this.pcClient.startBot({
                endpoint: this.startUrl,
                headers: headers,
                requestData: {
                    transport: "websocket"
                }
            });
            // @ts-ignore
            const wsConnectionParams = startBotResponseTransformerWebsocket(startBotResult);
            await this.pcClient.connect(wsConnectionParams);
        }
        catch (e) {
            console.error(`Failed to connect ${e}`);
            this.stop();
        }
    }
    stop() {
        void this.pcClient.disconnect();
        this.onDisconnectedHandler();
    }
}
const websocketApp = new WebSocketApp();
