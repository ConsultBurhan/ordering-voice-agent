export interface OrderItem {
  id: string;
  name: string;
  price: number;
  quantity: number;
  icon: string;
  category: string;
}

const KNOWN_MENU_ITEMS: Array<{ keywords: string[]; name: string; price: number; icon: string; category: string }> = [
  { keywords: ['double cheeseburger', 'cheeseburger', 'double burger', 'burger'], name: 'Classic Double Cheeseburger', price: 8.99, icon: '🍔', category: 'Mains' },
  { keywords: ['pepperoni pizza', 'pizza', 'slice'], name: 'Artisan Pepperoni Pizza', price: 14.50, icon: '🍕', category: 'Mains' },
  { keywords: ['fries', 'french fries', 'potato fries'], name: 'Crispy Golden French Fries', price: 3.99, icon: '🍟', category: 'Sides' },
  { keywords: ['latte', 'oat latte', 'iced latte', 'coffee'], name: 'Iced Oat Milk Latte', price: 4.75, icon: '☕', category: 'Drinks' },
  { keywords: ['taco', 'tacos'], name: 'Street Beef Tacos (3x)', price: 9.50, icon: '🌮', category: 'Mains' },
  { keywords: ['coke', 'soda', 'cola', 'drink', 'soft drink'], name: 'Fountain Soda', price: 2.25, icon: '🥤', category: 'Drinks' },
  { keywords: ['nuggets', 'chicken nuggets'], name: 'Crispy Chicken Nuggets (10pc)', price: 6.99, icon: '🍗', category: 'Sides' },
  { keywords: ['salad', 'caesar salad'], name: 'Fresh Caesar Salad', price: 7.50, icon: '🥗', category: 'Mains' },
  { keywords: ['shake', 'milkshake', 'ice cream'], name: 'Vanilla Bean Milkshake', price: 4.99, icon: '🍦', category: 'Desserts' },
];

export class OrderCart {
  private container: HTMLElement;
  private items: Map<string, OrderItem> = new Map();
  private onItemAddedCallback?: (item: OrderItem) => void;

  constructor(containerId: string, onItemAdded?: (item: OrderItem) => void) {
    const el = document.getElementById(containerId);
    if (!el) {
      throw new Error(`Cart container element '${containerId}' not found.`);
    }
    this.container = el;
    this.onItemAddedCallback = onItemAdded;
    this.render();
  }

  public parseTranscript(text: string): void {
    const lowerText = text.toLowerCase();
    
    // Check if user or bot said "clear order" or "start over" or "cancel order"
    if (lowerText.includes('clear order') || lowerText.includes('cancel order') || lowerText.includes('start over')) {
      this.clearCart();
      return;
    }

    for (const menuItem of KNOWN_MENU_ITEMS) {
      const match = menuItem.keywords.some((kw) => lowerText.includes(kw));
      if (match) {
        // Avoid duplicate triggers if item was recently added in last sentence unless explicitly requested with numbers
        this.addItem({
          id: menuItem.name.toLowerCase().replace(/\s+/g, '-'),
          name: menuItem.name,
          price: menuItem.price,
          quantity: 1,
          icon: menuItem.icon,
          category: menuItem.category
        });
      }
    }
  }

  public addItem(itemDef: OrderItem): void {
    const existing = this.items.get(itemDef.id);
    if (existing) {
      existing.quantity += 1;
    } else {
      this.items.set(itemDef.id, { ...itemDef });
    }
    this.render();
    if (this.onItemAddedCallback) {
      this.onItemAddedCallback(itemDef);
    }
  }

  public removeItem(itemId: string): void {
    this.items.delete(itemId);
    this.render();
  }

  public clearCart(): void {
    this.items.clear();
    this.render();
  }

  public getItemCount(): number {
    let count = 0;
    this.items.forEach((item) => { count += item.quantity; });
    return count;
  }

