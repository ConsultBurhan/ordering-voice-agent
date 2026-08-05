import { SmallWebRTCTransport } from '@pipecat-ai/small-webrtc-transport';
import {
  AggregationType,
  BotOutputData,
  Participant,
  PipecatClient,
  PipecatClientOptions,
  TranscriptData,
  TransportState,
} from '@pipecat-ai/client-js';
import { Avatar } from './components/Avatar';
import { OrderCart } from './components/OrderCart';
import { Visualizer } from './components/Visualizer';

class VoiceOrderingKioskApp {
  private declare connectBtn: HTMLButtonElement;
  private declare disconnectBtn: HTMLButtonElement;
  private declare botAudioElement: HTMLAudioElement;

  private debugLog: HTMLElement | null = null;
  private statusSpan: HTMLElement | null = null;
  private statusBadge: HTMLElement | null = null;
  private transcriptBox: HTMLElement | null = null;
  private emptyState: HTMLElement | null = null;

  private avatar!: Avatar;
  private cart!: OrderCart;
  private visualizer!: Visualizer;

  private declare pcClient: PipecatClient;

  private declare baseUrl: string;
  private declare startUrl: string;
  private declare apiKey: string;

  constructor() {
    this.setupEnvironmentVariables();
    this.setupDOMElements();
    this.initializeComponents();
    this.setupDOMEventListeners();
    this.initializePipecatClient();
  }

  private setupEnvironmentVariables() {
    this.baseUrl = import.meta.env.VITE_PIPECAT_BASE_URL || 'http://localhost:7860';
    this.startUrl = `${this.baseUrl}/start`;
    this.apiKey = import.meta.env.VITE_PIPECAT_PUBLIC_API;
  }

  private initializeComponents(): void {
    this.avatar = new Avatar('avatar-container-root');
    this.cart = new OrderCart('cart-container-root', (item) => {
      this.avatar.triggerSuccessGesture(item.name);
    });
    this.visualizer = new Visualizer('visualizer-root', 28);
  }

