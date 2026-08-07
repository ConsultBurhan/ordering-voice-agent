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
import { Visualizer } from './components/Visualizer';

interface MenuCategory {
  id: string;
  name: string;
  name_ar?: string;
  item_count: number;
}

interface MenuItem {
  id: string;
  name: string;
  name_ar?: string;
  price: number;
  formatted_price: string;
  category: string;
  description: string;
  image_url: string;
  allergens?: string[];
  calories?: number;
}

interface CustomizationChoice {
  name: string;
  extra_price: number;
  formatted_price: string;
}

interface CustomizationGroup {
  option: string;
  choices: CustomizationChoice[];
}

interface CartItemData {
  item_id: string;
  name: string;
  quantity: number;
  unit_price: number;
  extra_price: number;
  price: number;
  line_total: number;
  formatted_price: string;
  formatted_total: string;
  customizations: Record<string, any>;
}

interface KioskOrderState {
  session_id?: string;
  current_stage?: string;
  cart?: CartItemData[];
  current_item?: Record<string, any>;
  subtotal?: number;
  tax?: number;
  discount_amount?: number;
  total?: number;
  formatted_subtotal?: string;
  formatted_tax?: string;
  formatted_discount?: string;
  formatted_total?: string;
  currency?: string;
  order_type?: string;
  payment_status?: string;
  order_id?: string;
}

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
  private visualizer!: Visualizer;

  private declare pcClient: PipecatClient;

  private declare baseUrl: string;
  private declare startUrl: string;
  private declare apiKey: string;

  // Kiosk Adaptive Stage Display Elements
  private stagePill: HTMLElement | null = null;
  private orderTypePill: HTMLElement | null = null;
  private categoriesContainer: HTMLElement | null = null;
  private categoryTabs: HTMLElement | null = null;
  private productsContainer: HTMLElement | null = null;
  private customizeHero: HTMLElement | null = null;
  private customizeOptionsContainer: HTMLElement | null = null;
  private cartItemsContainer: HTMLElement | null = null;
  private checkoutSummaryContainer: HTMLElement | null = null;
  private paymentContainer: HTMLElement | null = null;
  private completeContainer: HTMLElement | null = null;
  private productDetailContainer: HTMLElement | null = null;
  private productDetailBackBtn: HTMLButtonElement | null = null;
  private footerItemCount: HTMLElement | null = null;
  private footerTotal: HTMLElement | null = null;

  // Local State
  private menuData: { categories: MenuCategory[]; items: MenuItem[]; customizations: Record<string, CustomizationGroup[]> } | null = null;
  private currentState: KioskOrderState = {};
  private activeCategoryName: string = 'Chicken Meals';

  // Subtitle Overlay elements & Fade Timers
  private botSubtitleBox: HTMLElement | null = null;
  private botSubtitleText: HTMLElement | null = null;
  private userSubtitleBox: HTMLElement | null = null;
  private userSubtitleText: HTMLElement | null = null;

  private botFadeTimer: number | null = null;
  private userFadeTimer: number | null = null;

  constructor() {
    this.setupEnvironmentVariables();
    this.setupDOMElements();
    this.initializeComponents();
    this.setupDOMEventListeners();
    this.initializePipecatClient();
    this.renderDefaultMockMenu();
  }

  private setupEnvironmentVariables() {
    this.baseUrl = import.meta.env.VITE_PIPECAT_BASE_URL || 'http://localhost:7860';
    this.startUrl = `${this.baseUrl}/start`;
    this.apiKey = import.meta.env.VITE_PIPECAT_PUBLIC_API;
  }

  private initializeComponents(): void {
    this.avatar = new Avatar('avatar-container-root');
    this.visualizer = new Visualizer('visualizer-root', 28);
  }

  private setupDOMElements(): void {
    this.connectBtn = document.getElementById('connect-btn') as HTMLButtonElement;
    this.disconnectBtn = document.getElementById('disconnect-btn') as HTMLButtonElement;
    this.debugLog = document.getElementById('debug-log');
    this.statusSpan = document.getElementById('connection-status');
    this.statusBadge = document.getElementById('status-badge');
    this.botAudioElement = document.getElementById('bot-audio') as HTMLAudioElement;

    // Live Subtitle Overlay elements
    this.botSubtitleBox = document.getElementById('bot-subtitle-box');
    this.botSubtitleText = document.getElementById('bot-subtitle-text');
    this.userSubtitleBox = document.getElementById('user-subtitle-box');
    this.userSubtitleText = document.getElementById('user-subtitle-text');

    // Stage Display elements
    this.stagePill = document.getElementById('current-stage-pill');
    this.orderTypePill = document.getElementById('kiosk-order-type');
    this.categoriesContainer = document.getElementById('categories-container');
    this.categoryTabs = document.getElementById('category-tabs');
    this.productsContainer = document.getElementById('products-container');
    this.customizeHero = document.getElementById('customize-hero');
    this.customizeOptionsContainer = document.getElementById('customize-options-container');
    this.cartItemsContainer = document.getElementById('cart-items-container');
    this.checkoutSummaryContainer = document.getElementById('checkout-summary-container');
    this.paymentContainer = document.getElementById('payment-container');
    this.completeContainer = document.getElementById('complete-container');
    this.productDetailContainer = document.getElementById('product-detail-container');
    this.productDetailBackBtn = document.getElementById('product-detail-back-btn') as HTMLButtonElement;
    if (this.productDetailBackBtn) {
      this.productDetailBackBtn.addEventListener('click', () => {
        this.switchStageView('browse_menu');
      });
    }
    this.footerItemCount = document.getElementById('footer-item-count');
    this.footerTotal = document.getElementById('kiosk-footer-total');
  }

  private setupDOMEventListeners(): void {
    this.connectBtn.addEventListener('click', () => this.start());
    this.disconnectBtn.addEventListener('click', () => this.stop());
  }

  private renderDefaultMockMenu(): void {
    this.menuData = {
      categories: [
        { id: '1', name: 'Chicken Meals', item_count: 2 },
        { id: '2', name: 'Sides & Salads', item_count: 3 },
        { id: '3', name: 'Desserts & Drinks', item_count: 4 },
      ],
      items: [
        {
          id: '1',
          name: 'Spicy Crispy Fillet Meal',
          price: 2.65,
          formatted_price: 'KWD 2.650',
          category: 'Chicken Meals',
          description: 'A spicy golden chicken fillet with Jalapeno and House Sauce.',
          image_url: 'https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/6393.jpg',
        },
        {
          id: '2',
          name: 'Chicken Royale Meal',
          price: 2.35,
          formatted_price: 'KWD 2.350',
          category: 'Chicken Meals',
          description: 'Crispy chicken patty with lettuce and mayo in a sesame bun.',
          image_url: 'https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/6030.jpg',
        },
        {
          id: '3',
          name: 'Chicken Fries',
          price: 1.0,
          formatted_price: 'KWD 1.000',
          category: 'Sides & Salads',
          description: 'Famous chicken fries served with BBQ sauce.',
          image_url: 'https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/208100.jpg',
        },
        {
          id: '4',
          name: 'Chicken Tenders 6 Pcs',
          price: 1.0,
          formatted_price: 'KWD 1.000',
          category: 'Sides & Salads',
          description: '6 pieces of golden tender chicken tenders.',
          image_url: 'https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/208080.jpg',
        },
        {
          id: '5',
          name: 'Mozarella Stick - 4 pieces',
          price: 1.0,
          formatted_price: 'KWD 1.000',
          category: 'Sides & Salads',
          description: 'Mozzarella sticks served with marinara sauce.',
          image_url: 'https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/228443.jpg',
        },
        {
          id: '6',
          name: 'Classic Mojito',
          price: 0.85,
          formatted_price: 'KWD 0.850',
          category: 'Desserts & Drinks',
          description: 'Soda, lime, and fresh mint.',
          image_url: 'https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/248329.jpg',
        },
        {
          id: '7',
          name: 'Blue Lagoon Mojito',
          price: 0.85,
          formatted_price: 'KWD 0.850',
          category: 'Desserts & Drinks',
          description: 'Vibrant soda, lime, and blue lagoon mix.',
          image_url: 'https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/248330.jpg',
        },
        {
          id: '8',
          name: 'King On The Beach Mojito',
          price: 0.85,
          formatted_price: 'KWD 0.850',
          category: 'Desserts & Drinks',
          description: 'Soda, lime, and rich strawberry mix.',
          image_url: 'https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/248331.jpg',
        },
        {
          id: '9',
          name: 'Coca Cola Zero',
          price: 0.45,
          formatted_price: 'KWD 0.450',
          category: 'Desserts & Drinks',
          description: 'Zero sugar Coca-Cola.',
          image_url: 'https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/248284.jpg',
        },
      ],
      customizations: {},
    };

    this.renderCategoriesView();
    this.renderProductsView('Chicken Meals');
    this.switchStageView('welcome');
  }

  // ── Stage View Switcher ───────────────────────────────────────────────────

  private switchStageView(stage: string): void {
    const stageName = stage.toLowerCase();
    if (this.stagePill) {
      this.stagePill.textContent = `${stageName.toUpperCase()} STAGE`;
    }

    const views = [
      'view-categories',
      'view-products',
      'view-product-detail',
      'view-customize',
      'view-cart',
      'view-checkout',
      'view-payment',
      'view-complete',
    ];

    views.forEach((v) => {
      const el = document.getElementById(v);
      if (el) el.classList.remove('active');
    });

    let targetId = 'view-categories';
    if (stageName.includes('welcome')) {
      targetId = 'view-categories';
    } else if (stageName.includes('detail') || stageName.includes('product_detail')) {
      targetId = 'view-product-detail';
    } else if (stageName.includes('browse')) {
      targetId = 'view-products';
    } else if (stageName.includes('customize')) {
      targetId = 'view-customize';
    } else if (stageName.includes('cart')) {
      targetId = 'view-cart';
    } else if (stageName.includes('checkout')) {
      targetId = 'view-checkout';
    } else if (stageName.includes('payment')) {
      targetId = 'view-payment';
    } else if (stageName.includes('complete')) {
      targetId = 'view-complete';
    }

    const targetEl = document.getElementById(targetId);
    if (targetEl) targetEl.classList.add('active');
  }

  // ── Rendering Functions ───────────────────────────────────────────────────

  private renderCategoriesView(): void {
    if (!this.categoriesContainer || !this.menuData) return;
    this.categoriesContainer.innerHTML = '';

    this.menuData.categories.forEach((cat) => {
      const card = document.createElement('div');
      card.className = 'category-card';
      card.innerHTML = `
        <div class="category-card-title">${cat.name}</div>
        <div class="category-card-count">${cat.item_count} menu items</div>
      `;
      card.addEventListener('click', () => {
        this.activeCategoryName = cat.name;
        this.renderProductsView(cat.name);
        this.switchStageView('browse_menu');
      });
      this.categoriesContainer!.appendChild(card);
    });
  }

  private renderProductsView(activeCat: string): void {
    if (!this.productsContainer || !this.categoryTabs || !this.menuData) return;
    this.categoryTabs.innerHTML = '';
    this.productsContainer.innerHTML = '';

    // Render Category Tabs
    this.menuData.categories.forEach((cat) => {
      const btn = document.createElement('button');
      btn.className = `tab-btn ${cat.name === activeCat ? 'active' : ''}`;
      btn.textContent = cat.name;
      btn.addEventListener('click', () => {
        this.activeCategoryName = cat.name;
        this.renderProductsView(cat.name);
      });
      this.categoryTabs!.appendChild(btn);
    });

    // Render Filtered Products
    const items = this.menuData.items.filter((i) => i.category === activeCat);
    items.forEach((item) => {
      const card = document.createElement('div');
      card.className = 'product-card';
      card.innerHTML = `
        <img class="product-img" src="${item.image_url}" alt="${item.name}" onerror="this.src='https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/6393.jpg'" />
        <div class="product-info">
          <div class="product-name">${item.name}</div>
          <div class="product-desc">${item.description}</div>
          <div class="product-price-badge">${item.formatted_price}</div>
        </div>
      `;
      card.style.cursor = 'pointer';
      card.addEventListener('click', () => {
        this.renderProductDetailPage(item);
      });
      this.productsContainer!.appendChild(card);
    });
  }

  private renderProductDetailPage(item: MenuItem): void {
    if (!this.productDetailContainer) return;
    const priceHtml = this.formatKWDHtml(item.formatted_price || `KWD ${(item.price || 0).toFixed(3)}`);
    const allergensHtml = (item.allergens || []).map((a) => `<span class="meta-chip">⚠️ Contains ${a}</span>`).join('');
    const caloriesHtml = item.calories ? `<span class="meta-chip">🔥 ${item.calories} Calories</span>` : '';

    this.productDetailContainer.innerHTML = `
      <img class="product-detail-hero" src="${item.image_url}" alt="${item.name}" onerror="this.src='https://lsm.koutfood.com/Content/img/Menu/WhatsApp/2_0/6393.jpg'" />
      <div class="product-detail-header">
        <div>
          <div class="product-detail-title">${item.name}</div>
          ${item.name_ar ? `<div style="font-size: 13px; color: #70594B;">${item.name_ar}</div>` : ''}
          <div class="product-detail-category">${item.category || 'Menu Item'}</div>
        </div>
        <div>${priceHtml}</div>
      </div>
      <div class="product-detail-desc">${item.description}</div>
      <div class="product-detail-meta">
        <span class="meta-chip">👑 Burger King Favorite</span>
        ${caloriesHtml}
        ${allergensHtml}
      </div>
    `;

    this.switchStageView('product-detail');
  }

  private renderCustomizeView(itemName: string, currentCustomizations: Record<string, any> = {}): void {
    if (!this.customizeHero || !this.customizeOptionsContainer || !this.menuData) return;
    const item = this.menuData.items.find((i) => i.name.toLowerCase() === itemName.toLowerCase()) || this.menuData.items[0];

    this.customizeHero.innerHTML = `
      <img src="${item.image_url}" style="width: 80px; height: 80px; border-radius: 12px; object-fit: cover;" />
      <div>
        <div class="customize-hero-title">${item.name}</div>
        <div style="font-size: 13px; color: #a0958e;">Base Price: ${item.formatted_price}</div>
      </div>
    `;

    const groups = this.menuData.customizations[item.name] || [
      {
        option: 'Meal Size Upgrade',
        choices: [
          { name: 'Go Mega', extra_price: 0, formatted_price: 'KWD 0.000' },
          { name: 'Go King', extra_price: 0.2, formatted_price: 'KWD 0.200' },
        ],
      },
      {
        option: 'Side Selection',
        choices: [
          { name: 'Fries', extra_price: 0, formatted_price: 'KWD 0.000' },
          { name: 'Curly Fries', extra_price: 0.15, formatted_price: 'KWD 0.150' },
          { name: 'Onion Rings', extra_price: 0.15, formatted_price: 'KWD 0.150' },
        ],
      },
      {
        option: 'Drink Selection',
        choices: [
          { name: 'Coca Cola', extra_price: 0, formatted_price: 'KWD 0.000' },
          { name: 'Coca Cola Zero', extra_price: 0, formatted_price: 'KWD 0.000' },
          { name: 'Classic Mojito', extra_price: 0.25, formatted_price: 'KWD 0.250' },
        ],
      },
    ];

    this.customizeOptionsContainer.innerHTML = '';
    groups.forEach((grp) => {
      const div = document.createElement('div');
      div.className = 'option-group';
      const selectedVal = currentCustomizations[grp.option] || '';

      const chipsHtml = grp.choices
        .map(
          (c) => `
        <span class="choice-chip ${selectedVal === c.name ? 'selected' : ''}">
          ${c.name} ${c.extra_price > 0 ? `(+${c.formatted_price})` : ''}
        </span>
      `
        )
        .join('');

      div.innerHTML = `
        <div class="option-group-title">${grp.option}</div>
        <div class="chips-wrap">${chipsHtml}</div>
      `;
      this.customizeOptionsContainer!.appendChild(div);
    });
  }

  private renderCartView(cart: CartItemData[], totals: KioskOrderState): void {
    if (!this.cartItemsContainer) return;
    this.cartItemsContainer.innerHTML = '';

    if (!cart || cart.length === 0) {
      this.cartItemsContainer.innerHTML = `<div style="text-align: center; color: #a0958e; padding: 20px;">Your cart is empty.</div>`;
      return;
    }

    cart.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'cart-item-row';

      const custPills = Object.entries(item.customizations || {})
        .map(([k, v]) => `<span class="tag-pill">${v}</span>`)
        .join('');

      row.innerHTML = `
        <div class="item-main-info">
          <div class="item-row-title">${item.quantity}x ${item.name}</div>
          <div class="item-row-tags">${custPills}</div>
        </div>
        <div class="item-row-total">${item.formatted_total || `KWD ${(item.line_total || 0).toFixed(3)}`}</div>
      `;
      this.cartItemsContainer!.appendChild(row);
    });
  }

  private renderCheckoutView(state: KioskOrderState): void {
    if (!this.checkoutSummaryContainer) return;
    const items = state.cart || [];
    const itemsHtml = items.map((i) => `<div class="summary-line"><span>${i.quantity}x ${i.name}</span><span>${i.formatted_total}</span></div>`).join('');

    this.checkoutSummaryContainer.innerHTML = `
      <div style="font-weight: 700; color: #FFC72C;">Order Type: ${state.order_type || 'Dine In'}</div>
      <div style="display: flex; flex-direction: column; gap: 6px;">${itemsHtml}</div>
      <div class="summary-line" style="margin-top: 10px; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 6px;">
        <span>Subtotal</span><span>${state.formatted_subtotal || 'KWD 0.000'}</span>
      </div>
      <div class="summary-line">
        <span>Tax (0%)</span><span>${state.formatted_tax || 'KWD 0.000'}</span>
      </div>
      ${state.discount_amount ? `<div class="summary-line" style="color: #10b981;"><span>Discount</span><span>-${state.formatted_discount}</span></div>` : ''}
      <div class="summary-line total-line">
        <span>Final Payable Amount</span><span>${state.formatted_total || 'KWD 0.000'}</span>
      </div>
    `;
  }

  private renderPaymentView(state: KioskOrderState): void {
    if (!this.paymentContainer) return;
    this.paymentContainer.innerHTML = `
      <div class="payment-icon">💳</div>
      <div style="font-family: var(--font-heading); font-size: 22px; font-weight: 800; color: #FFC72C;">
        Payable Amount: ${state.formatted_total || 'KWD 0.000'}
      </div>
      <p style="color: #a0958e; font-size: 14px;">Please tap, insert, or swipe your payment card on the POS terminal below.</p>
    `;
  }

  private renderCompleteView(state: KioskOrderState): void {
    if (!this.completeContainer) return;
    this.completeContainer.innerHTML = `
      <div class="receipt-icon">🎉</div>
      <div style="font-family: var(--font-heading); font-size: 24px; font-weight: 900; color: #10b981;">
        Order Confirmed!
      </div>
      <div style="font-size: 16px; font-weight: 700; color: #FFC72C;">
        Order Number: ${state.order_id || 'BK-10824'}
      </div>
      <p style="color: #a0958e; font-size: 13px;">Thank you for dining at Burger King! Your meal is being prepared.</p>
    `;
  }

  private formatKWDHtml(priceStr: string): string {
    if (!priceStr) return `<span class="kwd-unit-badge">KWD</span> <span class="kwd-amount-val">0.000</span>`;
    const parts = priceStr.trim().split(' ');
    if (parts.length === 2) {
      return `<span class="kwd-unit-badge">${parts[0]}</span> <span class="kwd-amount-val">${parts[1]}</span>`;
    }
    return `<span class="kwd-amount-val">${priceStr}</span>`;
  }

  private updateState(state: KioskOrderState): void {
    this.currentState = { ...this.currentState, ...state };

    if (state.order_type && this.orderTypePill) {
      this.orderTypePill.textContent = state.order_type;
    }

    const items = this.currentState.cart || [];
    const count = items.reduce((acc, item) => acc + (item.quantity || 1), 0);
    const totalStr = this.currentState.formatted_total || 'KWD 0.000';

    if (this.footerItemCount) this.footerItemCount.textContent = `${count} item(s)`;
    if (this.footerTotal) this.footerTotal.innerHTML = this.formatKWDHtml(totalStr);

    // Render cart & checkout views
    this.renderCartView(items, this.currentState);
    this.renderCheckoutView(this.currentState);
    this.renderPaymentView(this.currentState);
    this.renderCompleteView(this.currentState);

    // Switch view if stage is present
    if (state.current_stage) {
      this.switchStageView(state.current_stage);
    }
  }

  // ── Pipecat Client Setup ─────────────────────────────────────────────────

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
            this.updateSubtitleCaption('user', transcript.text);
          }
        },
        onBotOutput: (data: BotOutputData) => {
          if (data.aggregated_by === AggregationType.SENTENCE) {
            this.log(`Bot output: ${data.text}`);
            this.updateSubtitleCaption('bot', data.text);
          }
        },
        onTrackStarted: (track: MediaStreamTrack, participant?: Participant) => {
          if (!participant?.local) {
            this.onBotTrackStarted(track);
          }
        },
        onServerMessage: (msg: any) => {
          this.log(`Server message: ${JSON.stringify(msg)}`);
          if (msg && msg.type === 'init_menu_payload') {
            if (msg.menu) {
              this.menuData = msg.menu;
              this.renderCategoriesView();
              this.renderProductsView(this.activeCategoryName);
            }
            if (msg.state) {
              this.updateState(msg.state);
            }
          } else if (msg && (msg.type === 'product_detail' || (msg.type === 'menu_display' && msg.item))) {
            if (msg.item) {
              this.renderProductDetailPage(msg.item);
            }
            if (msg.state) {
              this.updateState(msg.state);
            }
          } else if (msg && msg.type === 'menu_display') {
            if (msg.category) {
              this.activeCategoryName = msg.category;
              this.renderProductsView(msg.category);
            }
            if (msg.state) {
              this.updateState(msg.state);
            }
          } else if (msg && msg.type === 'stage_change') {
            if (msg.state) {
              this.updateState(msg.state);
            }
          }
        },
      },
    };

    this.pcClient = new PipecatClient(opts);
    // @ts-ignore
    window.webapp = this;
    // @ts-ignore
    window.client = this.pcClient;
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

  private updateSubtitleCaption(role: 'user' | 'bot', text: string): void {
    const cleanText = text.trim();
    if (!cleanText) return;

    if (role === 'user') {
      if (this.userSubtitleText && this.userSubtitleBox) {
        this.userSubtitleText.textContent = cleanText;
        this.userSubtitleBox.classList.remove('fading');

        if (this.userFadeTimer) window.clearTimeout(this.userFadeTimer);
        this.userFadeTimer = window.setTimeout(() => {
          if (this.userSubtitleBox) this.userSubtitleBox.classList.add('fading');
        }, 4000);
      }
    } else {
      if (this.botSubtitleText && this.botSubtitleBox) {
        this.botSubtitleText.textContent = cleanText;
        this.botSubtitleBox.classList.remove('fading');

        if (this.botFadeTimer) window.clearTimeout(this.botFadeTimer);
        this.botFadeTimer = window.setTimeout(() => {
          if (this.botSubtitleBox) this.botSubtitleBox.classList.add('fading');
        }, 4000);
      }
    }
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
        headers.append('Authorization', `Bearer ${this.apiKey}`);
      }

      const startBotResult = await this.pcClient.startBot({
        endpoint: this.startUrl,
        headers: headers,
        requestData: {
          createDailyRoom: false,
          enableDefaultIceServers: true,
          transport: 'webrtc',
        },
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
