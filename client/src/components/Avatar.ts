import bkCrewAvatarUrl from '../bk_crew_avatar.jpg';

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

        <!-- Main 3D Burger King Crew Member Character Portrait -->
        <div class="avatar-body-container" id="avatar-body">
          <div class="crew-avatar-frame">
            <img src="${bkCrewAvatarUrl}" alt="Burger King Assistant" class="crew-avatar-img" />
            <div class="avatar-status-glow"></div>
            <div class="avatar-headset-indicator">
              <span class="headset-pulse"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- State Caption Badge -->
      <div class="avatar-caption-badge" id="avatar-caption">
        <span class="caption-pulse-dot"></span>
        <span class="caption-text" id="caption-text">Click "Start Voice Ordering" to talk</span>
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
      'disconnected': 'Offline — Click Start Voice Ordering',
      'connected': 'BK Voice Bot Ready — Speak into mic',
      'user-speaking': 'Listening to your request...',
      'processing': 'Processing your request...',
      'bot-speaking': 'BK Assistant speaking...',
      'order-success': 'Got it!'
    };

    if (this.stateCaption) {
      this.stateCaption.textContent = caption || defaultCaptions[state];
    }
  }

  public triggerSuccessGesture(itemName?: string): void {
    const prevState = this.currentState;
    this.setState('order-success', itemName ? `Showing ${itemName}!` : 'Got it!');

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
