export class Visualizer {
  private container: HTMLElement;
  private bars: HTMLElement[] = [];
  private animInterval: number | null = null;
  private isActive: boolean = false;
  private mode: 'user' | 'bot' | 'idle' = 'idle';

  constructor(containerId: string, barCount: number = 24) {
    const el = document.getElementById(containerId);
    if (!el) {
      throw new Error(`Visualizer container element '${containerId}' not found.`);
    }
    this.container = el;
    this.render(barCount);
  }

  private render(barCount: number): void {
    this.container.innerHTML = '';
    this.bars = [];
    const wrapper = document.createElement('div');
    wrapper.className = 'visualizer-bars-wrapper';

    for (let i = 0; i < barCount; i++) {
      const bar = document.createElement('div');
      bar.className = 'v-bar';
      wrapper.appendChild(bar);
      this.bars.push(bar);
    }

    this.container.appendChild(wrapper);
  }

  public setMode(mode: 'user' | 'bot' | 'idle'): void {
    this.mode = mode;
    this.container.className = `visualizer-container mode-${mode}`;

    if (mode === 'idle') {
      this.stop();
    } else {
      this.start();
    }
  }

  private start(): void {
    if (this.isActive) return;
    this.isActive = true;

    const animate = () => {
      if (!this.isActive) return;

      this.bars.forEach((bar, index) => {
        let heightPercent = 15;
        if (this.mode === 'user') {
          // Amber pulse pattern
          heightPercent = 20 + Math.sin(Date.now() / 150 + index) * 35 + Math.random() * 45;
        } else if (this.mode === 'bot') {
          // Magenta pulse pattern
          heightPercent = 25 + Math.cos(Date.now() / 120 + index * 0.8) * 40 + Math.random() * 35;
        }
        bar.style.height = `${Math.min(100, Math.max(10, heightPercent))}%`;
      });

      this.animInterval = requestAnimationFrame(animate);
    };

    animate();
  }

  private stop(): void {
    this.isActive = false;
    if (this.animInterval) {
      cancelAnimationFrame(this.animInterval);
      this.animInterval = null;
    }
    this.bars.forEach((bar) => {
      bar.style.height = '12%';
    });
  }
}
