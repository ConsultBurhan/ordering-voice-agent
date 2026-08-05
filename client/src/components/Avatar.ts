export type AvatarState = 'disconnected' | 'connected' | 'user-speaking' | 'processing' | 'bot-speaking' | 'order-success';

export class Avatar {
  private container: HTMLElement;
  private avatarEl: HTMLElement | null = null;
  private stateCaption: HTMLElement | null = null;
  private currentState: AvatarState = 'disconnected';
  private gestureTimer: number | null = null;

  constructor(containerId: string) {
    const el = document.getElementById(containerId);
    if (!el) {
      throw new Error(`Container element with id '${containerId}' not found.`);
    }
    this.container = el;
    this.render();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="avatar-wrapper state-disconnected" id="avatar-wrapper">
        <!-- Soundwave Equalizer Rings -->
        <div class="soundwave-ring ring-1"></div>
        <div class="soundwave-ring ring-2"></div>
        <div class="soundwave-ring ring-3"></div>

        <!-- Thinking Halo Ring -->
        <div class="halo-ring"></div>

        <!-- Main Avatar Sphere & Character -->
        <div class="avatar-body-container" id="avatar-body">
          <svg viewBox="0 0 200 200" class="avatar-svg" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <radialGradient id="headGrad" cx="40%" cy="40%" r="60%">
                <stop offset="0%" stop-color="#818cf8" />
                <stop offset="60%" stop-color="#4f46e5" />
                <stop offset="100%" stop-color="#312e81" />
              </radialGradient>
              
              <radialGradient id="listeningGrad" cx="40%" cy="40%" r="60%">
                <stop offset="0%" stop-color="#fbbf24" />
                <stop offset="60%" stop-color="#d97706" />
                <stop offset="100%" stop-color="#78350f" />
              </radialGradient>

              <radialGradient id="speakingGrad" cx="40%" cy="40%" r="60%">
                <stop offset="0%" stop-color="#f472b6" />
                <stop offset="60%" stop-color="#db2777" />
                <stop offset="100%" stop-color="#831843" />
              </radialGradient>

              <radialGradient id="successGrad" cx="40%" cy="40%" r="60%">
                <stop offset="0%" stop-color="#34d399" />
                <stop offset="60%" stop-color="#059669" />
                <stop offset="100%" stop-color="#064e3b" />
              </radialGradient>
            </defs>

            <!-- Base Head Outer Shape -->
            <circle cx="100" cy="100" r="75" class="avatar-head-base" />

            <!-- Cheeks Blush -->
            <circle cx="62" cy="118" r="10" class="blush blush-left" fill="#f43f5e" opacity="0.3" />
            <circle cx="138" cy="118" r="10" class="blush blush-right" fill="#f43f5e" opacity="0.3" />

            <!-- Left Eye -->
            <g class="eye eye-left">
              <ellipse cx="68" cy="90" rx="10" ry="12" fill="#ffffff" />
              <circle cx="68" cy="90" r="5" class="pupil pupil-left" fill="#0f172a" />
              <circle cx="70" cy="87" r="2" fill="#ffffff" />
              <!-- Closed Eye Line -->
              <path class="eye-closed" d="M 58 90 Q 68 97 78 90" stroke="#94a3b8" stroke-width="3" stroke-linecap="round" fill="none" />
            </g>

            <!-- Right Eye -->
            <g class="eye eye-right">
              <ellipse cx="132" cy="90" rx="10" ry="12" fill="#ffffff" />
              <circle cx="132" cy="90" r="5" class="pupil pupil-right" fill="#0f172a" />
              <circle cx="134" cy="87" r="2" fill="#ffffff" />
              <!-- Closed Eye Line -->
              <path class="eye-closed" d="M 122 90 Q 132 97 142 90" stroke="#94a3b8" stroke-width="3" stroke-linecap="round" fill="none" />
            </g>

            <!-- Eyebrows -->
            <path class="eyebrow eyebrow-left" d="M 58 72 Q 68 68 78 72" stroke="#ffffff" stroke-width="3" stroke-linecap="round" fill="none" />
            <path class="eyebrow eyebrow-right" d="M 122 72 Q 132 68 142 72" stroke="#ffffff" stroke-width="3" stroke-linecap="round" fill="none" />

            <!-- Dynamic Animated Mouth -->
            <g class="mouth-group">
              <!-- Neutral Smile -->
              <path class="mouth mouth-smile" d="M 80 122 Q 100 140 120 122" stroke="#ffffff" stroke-width="4" stroke-linecap="round" fill="none" />
              <!-- Talking Mouth -->
              <ellipse class="mouth mouth-talk" cx="100" cy="128" rx="12" ry="14" fill="#0f172a" stroke="#ffffff" stroke-width="3" />
              <!-- Surprised/Listening Mouth -->
              <circle class="mouth mouth-listen" cx="100" cy="126" r="7" fill="#ffffff" />
              <!-- Sleeping Mouth -->
              <path class="mouth mouth-sleep" d="M 88 126 Q 100 131 112 126" stroke="#94a3b8" stroke-width="3" stroke-linecap="round" fill="none" />
            </g>

            <!-- Animated Arm/Hand Gesture -->
            <g class="avatar-hand-gesture" id="avatar-hand">
              <path d="M 155 125 Q 175 110 182 95" stroke="#818cf8" stroke-width="5" stroke-linecap="round" fill="none" />
              <circle cx="182" cy="93" r="7" fill="#818cf8" />
              <text x="170" y="80" font-size="18" class="gesture-icon">👍</text>
            </g>
          </svg>
        </div>
      </div>

      <!-- State Caption Badge -->
      <div class="avatar-caption-badge" id="avatar-caption">
        <span class="caption-pulse-dot"></span>
        <span class="caption-text" id="caption-text">Click Connect to Start</span>
      </div>
    `;

    this.avatarEl = document.getElementById('avatar-wrapper');
    this.stateCaption = document.getElementById('caption-text');
  }

  public setState(state: AvatarState, caption?: string): void {
    this.currentState = state;
    if (!this.avatarEl) return;

    this.avatarEl.className = 'avatar-wrapper';
    this.avatarEl.classList.add(`state-${state}`);

    const defaultCaptions: Record<AvatarState, string> = {
      'disconnected': 'Offline — Click Connect',
      'connected': 'Order Assistant Ready — Speak into mic',
      'user-speaking': 'Listening to your order...',
      'processing': 'Thinking & building order...',
      'bot-speaking': 'Assistant speaking...',
      'order-success': 'Item added to order!'
    };

    if (this.stateCaption) {
      this.stateCaption.textContent = caption || defaultCaptions[state];
    }
  }

  public triggerSuccessGesture(itemName?: string): void {
    const prevState = this.currentState;
    this.setState('order-success', itemName ? `Added ${itemName}!` : 'Got it! Added to order!');

    if (this.gestureTimer) {
      window.clearTimeout(this.gestureTimer);
    }

    this.gestureTimer = window.setTimeout(() => {
      this.setState(prevState);
    }, 2500);
  }

  public getState(): AvatarState {
    return this.currentState;
  }
}