  public getSubtotal(): number {
    let sum = 0;
    this.items.forEach((item) => { sum += item.price * item.quantity; });
    return sum;
  }

  private render(): void {
    const itemCount = this.getItemCount();
    const subtotal = this.getSubtotal();
    const tax = subtotal * 0.08;
    const total = subtotal + tax;

    let itemsHtml = '';
    if (this.items.size === 0) {
      itemsHtml = `
        <div class="cart-empty-state">
          <div class="empty-cart-icon">🛒</div>
          <p class="empty-cart-title">Your Order Cart is Empty</p>
          <p class="empty-cart-sub">Speak to your Assistant or tap a menu item to start building your order!</p>
        </div>
      `;
    } else {
      this.items.forEach((item) => {
        itemsHtml += `
          <div class="cart-item-row" data-id="${item.id}">
            <div class="cart-item-icon">${item.icon}</div>
            <div class="cart-item-details">
              <span class="cart-item-name">${item.name}</span>
              <span class="cart-item-price">$${item.price.toFixed(2)} each</span>
            </div>
            <div class="cart-item-qty-controls">
              <button class="qty-btn qty-minus" data-id="${item.id}">-</button>
              <span class="qty-val">${item.quantity}</span>
              <button class="qty-btn qty-plus" data-id="${item.id}">+</button>
            </div>
            <div class="cart-item-total">$${(item.price * item.quantity).toFixed(2)}</div>
          </div>
        `;
      });
    }

    this.container.innerHTML = `
      <div class="cart-panel">
        <div class="cart-header">
          <div class="cart-title-group">
            <span class="cart-header-icon">📋</span>
            <h3>Live Receipt</h3>
          </div>
          <span class="cart-badge">${itemCount} ${itemCount === 1 ? 'item' : 'items'}</span>
        </div>

        <div class="cart-items-scroll">
          ${itemsHtml}
        </div>

        <div class="cart-footer">
          <div class="cart-summary-line">
            <span>Subtotal</span>
            <span>$${subtotal.toFixed(2)}</span>
          </div>
          <div class="cart-summary-line">
            <span>Tax (8%)</span>
            <span>$${tax.toFixed(2)}</span>
          </div>
          <div class="cart-summary-line cart-total-line">
            <span>Estimated Total</span>
            <span class="total-price-tag">$${total.toFixed(2)}</span>
          </div>

          <div class="cart-actions">
            <button class="btn btn-cart-clear" id="cart-clear-btn" ${this.items.size === 0 ? 'disabled' : ''}>Clear Receipt</button>
            <button class="btn btn-cart-submit" id="cart-checkout-btn" ${this.items.size === 0 ? 'disabled' : ''}>
              Place Order ($${total.toFixed(2)})
            </button>
          </div>
        </div>
      </div>
    `;

    this.setupEventListeners();
  }

  private setupEventListeners(): void {
    const clearBtn = this.container.querySelector('#cart-clear-btn');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => this.clearCart());
    }

    const checkoutBtn = this.container.querySelector('#cart-checkout-btn');
    if (checkoutBtn) {
      checkoutBtn.addEventListener('click', () => {
        if (this.items.size > 0) {
          alert(`🎉 Order Placed Successfully! Total: $${(this.getSubtotal() * 1.08).toFixed(2)}`);
          this.clearCart();
        }
      });
    }

    this.container.querySelectorAll('.qty-minus').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const id = (e.currentTarget as HTMLElement).getAttribute('data-id');
        if (id) {
          const item = this.items.get(id);
          if (item) {
            if (item.quantity > 1) {
              item.quantity -= 1;
              this.render();
            } else {
              this.removeItem(id);
            }
          }
        }
      });
    });

    this.container.querySelectorAll('.qty-plus').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const id = (e.currentTarget as HTMLElement).getAttribute('data-id');
        if (id) {
          const item = this.items.get(id);
          if (item) {
            item.quantity += 1;
            this.render();
          }
        }
      });
    });
  }
}
