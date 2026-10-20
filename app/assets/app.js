/**
 * NetPulse Demo Store - Frontend Logic & Network Telemetry Engine
 *
 * Demonstrates Layer-7 load balanced traffic routing through Port 8080.
 * Captures real HTTP response headers (X-Served-By, X-LB-Latency-Ms, X-Request-ID)
 * to prove load distribution across backends (b1, b2, b3).
 */

(function () {
  'use strict';

  // -------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------
  const state = {
    products: [],
    categories: [],
    activeCategory: 'all',
    searchQuery: '',
    cart: JSON.parse(localStorage.getItem('netpulse_cart') || '[]'),
    activityLog: [],
  };

  // -------------------------------------------------------------------
  // Hardware SVG Icons Map
  // -------------------------------------------------------------------
  const ICONS = {
    router: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="12" rx="2"></rect><circle cx="6" cy="12" r="1.5"></circle><circle cx="10" cy="12" r="1.5"></circle><circle cx="14" cy="12" r="1.5"></circle><line x1="6" y1="2" x2="6" y2="6"></line><line x1="18" y1="2" x2="18" y2="6"></line></svg>`,
    switch: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="10" rx="2"></rect><line x1="6" y1="12" x2="6.01" y2="12"></line><line x1="9" y1="12" x2="9.01" y2="12"></line><line x1="12" y1="12" x2="12.01" y2="12"></line><line x1="15" y1="12" x2="15.01" y2="12"></line><line x1="18" y1="12" x2="18.01" y2="12"></line></svg>`,
    wifi: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12.55a11 11 0 0 1 14.08 0"></path><path d="M1.42 9a16 16 0 0 1 21.16 0"></path><path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path><line x1="12" y1="20" x2="12.01" y2="20"></line></svg>`,
    fiber: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"></circle><path d="m10 15 5-3-5-3v6Z"></path><path d="M12 3v3M12 18v3M3 12h3M18 12h3"></path></svg>`,
    shield: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>`,
    server: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2"></rect><rect x="2" y="14" width="20" height="8" rx="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>`,
    activity: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>`,
  };

  // -------------------------------------------------------------------
  // DOM Element Selectors
  // -------------------------------------------------------------------
  const els = {
    productGrid: document.getElementById('productGrid'),
    productCount: document.getElementById('productCount'),
    categoryTabs: document.getElementById('categoryTabs'),
    searchInput: document.getElementById('searchInput'),
    clearSearchBtn: document.getElementById('clearSearchBtn'),
    refreshCatalogBtn: document.getElementById('refreshCatalogBtn'),
    errorBanner: document.getElementById('errorBanner'),
    errorMessage: document.getElementById('errorMessage'),
    retryFetchBtn: document.getElementById('retryFetchBtn'),

    // Telemetry Elements
    telemetryPill: document.getElementById('telemetryPill'),
    lastServingBackend: document.getElementById('lastServingBackend'),
    lastLatency: document.getElementById('lastLatency'),
    activityCounter: document.getElementById('activityCounter'),
    activityDrawer: document.getElementById('activityDrawer'),
    activityList: document.getElementById('activityList'),
    toggleActivityBtn: document.getElementById('toggleActivityBtn'),
    closeActivityBtn: document.getElementById('closeActivityBtn'),
    clearActivityBtn: document.getElementById('clearActivityBtn'),

    // Cart Elements
    cartBtn: document.getElementById('cartBtn'),
    cartBadge: document.getElementById('cartBadge'),
    cartDrawer: document.getElementById('cartDrawer'),
    cartOverlay: document.getElementById('cartOverlay'),
    closeCartBtn: document.getElementById('closeCartBtn'),
    cartItemsList: document.getElementById('cartItemsList'),
    cartSubtotal: document.getElementById('cartSubtotal'),
    cartTax: document.getElementById('cartTax'),
    cartShipping: document.getElementById('cartShipping'),
    cartTotal: document.getElementById('cartTotal'),
    checkoutBtn: document.getElementById('checkoutBtn'),

    // Detail Modal Elements
    detailModalBackdrop: document.getElementById('detailModalBackdrop'),
    detailModalContent: document.getElementById('detailModalContent'),
    closeDetailModal: document.getElementById('closeDetailModal'),

    // Checkout Modal Elements
    checkoutModalBackdrop: document.getElementById('checkoutModalBackdrop'),
    closeCheckoutModal: document.getElementById('closeCheckoutModal'),
    cancelCheckoutBtn: document.getElementById('cancelCheckoutBtn'),
    checkoutForm: document.getElementById('checkoutForm'),
    checkoutSummaryBox: document.getElementById('checkoutSummaryBox'),
    confirmOrderBtn: document.getElementById('confirmOrderBtn'),
    checkoutSpinner: document.getElementById('checkoutSpinner'),
    custName: document.getElementById('custName'),
    custEmail: document.getElementById('custEmail'),
    custAddress: document.getElementById('custAddress'),

    // Success Modal Elements
    successModalBackdrop: document.getElementById('successModalBackdrop'),
    orderReceiptDetails: document.getElementById('orderReceiptDetails'),
    continueShoppingBtn: document.getElementById('continueShoppingBtn'),
    viewInDashboardBtn: document.getElementById('viewInDashboardBtn'),
  };

  // -------------------------------------------------------------------
  // Core Network Fetch Interceptor
  // -------------------------------------------------------------------
  async function apiCall(endpoint, options = {}) {
    const startTime = performance.now();
    const method = options.method || 'GET';

    try {
      const response = await fetch(endpoint, options);
      const durationMs = Math.round(performance.now() - startTime);

      // Extract real load balancer headers
      const servingBackend =
        response.headers.get('X-Served-By') ||
        response.headers.get('x-served-by') ||
        'UNKNOWN';

      const algorithm =
        response.headers.get('X-LB-Algorithm') ||
        response.headers.get('x-lb-algorithm') ||
        '';

      const lbLatency =
        response.headers.get('X-LB-Latency-Ms') ||
        response.headers.get('x-lb-latency-ms') ||
        durationMs;

      const requestId =
        response.headers.get('X-Request-ID') ||
        response.headers.get('x-request-id') ||
        'req-' + Math.random().toString(36).substring(2, 9);

      // Parse payload if JSON
      let data = null;
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        data = await response.json();
      }

      // If backend name was also present in payload body
      const effectiveBackend = (data && data.backend) ? data.backend : servingBackend;

      // Update navbar telemetry badge
      updateTelemetryBadge(effectiveBackend, lbLatency, response.status);

      // Record in live telemetry log
      recordActivityEntry({
        method,
        path: endpoint,
        status: response.status,
        backend: effectiveBackend,
        latencyMs: lbLatency,
        requestId,
        timestamp: new Date().toLocaleTimeString(),
      });

      return { ok: response.ok, status: response.status, data, backend: effectiveBackend };
    } catch (err) {
      const durationMs = Math.round(performance.now() - startTime);
      updateTelemetryBadge('ERROR', durationMs, 503);

      recordActivityEntry({
        method,
        path: endpoint,
        status: 503,
        backend: 'DOWN',
        latencyMs: durationMs,
        requestId: 'err-' + Date.now(),
        timestamp: new Date().toLocaleTimeString(),
      });

      throw err;
    }
  }

  // -------------------------------------------------------------------
  // Telemetry Badge & Drawer Management
  // -------------------------------------------------------------------
  function updateTelemetryBadge(backend, latency, status) {
    if (!els.lastServingBackend) return;

    els.lastServingBackend.textContent = backend;
    els.lastServingBackend.className = 'backend-tag ' + (backend ? backend.toLowerCase() : '');
    els.lastLatency.textContent = latency + ' ms';

    if (status >= 400) {
      els.telemetryPill.style.borderColor = 'rgba(239, 68, 68, 0.4)';
    } else {
      els.telemetryPill.style.borderColor = 'var(--border-subtle)';
    }
  }

  function recordActivityEntry(entry) {
    state.activityLog.unshift(entry);
    if (state.activityLog.length > 50) state.activityLog.pop();

    if (els.activityCounter) {
      els.activityCounter.textContent = state.activityLog.length;
    }

    renderActivityList();
  }

  function renderActivityList() {
    if (!els.activityList) return;

    if (state.activityLog.length === 0) {
      els.activityList.innerHTML = `
        <div class="empty-activity">
          <p>No requests recorded yet.</p>
          <small>Interact with products or run searches to see real traffic routed through backends.</small>
        </div>
      `;
      return;
    }

    els.activityList.innerHTML = state.activityLog.map(item => {
      let statusClass = 's2xx';
      if (item.status >= 500) statusClass = 's5xx';
      else if (item.status >= 400) statusClass = 's4xx';

      return `
        <div class="activity-entry">
          <div class="entry-top">
            <div class="entry-method-path">
              <span class="entry-method ${item.method.toLowerCase()}">${item.method}</span>
              <span class="entry-path">${item.path}</span>
            </div>
            <span class="entry-status ${statusClass}">${item.status}</span>
          </div>
          <div class="entry-bottom">
            <span class="entry-backend ${item.backend.toLowerCase()}">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>
              Node: ${item.backend}
            </span>
            <span class="entry-latency">${item.latencyMs} ms &bull; ${item.timestamp}</span>
          </div>
        </div>
      `;
    }).join('');
  }

  // -------------------------------------------------------------------
  // Catalogue & Categories Fetching
  // -------------------------------------------------------------------
  async function loadCategories() {
    try {
      const res = await apiCall('/api/categories');
      if (res.ok && res.data && res.data.categories) {
        state.categories = res.data.categories;
        renderCategoryTabs();
      }
    } catch (err) {
      console.warn('Could not load categories:', err);
    }
  }

  function renderCategoryTabs() {
    if (!els.categoryTabs) return;

    els.categoryTabs.innerHTML = state.categories.map(cat => `
      <button class="cat-pill ${cat.id === state.activeCategory ? 'active' : ''}" data-category="${cat.id}">
        ${cat.name} <span style="opacity:0.6; font-size:0.75rem;">(${cat.count})</span>
      </button>
    `).join('');

    // Attach click listeners
    els.categoryTabs.querySelectorAll('.cat-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        const cat = btn.getAttribute('data-category');
        state.activeCategory = cat;
        renderCategoryTabs();
        loadProducts();
      });
    });
  }

  async function loadProducts() {
    showError(false);
    if (els.productCount) els.productCount.textContent = 'Querying backend pool...';

    const params = new URLSearchParams();
    if (state.activeCategory && state.activeCategory !== 'all') {
      params.append('category', state.activeCategory);
    }
    if (state.searchQuery && state.searchQuery.trim()) {
      params.append('search', state.searchQuery.trim());
    }

    const url = '/api/products' + (params.toString() ? '?' + params.toString() : '');

    try {
      const res = await apiCall(url);
      if (res.ok && res.data && res.data.products) {
        state.products = res.data.products;
        renderProducts();
      } else {
        showError(true, 'Unexpected Response', 'Backend returned an unprocessable status.');
      }
    } catch (err) {
      showError(
        true,
        'Backend Pool Offline / Unavailable',
        'Could not reach any healthy backends on :5001, :5002, or :5003 through the reverse proxy. Check health monitoring in Observatory.'
      );
    }
  }

  function showError(visible, title = '', msg = '') {
    if (!els.errorBanner) return;
    if (visible) {
      document.getElementById('errorTitle').textContent = title;
      els.errorMessage.textContent = msg;
      els.errorBanner.style.display = 'flex';
      if (els.productGrid) els.productGrid.innerHTML = '';
      if (els.productCount) els.productCount.textContent = '0 items (Network Error)';
    } else {
      els.errorBanner.style.display = 'none';
    }
  }

  function renderProducts() {
    if (!els.productGrid) return;

    if (els.productCount) {
      els.productCount.textContent = `Showing ${state.products.length} hardware unit${state.products.length === 1 ? '' : 's'}`;
    }

    if (state.products.length === 0) {
      els.productGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: var(--text-dim);">
          <h3>No matching networking products found</h3>
          <p style="margin-top: 8px; font-size: 0.9rem;">Try searching for "router", "switch", "SFP+", or reset the category filter.</p>
        </div>
      `;
      return;
    }

    els.productGrid.innerHTML = state.products.map(prod => {
      const iconSvg = ICONS[prod.icon] || ICONS.server;
      const specsList = prod.specs
        ? Object.entries(prod.specs).slice(0, 3).map(([k, v]) => `<span class="spec-pill">${k}: ${v}</span>`).join('')
        : '';

      return `
        <article class="product-card" data-id="${prod.id}">
          <div class="card-top">
            <span class="badge-tag">${prod.badge || 'Enterprise'}</span>
            <span style="font-size:0.75rem; color:var(--text-dim); font-family:var(--font-mono);">${prod.id}</span>
          </div>

          <div class="product-icon-box">
            ${iconSvg}
          </div>

          <h3 class="product-title">${prod.name}</h3>
          <span class="product-cat-name">${prod.category_name}</span>
          <p class="product-desc">${prod.description}</p>

          <div class="specs-preview">
            ${specsList}
          </div>

          <div class="card-bottom">
            <div class="price-box">
              <span class="price-label">Price</span>
              <span class="price-value">$${prod.price.toFixed(2)}</span>
            </div>
            <div class="card-actions">
              <button class="btn-icon-action btn-view-detail" data-id="${prod.id}" title="View Technical Specs">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
              </button>
              <button class="btn-add-cart" data-id="${prod.id}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                Add
              </button>
            </div>
          </div>
        </article>
      `;
    }).join('');

    // Attach card event listeners
    els.productGrid.querySelectorAll('.btn-add-cart').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = btn.getAttribute('data-id');
        addToCart(id);
      });
    });

    els.productGrid.querySelectorAll('.btn-view-detail').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = btn.getAttribute('data-id');
        openDetailModal(id);
      });
    });
  }

  // -------------------------------------------------------------------
  // Product Detail Modal
  // -------------------------------------------------------------------
  async function openDetailModal(productId) {
    try {
      const res = await apiCall(`/api/products/${productId}`);
      if (!res.ok || !res.data || !res.data.product) {
        alert('Could not retrieve product details from backend.');
        return;
      }

      const prod = res.data.product;
      const iconSvg = ICONS[prod.icon] || ICONS.server;

      const specsRows = prod.specs
        ? Object.entries(prod.specs).map(([k, v]) => `
            <tr>
              <td>${k}</td>
              <td>${v}</td>
            </tr>
          `).join('')
        : '';

      els.detailModalContent.innerHTML = `
        <div class="detail-header">
          <div class="detail-icon-large">${iconSvg}</div>
          <div>
            <span class="badge-tag" style="margin-bottom:6px; display:inline-block;">${prod.badge || 'Enterprise'}</span>
            <h2 class="detail-title">${prod.name}</h2>
            <div style="font-size:0.8rem; color:var(--text-dim); margin-top:2px;">
              Category: ${prod.category_name} &bull; Rating: ⭐ ${prod.rating} &bull; In Stock: ${prod.stock} units
            </div>
          </div>
        </div>

        <p style="color:var(--text-muted); font-size:0.92rem; line-height:1.6; margin-bottom:16px;">
          ${prod.description}
        </p>

        <h4 style="font-size:0.9rem; font-weight:700; margin-bottom:8px; border-bottom:1px solid var(--border-subtle); padding-bottom:6px;">
          Hardware Technical Specifications
        </h4>
        <table class="detail-specs-table">
          <tbody>${specsRows}</tbody>
        </table>

        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:24px; padding-top:16px; border-top:1px solid var(--border-subtle);">
          <div>
            <div style="font-size:0.75rem; color:var(--text-dim);">Unit Price</div>
            <div style="font-size:1.6rem; font-weight:800; font-family:var(--font-mono); color:#fff;">$${prod.price.toFixed(2)}</div>
          </div>
          <button class="btn-primary" id="modalAddToCartBtn" style="padding:12px 24px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>
            Add to Shopping Cart
          </button>
        </div>
      `;

      document.getElementById('modalAddToCartBtn').addEventListener('click', () => {
        addToCart(prod.id);
        closeDetail();
      });

      els.detailModalBackdrop.classList.add('active');
    } catch (err) {
      alert('Failed to fetch product details.');
    }
  }

  function closeDetail() {
    els.detailModalBackdrop.classList.remove('active');
  }

  // -------------------------------------------------------------------
  // Shopping Cart Management
  // -------------------------------------------------------------------
  function addToCart(productId) {
    const prod = state.products.find(p => p.id === productId);
    if (!prod) return;

    const existing = state.cart.find(it => it.id === productId);
    if (existing) {
      existing.qty += 1;
    } else {
      state.cart.push({
        id: prod.id,
        name: prod.name,
        price: prod.price,
        qty: 1,
        icon: prod.icon,
        category: prod.category_name,
      });
    }

    saveCart();
    renderCart();
    openCart();
  }

  function updateCartQty(productId, delta) {
    const item = state.cart.find(it => it.id === productId);
    if (!item) return;

    item.qty += delta;
    if (item.qty <= 0) {
      state.cart = state.cart.filter(it => it.id !== productId);
    }

    saveCart();
    renderCart();
  }

  function removeFromCart(productId) {
    state.cart = state.cart.filter(it => it.id !== productId);
    saveCart();
    renderCart();
  }

  function saveCart() {
    localStorage.setItem('netpulse_cart', JSON.stringify(state.cart));
    updateCartBadge();
  }

  function updateCartBadge() {
    const totalCount = state.cart.reduce((acc, it) => acc + it.qty, 0);
    if (els.cartBadge) {
      els.cartBadge.textContent = totalCount;
    }
  }

  function renderCart() {
    if (!els.cartItemsList) return;

    if (state.cart.length === 0) {
      els.cartItemsList.innerHTML = `
        <div class="empty-cart-view">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle>
            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
          </svg>
          <p>Your shopping cart is empty.</p>
          <small style="margin-top:4px; display:block;">Select networking devices from the catalogue.</small>
        </div>
      `;
      els.cartSubtotal.textContent = '$0.00';
      els.cartTax.textContent = '$0.00';
      els.cartShipping.textContent = '$0.00';
      els.cartTotal.textContent = '$0.00';
      els.checkoutBtn.disabled = true;
      els.checkoutBtn.style.opacity = '0.5';
      return;
    }

    els.checkoutBtn.disabled = false;
    els.checkoutBtn.style.opacity = '1';

    let subtotal = 0;

    els.cartItemsList.innerHTML = state.cart.map(it => {
      const lineTotal = it.price * it.qty;
      subtotal += lineTotal;

      return `
        <div class="cart-item">
          <div class="cart-item-header">
            <div>
              <div class="cart-item-title">${it.name}</div>
              <div style="font-size:0.72rem; color:var(--text-dim); font-family:var(--font-mono);">$${it.price.toFixed(2)} each</div>
            </div>
            <button class="btn-remove-item" data-id="${it.id}" title="Remove item">&times;</button>
          </div>
          <div class="cart-item-footer">
            <div class="qty-control">
              <button class="qty-btn" data-id="${it.id}" data-delta="-1">-</button>
              <span class="qty-val">${it.qty}</span>
              <button class="qty-btn" data-id="${it.id}" data-delta="1">+</button>
            </div>
            <span class="item-line-price">$${lineTotal.toFixed(2)}</span>
          </div>
        </div>
      `;
    }).join('');

    const tax = subtotal * 0.08;
    const shipping = subtotal >= 99 ? 0 : 15;
    const total = subtotal + tax + shipping;

    els.cartSubtotal.textContent = `$${subtotal.toFixed(2)}`;
    els.cartTax.textContent = `$${tax.toFixed(2)}`;
    els.cartShipping.textContent = shipping === 0 ? 'FREE' : `$${shipping.toFixed(2)}`;
    els.cartTotal.textContent = `$${total.toFixed(2)}`;

    // Attach listeners
    els.cartItemsList.querySelectorAll('.qty-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        const delta = parseInt(btn.getAttribute('data-delta'), 10);
        updateCartQty(id, delta);
      });
    });

    els.cartItemsList.querySelectorAll('.btn-remove-item').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        removeFromCart(id);
      });
    });
  }

  function openCart() {
    els.cartDrawer.classList.add('active');
    els.cartOverlay.classList.add('active');
  }

  function closeCart() {
    els.cartDrawer.classList.remove('active');
    els.cartOverlay.classList.remove('active');
  }

  // -------------------------------------------------------------------
  // Simulated Checkout & Order Submission
  // -------------------------------------------------------------------
  function openCheckoutModal() {
    if (state.cart.length === 0) return;

    closeCart();

    const subtotal = state.cart.reduce((acc, it) => acc + (it.price * it.qty), 0);
    const tax = subtotal * 0.08;
    const shipping = subtotal >= 99 ? 0 : 15;
    const total = subtotal + tax + shipping;

    els.checkoutSummaryBox.innerHTML = `
      <div style="font-weight:700; margin-bottom:8px; color:#fff;">Order Items (${state.cart.reduce((a, b) => a + b.qty, 0)} units)</div>
      ${state.cart.map(i => `
        <div style="display:flex; justify-content:space-between; margin-bottom:4px; color:var(--text-muted);">
          <span>${i.qty}x ${i.name}</span>
          <span style="font-family:var(--font-mono);">$${(i.price * i.qty).toFixed(2)}</span>
        </div>
      `).join('')}
      <div style="display:flex; justify-content:space-between; border-top:1px solid var(--border-subtle); padding-top:6px; margin-top:8px; font-weight:700; color:#fff;">
        <span>Total Due (Simulated)</span>
        <span style="font-family:var(--font-mono); color:var(--accent-cyan);">$${total.toFixed(2)}</span>
      </div>
    `;

    els.checkoutModalBackdrop.classList.add('active');
  }

  function closeCheckout() {
    els.checkoutModalBackdrop.classList.remove('active');
  }

  async function handleCheckoutSubmit(e) {
    e.preventDefault();

    if (state.cart.length === 0) {
      alert('Cart is empty.');
      return;
    }

    const payload = {
      customer_name: els.custName.value.trim(),
      email: els.custEmail.value.trim(),
      address: els.custAddress.value.trim(),
      items: state.cart.map(it => ({
        product_id: it.id,
        quantity: it.qty,
      })),
      payment_method: 'Simulated Card (Lab Demonstration)',
    };

    els.confirmOrderBtn.disabled = true;
    els.checkoutSpinner.style.display = 'inline-block';

    try {
      const res = await apiCall('/api/orders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (res.ok && res.data && res.data.order) {
        // Clear cart
        state.cart = [];
        saveCart();
        renderCart();

        closeCheckout();
        openSuccessModal(res.data.order, res.backend);
      } else {
        const msg = (res.data && res.data.message) ? res.data.message : 'Order processing failed.';
        alert('Order Rejected: ' + msg);
      }
    } catch (err) {
      alert('Network Error during order placement. Reverse proxy or all backends are currently unreachable.');
    } finally {
      els.confirmOrderBtn.disabled = false;
      els.checkoutSpinner.style.display = 'none';
    }
  }

  function openSuccessModal(order, servingBackend) {
    els.orderReceiptDetails.innerHTML = `
      <div class="receipt-row">
        <span class="label">Order Reference ID</span>
        <span class="val" style="color:var(--accent-cyan);">${order.order_id}</span>
      </div>
      <div class="receipt-row">
        <span class="label">Serving Backend Node</span>
        <span class="val backend-tag ${servingBackend.toLowerCase()}">
          Node ${servingBackend}
        </span>
      </div>
      <div class="receipt-row">
        <span class="label">Date & Time</span>
        <span class="val">${order.date_str}</span>
      </div>
      <div class="receipt-row">
        <span class="label">Recipient</span>
        <span class="val">${order.customer.name}</span>
      </div>
      <div class="receipt-row">
        <span class="label">Total Charged (Simulated)</span>
        <span class="val" style="color:var(--accent-green); font-size:1rem;">$${order.summary.total.toFixed(2)}</span>
      </div>
      <div class="receipt-row">
        <span class="label">Items Purchased</span>
        <span class="val">${order.summary.item_count} units (${order.items.length} lines)</span>
      </div>
    `;

    els.successModalBackdrop.classList.add('active');
  }

  function closeSuccess() {
    els.successModalBackdrop.classList.remove('active');
  }

  // -------------------------------------------------------------------
  // Search & Filter Events
  // -------------------------------------------------------------------
  let searchTimeout = null;

  function handleSearchInput() {
    const val = els.searchInput.value;
    state.searchQuery = val;

    if (els.clearSearchBtn) {
      els.clearSearchBtn.style.display = val ? 'block' : 'none';
    }

    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      loadProducts();
    }, 250);
  }

  function clearSearch() {
    els.searchInput.value = '';
    state.searchQuery = '';
    els.clearSearchBtn.style.display = 'none';
    loadProducts();
  }

  // -------------------------------------------------------------------
  // Initialization & Event Listeners
  // -------------------------------------------------------------------
  function initEventListeners() {
    // Search
    if (els.searchInput) {
      els.searchInput.addEventListener('input', handleSearchInput);
    }
    if (els.clearSearchBtn) {
      els.clearSearchBtn.addEventListener('click', clearSearch);
    }
    if (els.refreshCatalogBtn) {
      els.refreshCatalogBtn.addEventListener('click', () => loadProducts());
    }
    if (els.retryFetchBtn) {
      els.retryFetchBtn.addEventListener('click', () => {
        loadCategories();
        loadProducts();
      });
    }

    // Cart drawer
    if (els.cartBtn) els.cartBtn.addEventListener('click', openCart);
    if (els.closeCartBtn) els.closeCartBtn.addEventListener('click', closeCart);
    if (els.cartOverlay) els.cartOverlay.addEventListener('click', closeCart);
    if (els.checkoutBtn) els.checkoutBtn.addEventListener('click', openCheckoutModal);

    // Detail modal
    if (els.closeDetailModal) els.closeDetailModal.addEventListener('click', closeDetail);
    if (els.detailModalBackdrop) {
      els.detailModalBackdrop.addEventListener('click', (e) => {
        if (e.target === els.detailModalBackdrop) closeDetail();
      });
    }

    // Checkout modal
    if (els.closeCheckoutModal) els.closeCheckoutModal.addEventListener('click', closeCheckout);
    if (els.cancelCheckoutBtn) els.cancelCheckoutBtn.addEventListener('click', closeCheckout);
    if (els.checkoutForm) els.checkoutForm.addEventListener('submit', handleCheckoutSubmit);

    // Success modal
    if (els.continueShoppingBtn) els.continueShoppingBtn.addEventListener('click', closeSuccess);
    if (els.viewInDashboardBtn) {
      els.viewInDashboardBtn.addEventListener('click', () => {
        window.open('/dashboard', '_blank');
      });
    }

    // Activity Drawer
    if (els.toggleActivityBtn) {
      els.toggleActivityBtn.addEventListener('click', () => {
        els.activityDrawer.classList.toggle('open');
      });
    }
    if (els.closeActivityBtn) {
      els.closeActivityBtn.addEventListener('click', () => {
        els.activityDrawer.classList.remove('open');
      });
    }
    if (els.clearActivityBtn) {
      els.clearActivityBtn.addEventListener('click', () => {
        state.activityLog = [];
        els.activityCounter.textContent = '0';
        renderActivityList();
      });
    }
  }

  // Launch on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    updateCartBadge();
    renderCart();
    loadCategories();
    loadProducts();
  });

})();