  private initializePipecatClient(): void {
    const opts: PipecatClientOptions = {
      transport: new SmallWebRTCTransport(),
      enableMic: true,
      enableCam: false,
      callbacks: {
        onTransportStateChanged: (state: TransportState) => {
          this.log(`Transport state: ${state}`);
        },
        onConnected: () => {
          this.onConnectedHandler();
        },
        onBotReady: () => {
          this.log('Bot is ready to take orders.');
          this.avatar.setState('connected', 'Voice Assistant Ready — Speak your order!');
        },
        onDisconnected: () => {
          this.onDisconnectedHandler();
        },
        onUserStartedSpeaking: () => {
          this.log('User started speaking.');
          this.avatar.setState('user-speaking');
          this.visualizer.setMode('user');
          this.setStatusBadgeState('user-speaking', 'Listening to order...');
        },
        onUserStoppedSpeaking: () => {
          this.log('User stopped speaking.');
          this.avatar.setState('processing');
          this.visualizer.setMode('idle');
          this.setStatusBadgeState('connected', 'Processing order...');
        },
        onBotStartedSpeaking: () => {
          this.log('Bot started speaking.');
          this.avatar.setState('bot-speaking');
          this.visualizer.setMode('bot');
          this.setStatusBadgeState('bot-speaking', 'Assistant speaking...');
        },
        onBotStoppedSpeaking: () => {
          this.log('Bot stopped speaking.');
          this.avatar.setState('connected');
          this.visualizer.setMode('idle');
          this.setStatusBadgeState('connected', 'Order Assistant Ready');
        },
        onUserTranscript: (transcript: TranscriptData) => {
          if (transcript.final) {
            this.log(`User transcript: ${transcript.text}`);
            this.addTranscriptBubble('user', transcript.text);
            this.cart.parseTranscript(transcript.text);
          }
        },
        onBotOutput: (data: BotOutputData) => {
          if (data.aggregated_by === AggregationType.SENTENCE) {
            this.log(`Bot output: ${data.text}`);
            this.addTranscriptBubble('bot', data.text);
            this.cart.parseTranscript(data.text);
          }
        },
        onTrackStarted: (
          track: MediaStreamTrack,
          participant?: Participant
        ) => {
          if (!participant?.local) {
            this.onBotTrackStarted(track);
          }
        },
        onServerMessage: (msg: unknown) => {
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

  private setupDOMElements(): void {
    this.connectBtn = document.getElementById('connect-btn') as HTMLButtonElement;
    this.disconnectBtn = document.getElementById('disconnect-btn') as HTMLButtonElement;
    this.debugLog = document.getElementById('debug-log');
    this.statusSpan = document.getElementById('connection-status');
    this.statusBadge = document.getElementById('status-badge');
    this.botAudioElement = document.getElementById('bot-audio') as HTMLAudioElement;
    this.transcriptBox = document.getElementById('transcript-box');
    this.emptyState = document.getElementById('empty-state');
  }

  private setupDOMEventListeners(): void {
    this.connectBtn.addEventListener('click', () => this.start());
    this.disconnectBtn.addEventListener('click', () => this.stop());

    // Prompt Chips Listener
    document.querySelectorAll('.prompt-chip').forEach((chip) => {
      chip.addEventListener('click', (e) => {
        const promptText = (e.currentTarget as HTMLElement).getAttribute('data-prompt');
        if (promptText) {
          this.log(`Quick prompt triggered: "${promptText}"`);
          this.cart.parseTranscript(promptText);
          this.addTranscriptBubble('user', promptText);
        }
      });
    });
  }

  private setStatusBadgeState(state: 'disconnected' | 'connected' | 'user-speaking' | 'bot-speaking', label: string) {
    if (!this.statusBadge || !this.statusSpan) return;
    this.statusBadge.className = `status-badge ${state}`;
    this.statusSpan.textContent = label;
  }

  private log(message: string): void {
    if (!this.debugLog) return;
    const entry = document.createElement('div');
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    if (message.startsWith('User transcript: ')) {
      entry.style.color = '#818cf8';
    } else if (message.startsWith('Bot output: ') || message.startsWith('Bot transcript: ')) {
      entry.style.color = '#f472b6';
    }
    this.debugLog.appendChild(entry);
    this.debugLog.scrollTop = this.debugLog.scrollHeight;
  }

  private clearAllLogs() {
    if (this.debugLog) this.debugLog.innerText = '';
  }

  private addTranscriptBubble(role: 'user' | 'bot', text: string): void {
    if (!this.transcriptBox) return;

    if (this.emptyState) {
      this.emptyState.style.display = 'none';
    }

    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;
    bubble.textContent = text;
    this.transcriptBox.appendChild(bubble);
    this.transcriptBox.scrollTop = this.transcriptBox.scrollHeight;
  }

  private onConnectedHandler() {
    this.setStatusBadgeState('connected', 'Connected');
    if (this.connectBtn) this.connectBtn.disabled = true;
    if (this.disconnectBtn) this.disconnectBtn.disabled = false;
    this.avatar.setState('connected');
  }

  private onDisconnectedHandler() {
    this.setStatusBadgeState('disconnected', 'Offline');
    if (this.connectBtn) this.connectBtn.disabled = false;
    if (this.disconnectBtn) this.disconnectBtn.disabled = true;
    this.avatar.setState('disconnected');
    this.visualizer.setMode('idle');
  }

  private onBotTrackStarted(track: MediaStreamTrack) {
    if (track.kind === 'audio') {
      this.botAudioElement.srcObject = new MediaStream([track]);
    }
  }

  private async start(): Promise<void> {
    this.clearAllLogs();
    this.avatar.setState('processing', 'Connecting device & voice bot...');
    await this.pcClient.initDevices();
    this.connectBtn.disabled = true;
    try {
      this.setStatusBadgeState('connected', 'Starting Session...');
      const headers = new Headers();
      if (this.apiKey) {
        headers.append("Authorization", `Bearer ${this.apiKey}`);
      }

      const startBotResult = await this.pcClient.startBot({
        endpoint: this.startUrl,
        headers: headers,
        requestData: {
          createDailyRoom: false,
          enableDefaultIceServers: true,
          transport: "webrtc"
        }
      });

      await this.pcClient.connect(startBotResult as any);
    } catch (e) {
      console.error(`Failed to connect ${e}`);
      this.stop();
    }
  }

  private stop(): void {
    void this.pcClient.disconnect();
    this.onDisconnectedHandler();
  }
}

new VoiceOrderingKioskApp();
