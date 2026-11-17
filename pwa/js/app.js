/**
 * SD Finance PWA - Revolut Obsidian Controller (1:1 Android Mobile Parity)
 * Complete implementation for Village Selection, Dashboard, Customer List,
 * Payments, Posting, Add Customer, Offline Queue, and All Native Bottom Sheets.
 */

// Global Helpers
function generateUUID() {
  if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

function formatCurrency(val) {
  const num = parseFloat(val) || 0;
  return '₹' + Math.round(num).toLocaleString('en-IN');
}

function formatRawCurrency(val) {
  const num = parseFloat(val) || 0;
  return '₹' + Math.round(num);
}

function normalizeDateStr(val) {
  if (!val) return '';
  if (typeof val !== 'string') {
    if (val instanceof Date && !isNaN(val.getTime())) {
      const y = val.getFullYear();
      const m = String(val.getMonth() + 1).padStart(2, '0');
      const d = String(val.getDate()).padStart(2, '0');
      return `${y}-${m}-${d}`;
    }
    val = String(val);
  }
  const s = val.trim();
  if (!s) return '';

  const months = {
    jan: '01', feb: '02', mar: '03', apr: '04', may: '05', jun: '06',
    jul: '07', aug: '08', sep: '09', oct: '10', nov: '11', dec: '12'
  };
  const verboseMatch = s.match(/(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})/);
  if (verboseMatch) {
    const d = verboseMatch[1].padStart(2, '0');
    const mStr = verboseMatch[2].toLowerCase();
    const m = months[mStr] || '01';
    const y = verboseMatch[3];
    return `${y}-${m}-${d}`;
  }

  const isoMatch = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (isoMatch) {
    const y = isoMatch[1];
    const m = isoMatch[2].padStart(2, '0');
    const d = isoMatch[3].padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  const dmyMatch = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
  if (dmyMatch) {
    const d = dmyMatch[1].padStart(2, '0');
    const m = dmyMatch[2].padStart(2, '0');
    const y = dmyMatch[3];
    return `${y}-${m}-${d}`;
  }

  const parsed = new Date(s);
  if (!isNaN(parsed.getTime())) {
    const y = parsed.getFullYear();
    const m = String(parsed.getMonth() + 1).padStart(2, '0');
    const d = String(parsed.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  return s;
}

function formatDateDisplay(dateStr) {
  if (!dateStr) return '-';
  const norm = normalizeDateStr(dateStr);
  if (!norm) return '-';
  const parts = norm.split('-');
  if (parts.length === 3) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const d = parts[2];
    const mIdx = parseInt(parts[1], 10) - 1;
    const y = parts[0];
    return `${d} ${months[mIdx] || ''} ${y}`;
  }
  return norm;
}

function formatDateDDMMYYYY(dateStr) {
  if (!dateStr) return '-';
  const norm = normalizeDateStr(dateStr);
  if (!norm) return '-';
  const parts = norm.split('-');
  if (parts.length === 3) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }
  return norm;
}

function getDayOfWeek(dateStr) {
  if (!dateStr) return '';
  const norm = normalizeDateStr(dateStr);
  if (!norm) return '';
  const parts = norm.split('-');
  if (parts.length === 3) {
    const dt = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    if (!isNaN(dt.getTime())) {
      const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
      return days[dt.getDay()];
    }
  }
  return '';
}

function formatDmy(dateStr) {
  if (!dateStr) return '';
  const norm = normalizeDateStr(dateStr);
  if (!norm) return dateStr;
  const parts = norm.split('-');
  if (parts.length === 3) {
    const d = parseInt(parts[2], 10);
    const m = parseInt(parts[1], 10);
    const y = parts[0];
    return `${d}/${m}/${y}`;
  }
  return norm;
}

const CODE_GLOW_COLORS = [
  ['#10B981', '#059669'], // Emerald
  ['#0EA5E9', '#0284C7'], // Sky
  ['#8B5CF6', '#6D28D9'], // Purple
  ['#F59E0B', '#D97706'], // Amber
  ['#14B8A6', '#0F766E'], // Teal
  ['#EC4899', '#BE185D'], // Pink
  ['#6366F1', '#4338CA'], // Indigo
  ['#F97316', '#C2410C'], // Orange
];

class AppController {
  constructor() {
    this.currentView = 'login';
    this.selectedVid = null;
    this.selectedVillage = null;
    this.villages = [];

    // Customers Data & Filters
    this.customers = [];
    this.filteredCustomers = [];
    this.customerSearchQuery = '';
    this.customerFilterDate = null;
    this.customerMaxBalance = 150000;
    this.customerFilterBalance = 150000;
    this.activeCustomerDetail = null;

    // Payments Data
    this.allPayments = [];
    this.paymentDateGroups = [];
    this.paymentSearchQuery = '';
    this.activePaymentDateGroup = null;

    // Posting State
    this.selectedPostingCustomer = null;
    this.selectedPostingDate = new Date().toISOString().split('T')[0];
    this.selectedPostingMode = 'cash'; // 'cash', 'upi', 'partial'
    this.todayLocalPayments = [];

    // Add Customer State
    this.newCustLoanType = 'W'; // 'W' or 'M'
    this.newCustDisbursementMode = 'CASH'; // 'CASH', 'UPI', 'PARTIAL'
    this.newCustStartDate = new Date().toISOString().split('T')[0];
    this.newCustPhotos = { front: null, back: null, house: null };
    this.isUpdatingAmounts = false;

    // Dashboard Carousel State
    this.currentMetricPage = 1; // 0: Active Customers, 1: Total Balance, 2: Average Balance
    this.dashboardData = {
      activeCustomers: 0,
      totalBalance: 0,
      averageBalance: 0,
      unpostedToday: 0,
      closedAccounts: 0,
    };

    // Missing Payments & Closed Customers Deck State
    this.closedCustomers = [];
    this.paymentSkippedGroups = [];
    this.closedCustomerGroups = [];
    this.totalSkipped = 0;
    this.totalClosed = 0;
    this.isPostingActiveToday = false;
    this.todayMissingCount = 0;
    this.todayMissingCustomers = [];
  }

  async init() {
    try {
      this._bindEvents();
    } catch (e) {
      console.error('[App] Error binding events:', e);
    }

    try {
      this._initOnlineListener();
    } catch (_) {}

    // Listen to sync events
    try {
      if (window.syncManager) {
        window.syncManager.onStatusChange((status, details) => {
          this._updateOnlineBanner();
          this.updatePendingBadges();
          if (status === 'completed' && details.synced > 0) {
            this.showToast(`Synced ${details.synced} transactions!`, 'check_circle');
            this.computeDashboardMetrics();
          }
        });
      }
    } catch (_) {}

    // Check existing session
    try {
      const token = await window.dbService.getSession('token');
      const employeeName = await window.dbService.getSession('employee_name');
      const savedVid = await window.dbService.getSession('selected_vid');

      if (token) {
        if (employeeName) {
          const empEl = document.getElementById('profile-modal-name');
          if (empEl) empEl.textContent = employeeName;
        }

        if (savedVid) {
          this.selectedVid = savedVid;
          this.switchView('dashboard');
          this.loadVillages();
          Promise.all([
            this.loadCustomers(this.selectedVid),
            this.loadPayments(this.selectedVid),
            this.loadClosedCustomers(this.selectedVid)
          ]).then(() => {
            this.computeDashboardMetrics();
          });
          if (window.syncManager) window.syncManager.syncAll();
        } else {
          this.switchView('villages');
          this.loadVillages();
        }
      } else {
        this.switchView('login');
      }
    } catch (err) {
      console.warn('[App] Session check error, fallback to login:', err);
      this.switchView('login');
    }

    try {
      this.updatePendingBadges();
    } catch (_) {}
  }

  _bindEvents() {
    // ---------------- Login Form ----------------
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
      loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await this.handleLogin();
      });
    }

    // ---------------- Village Search ----------------
    const vSearch = document.getElementById('village-search-input');
    if (vSearch) {
      vSearch.addEventListener('input', (e) => {
        this.filterVillages(e.target.value);
      });
    }

    // ---------------- Dashboard Top Bar ----------------
    const dashHome = document.getElementById('dash-btn-home');
    if (dashHome) {
      dashHome.addEventListener('click', () => this.switchView('villages'));
    }

    const dashProfile = document.getElementById('dash-btn-profile');
    if (dashProfile) {
      dashProfile.addEventListener('click', () => this.openProfileModal());
    }

    // ---------------- Dashboard Metrics Carousel ----------------
    const metricSlide = document.getElementById('metric-slide-content');
    if (metricSlide) {
      metricSlide.addEventListener('click', () => this.cycleMetricsPage());
    }

    document.querySelectorAll('.metric-dot').forEach(dot => {
      dot.addEventListener('click', () => {
        const idx = parseInt(dot.dataset.idx, 10);
        this.setMetricsPage(idx);
      });
    });

    // ---------------- Dashboard Quick Actions ----------------
    const actAddCust = document.getElementById('dash-act-add-customer');
    if (actAddCust) {
      actAddCust.addEventListener('click', () => this.switchView('add-customer'));
    }

    const actPosting = document.getElementById('dash-act-posting');
    if (actPosting) {
      actPosting.addEventListener('click', () => this.switchView('posting'));
    }

    const actSubmit = document.getElementById('dash-act-submit');
    if (actSubmit) {
      actSubmit.addEventListener('click', () => this.switchView('sync'));
    }

    // ---------------- 3D Stacked Decks ----------------
    const deckMissing = document.getElementById('deck-missing-payments');
    if (deckMissing) {
      deckMissing.addEventListener('click', () => {
        this.openMissingPaymentsModal();
      });
    }

    const deckClosed = document.getElementById('deck-closed-accounts');
    if (deckClosed) {
      deckClosed.addEventListener('click', () => {
        this.openClosedCustomersModal();
      });
    }

    const mpmClose = document.getElementById('mpm-btn-close');
    if (mpmClose) {
      mpmClose.addEventListener('click', () => this.closeModal('missing-payments-modal'));
    }

    const mpmHistory = document.getElementById('mpm-btn-history');
    if (mpmHistory) {
      mpmHistory.addEventListener('click', () => {
        this.renderMissingPaymentsHistory(true);
      });
    }

    const ccmClose = document.getElementById('ccm-btn-close');
    if (ccmClose) {
      ccmClose.addEventListener('click', () => this.closeModal('closed-customers-modal'));
    }

    // ---------------- Customers Screen ----------------
    const custBack = document.getElementById('cust-btn-back');
    if (custBack) {
      custBack.addEventListener('click', () => this.switchView('dashboard'));
    }

    const custAdd = document.getElementById('cust-btn-add');
    if (custAdd) {
      custAdd.addEventListener('click', () => this.switchView('add-customer'));
    }

    const custSearch = document.getElementById('customer-search-input');
    if (custSearch) {
      custSearch.addEventListener('input', (e) => {
        this.customerSearchQuery = e.target.value.trim().toLowerCase();
        this.applyCustomerFilters();
      });
    }

    const custFilterBtn = document.getElementById('cust-btn-filter');
    if (custFilterBtn) {
      custFilterBtn.addEventListener('click', () => this.openCustomerFilterModal());
    }

    // Customer Filter Modal actions
    const custFilterReset = document.getElementById('btn-cust-filter-reset');
    if (custFilterReset) {
      custFilterReset.addEventListener('click', () => {
        this.customerFilterDate = null;
        this.customerFilterBalance = this.customerMaxBalance;
        const slider = document.getElementById('cust-filter-balance-slider');
        if (slider) slider.value = this.customerMaxBalance;
        const balLabel = document.getElementById('cust-filter-balance-label');
        if (balLabel) balLabel.textContent = `₹0 - ${formatCurrency(this.customerMaxBalance)}`;
        const dateLabel = document.getElementById('cust-filter-date-label');
        if (dateLabel) dateLabel.textContent = 'All Dates (Tap to pick range)';
        document.getElementById('cust-filter-dot').style.display = 'none';
        this.applyCustomerFilters();
        this.closeModal('customer-filter-modal');
      });
    }

    const btnPickDates = document.getElementById('btn-pick-filter-dates');
    const custFilterDateInput = document.getElementById('cust-filter-date-input');
    if (btnPickDates && custFilterDateInput) {
      btnPickDates.addEventListener('click', () => {
        if (typeof custFilterDateInput.showPicker === 'function') {
          custFilterDateInput.showPicker();
        } else {
          custFilterDateInput.click();
        }
      });

      custFilterDateInput.addEventListener('change', (e) => {
        this.customerFilterDate = e.target.value;
        const dateLabel = document.getElementById('cust-filter-date-label');
        if (dateLabel) dateLabel.textContent = formatDateDisplay(this.customerFilterDate);
      });
    }

    const balanceSlider = document.getElementById('cust-filter-balance-slider');
    if (balanceSlider) {
      balanceSlider.addEventListener('input', (e) => {
        this.customerFilterBalance = parseFloat(e.target.value) || 0;
        const balLabel = document.getElementById('cust-filter-balance-label');
        if (balLabel) balLabel.textContent = `₹0 - ${formatCurrency(this.customerFilterBalance)}`;
      });
    }

    const btnApplyFilter = document.getElementById('btn-apply-cust-filter');
    if (btnApplyFilter) {
      btnApplyFilter.addEventListener('click', () => {
        const dot = document.getElementById('cust-filter-dot');
        const isFiltered = (this.customerFilterBalance < this.customerMaxBalance) || this.customerFilterDate;
        if (dot) dot.style.display = isFiltered ? 'block' : 'none';
        this.applyCustomerFilters();
        this.closeModal('customer-filter-modal');
      });
    }

    // Customer Detail Modal actions
    const cdmClose = document.getElementById('cdm-btn-close');
    if (cdmClose) {
      cdmClose.addEventListener('click', () => this.closeModal('customer-detail-modal'));
    }

    const cdmCloseCustomer = document.getElementById('cdm-btn-close-customer');
    if (cdmCloseCustomer) {
      cdmCloseCustomer.addEventListener('click', async () => {
        if (!this.activeCustomerDetail) return;
        const c = this.activeCustomerDetail;
        const confirmed = window.confirm(`Are you sure you want to request account closure for ${c.name} (A.no: ${c.ano})?`);
        if (confirmed) {
          await this.requestAccountClosure(c);
          this.closeModal('customer-detail-modal');
        }
      });
    }

    // ---------------- Payments Screen ----------------
    const payBack = document.getElementById('pay-btn-back');
    if (payBack) {
      payBack.addEventListener('click', () => this.switchView('dashboard'));
    }

    const payPostingPill = document.getElementById('pay-btn-posting');
    if (payPostingPill) {
      payPostingPill.addEventListener('click', () => this.switchView('posting'));
    }

    const paySearch = document.getElementById('payments-search-input');
    if (paySearch) {
      paySearch.addEventListener('input', (e) => {
        this.paymentSearchQuery = e.target.value.trim().toLowerCase();
        this.computeDashboardMetrics();
    this.renderPaymentDateGroups();
      });
    }

    // Payment Date Detail Modal Close
    const pddClose = document.getElementById('pdd-btn-close');
    if (pddClose) {
      pddClose.addEventListener('click', () => this.closeModal('payment-date-detail-modal'));
    }

    // ---------------- Posting Screen ----------------
    const postBack = document.getElementById('post-btn-back');
    if (postBack) {
      postBack.addEventListener('click', () => {
        const dest = (this.previousView && this.previousView !== 'posting') ? this.previousView : 'dashboard';
        this.switchView(dest);
      });
    }

    const dateChip = document.getElementById('post-date-chip');
    const realDateInput = document.getElementById('pay-date-input');
    if (dateChip && realDateInput) {
      realDateInput.value = this.selectedPostingDate;
      const label = document.getElementById('post-date-label');
      if (label) label.textContent = formatDateDisplay(this.selectedPostingDate);

      dateChip.addEventListener('click', () => {
        if (typeof realDateInput.showPicker === 'function') {
          realDateInput.showPicker();
        } else {
          realDateInput.click();
        }
      });

      realDateInput.addEventListener('change', (e) => {
        this.selectedPostingDate = normalizeDateStr(e.target.value);
        if (label) label.textContent = formatDateDisplay(this.selectedPostingDate);
        this.checkPostingDuplicate();
        this.updatePostButtonState();
      });
    }

    const payAnoInput = document.getElementById('pay-ano');
    if (payAnoInput) {
      payAnoInput.addEventListener('input', (e) => {
        this.lookupPostingCustomer(e.target.value);
      });
    }

    // Payment Mode buttons (Cash / UPI / Partial)
    const btnCash = document.getElementById('btn-mode-cash');
    const btnUpi = document.getElementById('btn-mode-upi');
    const btnPartial = document.getElementById('btn-mode-partial');
    const partialFields = document.getElementById('partial-split-fields');

    const setPostingMode = (mode) => {
      this.selectedPostingMode = mode;
      if (btnCash) btnCash.classList.toggle('active', mode === 'cash');
      if (btnUpi) btnUpi.classList.toggle('active', mode === 'upi');
      if (btnPartial) btnPartial.classList.toggle('active', mode === 'partial');
      if (partialFields) partialFields.style.display = mode === 'partial' ? 'flex' : 'none';
      this.updatePostButtonState();
    };

    if (btnCash) btnCash.addEventListener('click', () => setPostingMode('cash'));
    if (btnUpi) btnUpi.addEventListener('click', () => setPostingMode('upi'));
    if (btnPartial) btnPartial.addEventListener('click', () => setPostingMode('partial'));

    const payAmountInput = document.getElementById('pay-amount');
    if (payAmountInput) {
      payAmountInput.addEventListener('input', () => this.updatePostButtonState());
    }

    const postBtn = document.getElementById('pay-post-btn');
    if (postBtn) {
      postBtn.addEventListener('click', async () => {
        await this.handlePaymentSubmit();
      });
    }

    // ---------------- Add Customer Screen ----------------
    const addCustBack = document.getElementById('addcust-btn-back');
    if (addCustBack) {
      addCustBack.addEventListener('click', () => this.switchView('dashboard'));
    }

    const btnPendingQueue = document.getElementById('btn-pending-queue');
    if (btnPendingQueue) {
      btnPendingQueue.addEventListener('click', () => this.switchView('sync'));
    }

    // Photo buttons
    this._bindPhotoPicker('btn-photo-front', 'file-photo-front', 'label-photo-front', 'front', 'Aadhaar Front');
    this._bindPhotoPicker('btn-photo-back', 'file-photo-back', 'label-photo-back', 'back', 'Aadhaar Back');
    this._bindPhotoPicker('btn-photo-house', 'file-photo-house', 'label-photo-house', 'house', 'House Photo');

    // Parent A/C Lookup
    const panoInput = document.getElementById('new-pano');
    let panoDebounce = null;
    if (panoInput) {
      panoInput.addEventListener('input', (e) => {
        clearTimeout(panoDebounce);
        panoDebounce = setTimeout(() => {
          this.lookupParentCustomer(e.target.value);
        }, 350);
      });
    }

    // Loan Type Toggle (Weekly / Monthly)
    const segWeekly = document.getElementById('seg-loan-weekly');
    const segMonthly = document.getElementById('seg-loan-monthly');
    if (segWeekly && segMonthly) {
      segWeekly.addEventListener('click', () => {
        this.newCustLoanType = 'W';
        segWeekly.classList.add('active');
        segMonthly.classList.remove('active');
        this.calculateEndDate();
      });
      segMonthly.addEventListener('click', () => {
        this.newCustLoanType = 'M';
        segMonthly.classList.add('active');
        segWeekly.classList.remove('active');
        this.calculateEndDate();
      });
    }

    // Period & Dates
    const periodInput = document.getElementById('new-period');
    if (periodInput) {
      periodInput.addEventListener('input', () => {
        this.calculateInstallment();
        this.calculateEndDate();
      });
    }

    const btnStartDate = document.getElementById('btn-start-date');
    const inputStartDate = document.getElementById('input-start-date');
    if (btnStartDate && inputStartDate) {
      inputStartDate.value = this.newCustStartDate;
      const startLabel = document.getElementById('start-date-label');
      if (startLabel) startLabel.textContent = formatDateDisplay(this.newCustStartDate);

      btnStartDate.addEventListener('click', () => {
        if (typeof inputStartDate.showPicker === 'function') {
          inputStartDate.showPicker();
        } else {
          inputStartDate.click();
        }
      });

      inputStartDate.addEventListener('change', (e) => {
        this.newCustStartDate = e.target.value;
        if (startLabel) startLabel.textContent = formatDateDisplay(this.newCustStartDate);
        this.calculateEndDate();
      });
    }

    // Financial calculations
    const totalAmtInput = document.getElementById('new-total-amt');
    const baseAmtInput = document.getElementById('new-base-amt');
    const cuttingAmtInput = document.getElementById('new-cutting-amt');
    const interestAmtInput = document.getElementById('new-interest-amt');

    if (totalAmtInput) {
      totalAmtInput.addEventListener('input', () => this.updateComponentsFromTotal());
    }

    const onComponentChange = () => this.updateTotalFromComponents();
    if (baseAmtInput) baseAmtInput.addEventListener('input', onComponentChange);
    if (cuttingAmtInput) cuttingAmtInput.addEventListener('input', onComponentChange);
    if (interestAmtInput) interestAmtInput.addEventListener('input', onComponentChange);

    // Disbursement Mode Toggle (Cash / UPI / Partial)
    const disbCash = document.getElementById('seg-disb-cash');
    const disbUpi = document.getElementById('seg-disb-upi');
    const disbPartial = document.getElementById('seg-disb-partial');

    const setDisbMode = (mode) => {
      this.newCustDisbursementMode = mode;
      if (disbCash) disbCash.classList.toggle('active', mode === 'CASH');
      if (disbUpi) disbUpi.classList.toggle('active', mode === 'UPI');
      if (disbPartial) disbPartial.classList.toggle('active', mode === 'PARTIAL');
    };

    if (disbCash) disbCash.addEventListener('click', () => setDisbMode('CASH'));
    if (disbUpi) disbUpi.addEventListener('click', () => setDisbMode('UPI'));
    if (disbPartial) disbPartial.addEventListener('click', () => setDisbMode('PARTIAL'));

    // Pull Location
    const btnPullLoc = document.getElementById('btn-pull-location');
    if (btnPullLoc) {
      btnPullLoc.addEventListener('click', async () => {
        btnPullLoc.disabled = true;
        btnPullLoc.innerHTML = `<span class="ms-icon" style="font-size:18px;">hourglass_top</span><span>Pulling Location...</span>`;
        try {
          const pos = await window.geoService.getCurrentPosition();
          document.getElementById('new-lat').value = pos.coords.latitude.toFixed(6);
          document.getElementById('new-lng').value = pos.coords.longitude.toFixed(6);
          this.showToast('Location captured', 'my_location');
        } catch (err) {
          this.showToast('Could not get GPS: ' + err.message, 'warning');
        } finally {
          btnPullLoc.disabled = false;
          btnPullLoc.innerHTML = `<span class="ms-icon" style="font-size:18px;">my_location</span><span>Pull Location</span>`;
        }
      });
    }

    // Add Customer Form Submit
    const addCustForm = document.getElementById('add-customer-form');
    if (addCustForm) {
      addCustForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await this.handleAddCustomerSubmit();
      });
    }

    // ---------------- Submission Queue / Sync Screen ----------------
    const syncBack = document.getElementById('sync-btn-back');
    if (syncBack) {
      syncBack.addEventListener('click', () => this.switchView('dashboard'));
    }

    const btnSyncNow = document.getElementById('btn-sync-now');
    if (btnSyncNow) {
      btnSyncNow.addEventListener('click', async () => {
        btnSyncNow.disabled = true;
        btnSyncNow.textContent = 'SYNCING...';
        await window.syncManager.syncAll();
        btnSyncNow.disabled = false;
        btnSyncNow.textContent = 'SYNC NOW';
        await this.renderSyncQueue();
        this.computeDashboardMetrics();
      });
    }

    // ---------------- Floating Bottom Dock Actions ----------------
    document.querySelectorAll('.dock-icon-item').forEach(item => {
      item.addEventListener('click', () => {
        const action = item.dataset.action;
        if (action === 'profile') {
          this.openProfileModal();
        } else {
          this.switchView(action);
        }
      });
    });

    // ---------------- Profile Modal ----------------
    const profileModal = document.getElementById('profile-modal');
    if (profileModal) {
      profileModal.addEventListener('click', (e) => {
        if (e.target.id === 'profile-modal' || e.target.classList.contains('sheet-drag-handle')) {
          this.closeModal('profile-modal');
        }
      });
    }

    const btnSignOut = document.getElementById('btn-signout-modal');
    if (btnSignOut) {
      btnSignOut.addEventListener('click', async () => {
        await this.handleLogout();
      });
    }
  }

  _bindPhotoPicker(btnId, fileInputId, labelId, photoKey, defaultText) {
    const btn = document.getElementById(btnId);
    const input = document.getElementById(fileInputId);
    const label = document.getElementById(labelId);
    if (!btn || !input) return;

    btn.addEventListener('click', () => input.click());

    input.addEventListener('change', async (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) {
        this.newCustPhotos[photoKey] = file;
        btn.classList.add('has-photo');
        if (label) label.textContent = '✓ ' + defaultText;
        this.showToast(`${defaultText} attached`, 'check_circle');
      }
    });
  }

  /* --------------------------------------------------------------------------
     Navigation & Routing
     -------------------------------------------------------------------------- */
  switchView(viewName) {
    if (this.currentView && this.currentView !== viewName) {
      this.previousView = this.currentView;
    }
    this.currentView = viewName;

    // Toggle view containers
    document.querySelectorAll('.view-section').forEach(sec => {
      sec.classList.remove('active');
    });
    const target = document.getElementById(`view-${viewName}`);
    if (target) target.classList.add('active');

    // Update Background Gradients
    const container = document.getElementById('screen-container');
    const body = document.body;
    container.className = 'app-screen-container';
    body.className = '';

    if (viewName === 'dashboard') {
      container.classList.add('bg-cobalt');
      body.classList.add('bg-cobalt');
    } else if (viewName === 'villages' || viewName === 'login') {
      container.classList.add('bg-atmospheric');
      body.classList.add('bg-atmospheric');
    } else {
      container.classList.add('bg-obsidian');
      body.classList.add('bg-obsidian');
    }

    // STRICT ANDROID PARITY: Floating Dock is visible ONLY on DashboardScreen
    const dock = document.getElementById('bottom-dock');
    if (dock) {
      if (viewName === 'dashboard') {
        dock.style.display = 'flex';
      } else {
        dock.style.display = 'none';
      }
    }

    // View specific initialization hooks
    if (viewName === 'dashboard') {
      this.renderDashboard();
    } else if (viewName === 'customers') {
      this.renderCustomerCards();
    } else if (viewName === 'payments') {
      this.loadPayments(this.selectedVid);
    } else if (viewName === 'posting') {
      this.initPostingView();
    } else if (viewName === 'add-customer') {
      this.initAddCustomerView();
    } else if (viewName === 'sync') {
      this.renderSyncQueue();
    }

    window.scrollTo(0, 0);
  }

  closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.style.display = 'none';
  }

  openModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.style.display = 'flex';
  }

  /* --------------------------------------------------------------------------
     Auth & Login
     -------------------------------------------------------------------------- */
  async handleLogin() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error');
    const submitBtn = document.getElementById('login-btn');

    errorEl.style.display = 'none';
    submitBtn.disabled = true;
    submitBtn.textContent = 'SIGNING IN...';
    this.showProgressBar(true);

    try {
      const res = await window.apiClient.login(username, password);
      const name = res.employee_name || username;
      const empEl = document.getElementById('profile-modal-name');
      if (empEl) empEl.textContent = name;

      this.showToast(`Welcome, ${name}!`, 'check_circle');
      await this.loadVillages();
      this.switchView('villages');
    } catch (err) {
      errorEl.textContent = err.message || 'Login failed. Please check credentials.';
      errorEl.style.display = 'block';
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Sign In';
      this.showProgressBar(false);
    }
  }

  async handleLogout() {
    await window.apiClient.logout();
    this.closeModal('profile-modal');
    this.switchView('login');
    this.showToast('Signed out', 'logout');
  }

  openProfileModal() {
    this.openModal('profile-modal');
  }

  /* --------------------------------------------------------------------------
     Villages Screen
     -------------------------------------------------------------------------- */
  async loadVillages() {
    this.showProgressBar(true);
    try {
      this.villages = await window.apiClient.getVillages();
    } catch (_) {
      this.villages = await window.dbService.getVillages();
    } finally {
      this.showProgressBar(false);
    }

    const badge = document.getElementById('villages-count-badge');
    if (badge) badge.textContent = this.villages.length;
    this.renderVillages(this.villages);
  }

  filterVillages(query) {
    const q = query.trim().toLowerCase();
    if (!q) {
      this.renderVillages(this.villages);
      return;
    }
    const filtered = this.villages.filter(v => {
      const name = (v.village_name || v.name || '').toLowerCase();
      const code = (v.village_code || v.code || '').toLowerCase();
      const dist = (v.district || '').toLowerCase();
      return name.includes(q) || code.includes(q) || dist.includes(q);
    });
    this.renderVillages(filtered);
  }

  renderVillages(list) {
    const container = document.getElementById('villages-grid-container');
    if (!container) return;

    if (list.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 40px 16px;">
          No villages found
        </div>`;
      return;
    }

    container.innerHTML = list.map((v, idx) => {
      const code = v.village_code || v.code || 'V' + (v.vid || v.id);
      const name = v.village_name || v.name || 'Unnamed Village';
      const district = v.district || 'SD Finance Route';
      const isSelected = this.selectedVid && String(this.selectedVid) === String(v.vid || v.id);
      const [grad1, grad2] = CODE_GLOW_COLORS[idx % CODE_GLOW_COLORS.length];

      return `
        <div class="village-card ${isSelected ? 'selected' : ''}" data-vid="${v.vid || v.id}">
          <div class="village-code-pill" style="background: linear-gradient(135deg, ${grad1}, ${grad2});">
            ${code}
          </div>
          <div>
            <div class="village-name">${name}</div>
            <div class="village-district">${district}</div>
          </div>
        </div>
      `;
    }).join('');

    container.querySelectorAll('.village-card').forEach(card => {
      card.addEventListener('click', async () => {
        const vid = card.dataset.vid;
        const found = this.villages.find(v => String(v.vid || v.id) === String(vid));
        if (found) {
          await this.selectVillage(found);
        }
      });
    });
  }

  async selectVillage(village) {
    this.selectedVid = village.vid || village.id;
    this.selectedVillage = village;
    await window.dbService.setSession('selected_vid', this.selectedVid);

    const dashTitle = document.getElementById('dash-village-title');
    if (dashTitle) {
      dashTitle.textContent = village.village_name || village.name;
    }

    this.showProgressBar(true);
    await Promise.all([
      this.loadCustomers(this.selectedVid),
      this.loadPayments(this.selectedVid),
      this.loadClosedCustomers(this.selectedVid)
    ]);
    this.showProgressBar(false);

    this.switchView('dashboard');
    window.syncManager.syncAll();
  }

  async loadClosedCustomers(vid) {
    if (!vid) return;
    try {
      this.closedCustomers = await window.apiClient.getClosedCustomers(vid);
    } catch (_) {
      this.closedCustomers = await window.dbService.getClosedCustomers(vid);
    }
    this.computeDashboardMetrics();
  }

  /* --------------------------------------------------------------------------
     Dashboard Screen
     -------------------------------------------------------------------------- */
  async renderDashboard() {
    if (this.selectedVillage) {
      const dashTitle = document.getElementById('dash-village-title');
      if (dashTitle) {
        dashTitle.textContent = this.selectedVillage.village_name || this.selectedVillage.name;
      }
    }
    this.computeDashboardMetrics();
    this.updatePendingBadges();
  }

  computeDashboardMetrics() {
    let activeCount = 0;
    let totalBal = 0;

    for (const c of (this.customers || [])) {
      const bal = parseFloat(c.balance !== undefined ? c.balance : c.balance_amount || 0);
      const isClosed = (c.status || '').toLowerCase() === 'closed';
      if (!isClosed) {
        activeCount++;
        totalBal += bal;
      }
    }

    const avgBal = activeCount > 0 ? (totalBal / activeCount) : 0;
    const closedCount = (this.closedCustomers && this.closedCustomers.length > 0)
      ? this.closedCustomers.length
      : (this.customers || []).filter(c => (c.status || '').toLowerCase() === 'closed').length;

    this.dashboardData = {
      activeCustomers: activeCount,
      totalBalance: totalBal,
      averageBalance: avgBal,
      closedAccounts: closedCount,
    };

    this.updateMetricsDisplay();
    this.computeDashboardDecks();
  }

  computeDashboardDecks() {
    // 1. Resolve collection weekday from confirmed payments
    const counts = {};
    for (const p of (this.allPayments || [])) {
      const norm = normalizeDateStr(p.payment_date);
      if (!norm) continue;
      const parts = norm.split('-');
      if (parts.length === 3) {
        const dt = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
        const wd = dt.getDay();
        counts[wd] = (counts[wd] || 0) + 1;
      }
    }
    let collectionWeekday = 4; // default Thursday (matches Baroda village)
    let maxC = 0;
    for (const [wd, c] of Object.entries(counts)) {
      if (c > maxC) {
        maxC = c;
        collectionWeekday = parseInt(wd, 10);
      }
    }

    // 2. Resolve collection dates (up to 12 weeks back)
    const dateSet = new Set();
    for (const p of (this.allPayments || [])) {
      const norm = normalizeDateStr(p.payment_date);
      if (norm && norm.length === 10) dateSet.add(norm);
    }
    let cur = new Date();
    while (cur.getDay() !== collectionWeekday) {
      cur.setDate(cur.getDate() - 1);
    }
    for (let i = 0; i < 12; i++) {
      const y = cur.getFullYear();
      const m = String(cur.getMonth() + 1).padStart(2, '0');
      const d = String(cur.getDate()).padStart(2, '0');
      dateSet.add(`${y}-${m}-${d}`);
      cur.setDate(cur.getDate() - 7);
    }
    const collectionDates = Array.from(dateSet).sort((a, b) => b.localeCompare(a)).slice(0, 12);

    // 3. Compute Missing Payments (Payment Skipped Groups)
    this.paymentSkippedGroups = [];
    for (const dKey of collectionDates) {
      const paidAnos = new Set();
      for (const p of (this.allPayments || [])) {
        if (normalizeDateStr(p.payment_date) === dKey) {
          if (p.ano) paidAnos.add(parseInt(p.ano, 10));
        }
      }
      for (const p of (this.todayLocalPayments || [])) {
        if (normalizeDateStr(p.payment_date) === dKey) {
          if (p.ano) paidAnos.add(parseInt(p.ano, 10));
        }
      }

      const skippedCusts = [];
      for (const c of (this.customers || [])) {
        const ano = parseInt(c.ano, 10);
        if (isNaN(ano) || paidAnos.has(ano)) continue;
        const isClosed = (c.status || '').toLowerCase() === 'closed';
        if (isClosed) continue;
        const sDate = normalizeDateStr(c.start_date);
        if (sDate && sDate > dKey) continue;
        skippedCusts.push({
          ano: ano,
          name: c.name || '',
          balanceAmount: parseFloat(c.balance !== undefined ? c.balance : c.balance_amount || 0)
        });
      }
      skippedCusts.sort((a, b) => a.ano - b.ano);
      if (skippedCusts.length > 0) {
        this.paymentSkippedGroups.push({
          weekDate: dKey,
          count: skippedCusts.length,
          customers: skippedCusts
        });
      }
    }
    this.totalSkipped = this.paymentSkippedGroups.reduce((sum, g) => sum + g.count, 0);

    // Check if live posting is active today
    const todayStr = normalizeDateStr(new Date());
    const hasPendingToday = (this.todayLocalPayments || []).some(p => normalizeDateStr(p.payment_date || p.created_at) === todayStr);
    this.isPostingActiveToday = hasPendingToday;
    if (this.isPostingActiveToday) {
      const paidToday = new Set();
      for (const p of (this.allPayments || [])) {
        if (normalizeDateStr(p.payment_date) === todayStr && p.ano) paidToday.add(parseInt(p.ano, 10));
      }
      for (const p of (this.todayLocalPayments || [])) {
        if (normalizeDateStr(p.payment_date) === todayStr && p.ano) paidToday.add(parseInt(p.ano, 10));
      }
      this.todayMissingCustomers = (this.customers || []).filter(c => {
        const ano = parseInt(c.ano, 10);
        const isClosed = (c.status || '').toLowerCase() === 'closed';
        return !isClosed && !isNaN(ano) && !paidToday.has(ano);
      }).map(c => ({
        ano: parseInt(c.ano, 10),
        name: c.name || '',
        balanceAmount: parseFloat(c.balance !== undefined ? c.balance : c.balance_amount || 0)
      })).sort((a, b) => a.ano - b.ano);
      this.todayMissingCount = this.todayMissingCustomers.length;
    }

    // 4. Update Missing Payments Deck UI
    const missingWrap = document.getElementById('deck-missing-icon-wrap');
    const missingIcon = document.getElementById('deck-missing-icon');
    const missingCount = document.getElementById('deck-missing-count');
    const missingBadge = document.getElementById('deck-missing-live-badge');
    const missingSub = document.getElementById('deck-missing-subtitle');

    if (this.isPostingActiveToday) {
      if (missingWrap) {
        missingWrap.style.background = 'rgba(16, 185, 129, 0.16)';
        missingWrap.style.color = '#10B981';
      }
      if (missingIcon) missingIcon.textContent = 'bolt';
      if (missingCount) missingCount.textContent = `${this.todayMissingCount} unposted today`;
      if (missingBadge) missingBadge.style.display = 'flex';
      if (missingSub) missingSub.textContent = 'Live posting active • Tap to view';
    } else {
      if (missingWrap) {
        missingWrap.style.background = 'rgba(239, 68, 68, 0.16)';
        missingWrap.style.color = '#EF4444';
      }
      if (missingIcon) missingIcon.textContent = 'arrow_downward';
      if (missingCount) missingCount.textContent = `${this.totalSkipped} skipped`;
      if (missingBadge) missingBadge.style.display = 'none';
      const latestSkipped = this.paymentSkippedGroups.length > 0
        ? `Latest: ${formatDmy(this.paymentSkippedGroups[0].weekDate)}`
        : 'No payment skipped';
      if (missingSub) missingSub.textContent = latestSkipped;
    }

    // 5. Compute Closed Customers Groups
    const closedBuckets = {};
    for (const c of (this.closedCustomers || [])) {
      const closedAt = normalizeDateStr(c.closed_at || c.updated_at || c.freeze_date);
      if (!closedAt) continue;
      const parts = closedAt.split('-');
      if (parts.length !== 3) continue;
      const dt = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
      while (dt.getDay() !== collectionWeekday) {
        dt.setDate(dt.getDate() - 1);
      }
      const y = dt.getFullYear();
      const m = String(dt.getMonth() + 1).padStart(2, '0');
      const d = String(dt.getDate()).padStart(2, '0');
      const bKey = `${y}-${m}-${d}`;
      if (!closedBuckets[bKey]) closedBuckets[bKey] = [];
      closedBuckets[bKey].push({
        ano: parseInt(c.ano, 10),
        name: c.name || '',
        balanceAmount: parseFloat(c.balance_amount || c.balance || 0)
      });
    }

    // Fallback to active customers with status=closed if closed_customers is empty
    if (Object.keys(closedBuckets).length === 0) {
      for (const c of (this.customers || [])) {
        if ((c.status || '').toLowerCase() === 'closed') {
          const closedAt = normalizeDateStr(c.updated_at || c.freeze_date || c.start_date);
          if (!closedAt) continue;
          const parts = closedAt.split('-');
          if (parts.length !== 3) continue;
          const dt = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
          while (dt.getDay() !== collectionWeekday) {
            dt.setDate(dt.getDate() - 1);
          }
          const y = dt.getFullYear();
          const m = String(dt.getMonth() + 1).padStart(2, '0');
          const d = String(dt.getDate()).padStart(2, '0');
          const bKey = `${y}-${m}-${d}`;
          if (!closedBuckets[bKey]) closedBuckets[bKey] = [];
          closedBuckets[bKey].push({
            ano: parseInt(c.ano, 10),
            name: c.name || '',
            balanceAmount: parseFloat(c.balance_amount || c.balance || 0)
          });
        }
      }
    }

    this.closedCustomerGroups = Object.keys(closedBuckets).sort((a, b) => b.localeCompare(a)).map(bKey => {
      const custs = closedBuckets[bKey].sort((a, b) => a.ano - b.ano);
      return {
        weekDate: bKey,
        count: custs.length,
        customers: custs
      };
    });

    this.totalClosed = (this.closedCustomers && this.closedCustomers.length > 0)
      ? this.closedCustomers.length
      : this.closedCustomerGroups.reduce((s, g) => s + g.count, 0);

    // 6. Update Closed Customers Deck UI
    const closedCount = document.getElementById('deck-closed-count');
    const closedSub = document.getElementById('deck-closed-subtitle');
    if (closedCount) closedCount.textContent = `${this.totalClosed} closed`;
    const latestClosed = this.closedCustomerGroups.length > 0
      ? `Latest: ${formatDmy(this.closedCustomerGroups[0].weekDate)}`
      : 'No closed customers';
    if (closedSub) closedSub.textContent = latestClosed;
  }

  openMissingPaymentsModal() {
    const titleEl = document.getElementById('mpm-title');
    const subEl = document.getElementById('mpm-subtitle');
    const historyBtn = document.getElementById('mpm-btn-history');
    const container = document.getElementById('mpm-content-container');
    if (!container) return;

    if (this.isPostingActiveToday) {
      if (titleEl) titleEl.textContent = 'Live Unposted Customers';
      if (subEl) subEl.textContent = `${this.todayMissingCount} unposted today`;
      if (historyBtn) historyBtn.style.display = 'flex';
      this.renderTodayMissingCustomersList();
    } else {
      if (titleEl) titleEl.textContent = 'Missing Payments';
      if (subEl) subEl.textContent = `${this.totalSkipped} skipped`;
      if (historyBtn) historyBtn.style.display = 'none';
      this.renderMissingPaymentsHistory(false);
    }

    this.openModal('missing-payments-modal');
  }

  renderMissingPaymentsHistory(showBackToLive) {
    const titleEl = document.getElementById('mpm-title');
    const subEl = document.getElementById('mpm-subtitle');
    const historyBtn = document.getElementById('mpm-btn-history');
    const container = document.getElementById('mpm-content-container');
    if (!container) return;

    if (titleEl) titleEl.textContent = 'Missing Payments';
    if (subEl) subEl.textContent = `${this.totalSkipped} skipped`;
    if (historyBtn) historyBtn.style.display = 'none';

    if (this.paymentSkippedGroups.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; color: rgba(255, 255, 255, 0.4); padding: 36px 16px; font-size: 14px;">
          No payment skipped
        </div>`;
      return;
    }

    container.innerHTML = this.paymentSkippedGroups.map((group, idx) => `
      <div class="deck-group-card">
        <div class="deck-group-header" data-idx="${idx}">
          <div class="deck-group-header-left">
            <div class="deck-group-icon red">
              <span class="ms-icon" style="font-size: 18px;">arrow_downward</span>
            </div>
            <div>
              <div class="deck-group-title">${formatDmy(group.weekDate)}</div>
              <div class="deck-group-subtitle red">${group.count} customers skipped</div>
            </div>
          </div>
          <span class="ms-icon deck-group-chevron" style="color: rgba(255, 255, 255, 0.4); font-size: 22px;">expand_more</span>
        </div>
        <div class="deck-group-body" id="mpm-group-body-${idx}">
          ${group.customers.map(c => `
            <div class="deck-customer-row">
              <div>
                <div style="font-size: 14px; font-weight: 700; color: #FFFFFF;">${c.name.toUpperCase()}</div>
                <div style="font-size: 12px; color: rgba(255, 255, 255, 0.5); margin-top: 2px;">A.No: ${c.ano}</div>
              </div>
              <div style="font-size: 15px; font-weight: 800; color: #FFFFFF;">${formatCurrency(c.balanceAmount)}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');

    container.querySelectorAll('.deck-group-header').forEach(header => {
      header.addEventListener('click', () => {
        const idx = header.dataset.idx;
        const body = document.getElementById(`mpm-group-body-${idx}`);
        const chevron = header.querySelector('.deck-group-chevron');
        if (body) {
          const isOpen = body.classList.toggle('open');
          if (chevron) chevron.textContent = isOpen ? 'expand_less' : 'expand_more';
        }
      });
    });
  }

  renderTodayMissingCustomersList() {
    const container = document.getElementById('mpm-content-container');
    if (!container) return;

    if (!this.todayMissingCustomers || this.todayMissingCustomers.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; color: var(--primary); padding: 36px 16px; font-size: 14px; font-weight: 700;">
          All customers posted today!
        </div>`;
      return;
    }

    container.innerHTML = `
      <div style="padding: 0 4px 10px; font-size: 12px; color: rgba(255, 255, 255, 0.5); font-weight: 600;">
        Tap any customer to open Posting
      </div>
      ${this.todayMissingCustomers.map(c => `
        <div class="deck-customer-row" style="cursor: pointer;" data-ano="${c.ano}">
          <div>
            <div style="font-size: 14px; font-weight: 700; color: #FFFFFF;">${c.name.toUpperCase()}</div>
            <div style="font-size: 12px; color: rgba(255, 255, 255, 0.5); margin-top: 2px;">A.No: ${c.ano}</div>
          </div>
          <div style="font-size: 15px; font-weight: 800; color: var(--primary);">${formatCurrency(c.balanceAmount)}</div>
        </div>
      `).join('')}
    `;

    container.querySelectorAll('.deck-customer-row[data-ano]').forEach(row => {
      row.addEventListener('click', () => {
        const ano = row.dataset.ano;
        this.closeModal('missing-payments-modal');
        this.switchView('posting');
        const payAnoInput = document.getElementById('pay-ano');
        if (payAnoInput) {
          payAnoInput.value = ano;
          this.lookupPostingCustomer(ano);
        }
      });
    });
  }

  openClosedCustomersModal() {
    const subEl = document.getElementById('ccm-subtitle');
    const container = document.getElementById('ccm-content-container');
    if (!container) return;

    if (subEl) subEl.textContent = `${this.totalClosed} closed`;

    if (this.closedCustomerGroups.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; color: rgba(255, 255, 255, 0.4); padding: 36px 16px; font-size: 14px;">
          No closed customers
        </div>`;
      return;
    }

    container.innerHTML = this.closedCustomerGroups.map((group, idx) => `
      <div class="deck-group-card">
        <div class="deck-group-header" data-idx="${idx}">
          <div class="deck-group-header-left">
            <div class="deck-group-icon green">
              <span class="ms-icon" style="font-size: 18px;">check_circle</span>
            </div>
            <div>
              <div class="deck-group-title">${formatDmy(group.weekDate)}</div>
              <div class="deck-group-subtitle green">${group.count} customers closed</div>
            </div>
          </div>
          <span class="ms-icon deck-group-chevron" style="color: rgba(255, 255, 255, 0.4); font-size: 22px;">expand_more</span>
        </div>
        <div class="deck-group-body" id="ccm-group-body-${idx}">
          ${group.customers.map(c => `
            <div class="deck-customer-row">
              <div>
                <div style="font-size: 14px; font-weight: 700; color: #FFFFFF;">${c.name.toUpperCase()}</div>
                <div style="font-size: 12px; color: rgba(255, 255, 255, 0.5); margin-top: 2px;">A.No: ${c.ano}</div>
              </div>
              <div style="font-size: 15px; font-weight: 800; color: var(--primary);">${formatCurrency(c.balanceAmount)}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');

    container.querySelectorAll('.deck-group-header').forEach(header => {
      header.addEventListener('click', () => {
        const idx = header.dataset.idx;
        const body = document.getElementById(`ccm-group-body-${idx}`);
        const chevron = header.querySelector('.deck-group-chevron');
        if (body) {
          const isOpen = body.classList.toggle('open');
          if (chevron) chevron.textContent = isOpen ? 'expand_less' : 'expand_more';
        }
      });
    });

    this.openModal('closed-customers-modal');
  }

  cycleMetricsPage() {
    this.currentMetricPage = (this.currentMetricPage + 1) % 3;
    this.updateMetricsDisplay();
  }

  setMetricsPage(idx) {
    this.currentMetricPage = idx;
    this.updateMetricsDisplay();
  }

  updateMetricsDisplay() {
    const valEl = document.getElementById('dash-metric-value');
    const labelEl = document.getElementById('dash-metric-label');
    if (!valEl || !labelEl) return;

    if (this.currentMetricPage === 0) {
      valEl.textContent = this.dashboardData.activeCustomers.toLocaleString();
      labelEl.textContent = 'Active Customers';
    } else if (this.currentMetricPage === 1) {
      valEl.textContent = formatCurrency(this.dashboardData.totalBalance);
      labelEl.textContent = 'Total Balance';
    } else {
      valEl.textContent = formatCurrency(this.dashboardData.averageBalance);
      labelEl.textContent = 'Average Balance';
    }

    document.querySelectorAll('.metric-dot').forEach((dot, idx) => {
      dot.classList.toggle('active', idx === this.currentMetricPage);
    });
  }

  /* --------------------------------------------------------------------------
     Customers Screen (Image 3 & 4 Parity)
     -------------------------------------------------------------------------- */
  async loadCustomers(vid) {
    try {
      this.customers = await window.apiClient.getCustomers(vid);
    } catch (_) {
      this.customers = await window.dbService.getCustomers(vid);
    }

    // Sort descending by ANO as in Android screenshot 3
    this.customers.sort((a, b) => (parseInt(b.ano, 10) || 0) - (parseInt(a.ano, 10) || 0));

    // Calculate max balance for filter slider
    let maxBal = 100000;
    for (const c of this.customers) {
      const b = parseFloat(c.balance || c.balance_amount || 0);
      if (b > maxBal) maxBal = b;
    }
    this.customerMaxBalance = Math.ceil(maxBal / 1000) * 1000;
    this.customerFilterBalance = this.customerMaxBalance;

    const slider = document.getElementById('cust-filter-balance-slider');
    if (slider) {
      slider.max = this.customerMaxBalance;
      slider.value = this.customerMaxBalance;
    }
    const balLabel = document.getElementById('cust-filter-balance-label');
    if (balLabel) {
      balLabel.textContent = `₹0 - ${formatCurrency(this.customerMaxBalance)}`;
    }

    this.applyCustomerFilters();
    this.computeDashboardMetrics();
  }

  applyCustomerFilters() {
    this.filteredCustomers = this.customers.filter(c => {
      // 1. Search Query
      if (this.customerSearchQuery) {
        const q = this.customerSearchQuery;
        const name = (c.name || '').toLowerCase();
        const ano = String(c.ano || '');
        const phone = String(c.phone || c.phone_number || '');
        if (!name.includes(q) && !ano.includes(q) && !phone.includes(q)) {
          return false;
        }
      }

      // 2. Balance Range Filter
      const bal = parseFloat(c.balance || c.balance_amount || 0);
      if (bal > this.customerFilterBalance) {
        return false;
      }

      // 3. Start Date Filter
      if (this.customerFilterDate) {
        const cDate = normalizeDateStr(c.start_date);
        if (cDate && cDate !== this.customerFilterDate) {
          return false;
        }
      }

      return true;
    });

    const countLabel = document.getElementById('cust-count-label');
    if (countLabel) countLabel.textContent = this.filteredCustomers.length;

    this.renderCustomerCards();
  }

  renderCustomerCards() {
    const container = document.getElementById('customers-cards-container');
    if (!container) return;

    if (this.filteredCustomers.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 48px 16px;">
          No matching customers found
        </div>`;
      return;
    }

    container.innerHTML = this.filteredCustomers.map(c => {
      const ano = c.ano || '0';
      const name = (c.name || 'Unnamed').toUpperCase();
      const bal = formatCurrency(c.balance !== undefined ? c.balance : c.balance_amount);
      const total = formatCurrency(c.loan_amount || c.total_amount);
      const startD = formatDateDDMMYYYY(c.start_date);
      const endD = formatDateDDMMYYYY(c.end_date);
      const isClosed = (c.status || '').toLowerCase() === 'closed';

      return `
        <div class="customer-card-2line" data-ano="${ano}">
          <div class="cust-avatar-circle active-grad">
            ${ano}
          </div>
          <div class="cust-details-2line">
            <div class="cust-line-1">
              <span class="cust-name">${name}</span>
              <span class="cust-balance">${bal}</span>
            </div>
            <div class="cust-line-2">
              <span class="cust-meta">Total: ${total} • ${startD} - ${endD}</span>
              <span class="${isClosed ? 'cust-status-pending' : 'cust-status-active'}">
                ${isClosed ? 'Closed' : 'Active'}
              </span>
            </div>
          </div>
        </div>
      `;
    }).join('');

    container.querySelectorAll('.customer-card-2line').forEach(card => {
      card.addEventListener('click', () => {
        const ano = card.dataset.ano;
        const customer = this.customers.find(c => String(c.ano) === String(ano));
        if (customer) {
          this.openCustomerDetailModal(customer);
        }
      });
    });
  }

  openCustomerDetailModal(c) {
    this.activeCustomerDetail = c;
    const initial = (c.name || 'C').charAt(0).toUpperCase();

    const avatar = document.getElementById('cdm-avatar');
    if (avatar) avatar.textContent = initial;

    const nameEl = document.getElementById('cdm-name');
    if (nameEl) nameEl.textContent = (c.name || 'Customer').toUpperCase();

    const subEl = document.getElementById('cdm-ano-subtitle');
    if (subEl) subEl.textContent = `Account #${c.ano}`;

    const phoneEl = document.getElementById('cdm-phone');
    const phone = c.phone || c.phone_number || '-';
    if (phoneEl) {
      phoneEl.textContent = phone;
      phoneEl.href = phone !== '-' ? `tel:${phone}` : '#';
    }

    const locEl = document.getElementById('cdm-location');
    const lat = c.latitude || (c.raw && c.raw.latitude);
    const lng = c.longitude || (c.raw && c.raw.longitude);
    if (locEl) {
      locEl.textContent = (lat && lng) ? `${parseFloat(lat).toFixed(4)}, ${parseFloat(lng).toFixed(4)}` : '-';
    }

    const panoEl = document.getElementById('cdm-pano');
    if (panoEl) panoEl.textContent = c.pano || '-';

    const durEl = document.getElementById('cdm-duration');
    const sDate = formatDateDDMMYYYY(c.start_date);
    const eDate = formatDateDDMMYYYY(c.end_date);
    if (durEl) durEl.textContent = `${sDate} → ${eDate}`;

    const total = parseFloat(c.total_amount || c.loan_amount || 0);
    const bal = parseFloat(c.balance || c.balance_amount || 0);
    const paid = parseFloat(c.paid_amount || Math.max(0, total - bal));

    const totalEl = document.getElementById('cdm-total-loan');
    if (totalEl) totalEl.textContent = formatCurrency(total);

    const paidEl = document.getElementById('cdm-paid-amount');
    if (paidEl) paidEl.textContent = formatCurrency(paid);

    const balEl = document.getElementById('cdm-balance-amount');
    if (balEl) balEl.textContent = formatCurrency(bal);

    this.openModal('customer-detail-modal');
  }

  async requestAccountClosure(c) {
    const eid = await window.dbService.getSession('eid');
    const deviceId = await window.apiClient.getDeviceId();
    const payload = {
      local_uuid: generateUUID(),
      ano: parseInt(c.ano, 10),
      vid: parseInt(c.vid || this.selectedVid, 10),
      eid: parseInt(eid || 0, 10),
      reason: 'Requested from mobile PWA',
      device_id: deviceId,
      created_at: new Date().toISOString()
    };

    try {
      await window.apiClient.closeAccountFeed(payload);
      this.showToast('Account closure request submitted', 'check_circle');
    } catch (_) {
      await window.dbService.queueCloseAccount(payload);
      this.showToast('Closure request queued offline', 'cloud_queue');
    }

    this.updatePendingBadges();
  }

  openCustomerFilterModal() {
    this.openModal('customer-filter-modal');
  }

  /* --------------------------------------------------------------------------
     Payments Screen (Image 9 & 10 Parity)
     -------------------------------------------------------------------------- */
  async loadPayments(vid) {
    if (!vid) return;
    this.showProgressBar(true);

    try {
      const serverPayments = await window.apiClient.getPayments(vid);
      this.allPayments = (serverPayments || []).map(p => ({
        ...p,
        payment_date: normalizeDateStr(p.payment_date || p.pdate || p.created_at)
      }));
    } catch (_) {
      const dbPayments = await window.dbService.getPayments(vid);
      this.allPayments = (dbPayments || []).map(p => ({
        ...p,
        payment_date: normalizeDateStr(p.payment_date || p.pdate || p.created_at)
      }));
    } finally {
      this.showProgressBar(false);
    }

    // Merge pending payments from IndexedDB
    const pending = await window.dbService.getPendingPayments();
    for (const p of pending) {
      if (String(p.vid) === String(vid)) {
        this.allPayments.unshift({
          ano: p.ano,
          amt: p.amt,
          payment_date: normalizeDateStr(p.payment_date || p.pdate || p.created_at),
          payment_type: p.payment_type || 'CASH',
          customer_name: p.customer_name || `Customer #${p.ano}`,
          status: 'pending',
          is_pending: true,
          local_uuid: p.local_uuid
        });
      }
    }

    this.computeDashboardMetrics();
    this.renderPaymentDateGroups();
  }

  renderPaymentDateGroups() {
    const container = document.getElementById('payments-cards-container');
    if (!container) return;

    // Filter by search query
    let filtered = this.allPayments;
    if (this.paymentSearchQuery) {
      const q = this.paymentSearchQuery.toLowerCase();
      filtered = filtered.filter(p => {
        const dStr = (p.payment_date || '').toLowerCase();
        const fDate = formatDateDisplay(p.payment_date).toLowerCase();
        const ano = String(p.ano || '');
        const name = (p.customer_name || '').toLowerCase();
        return dStr.includes(q) || fDate.includes(q) || ano.includes(q) || name.includes(q);
      });
    }

    // Group by payment_date descending
    const groupsMap = {};
    for (const p of filtered) {
      const dKey = normalizeDateStr(p.payment_date || p.pdate || p.created_at);
      if (!dKey) continue;
      if (!groupsMap[dKey]) groupsMap[dKey] = [];
      groupsMap[dKey].push(p);
    }

    const sortedDates = Object.keys(groupsMap).sort((a, b) => b.localeCompare(a));
    this.paymentDateGroups = sortedDates.map(dateKey => {
      const items = groupsMap[dateKey];
      let total = 0;
      const customersSet = new Set();
      let hasPending = false;
      for (const item of items) {
        total += parseFloat(item.amt || item.amount || 0);
        if (item.ano) customersSet.add(item.ano);
        if (item.is_pending || item.status === 'pending') hasPending = true;
      }
      return {
        dateStr: dateKey,
        customerCount: customersSet.size,
        totalAmount: total,
        payments: items,
        hasPending: hasPending
      };
    });

    if (this.paymentDateGroups.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 48px 16px;">
          No payment groups found
        </div>`;
      return;
    }

    container.innerHTML = this.paymentDateGroups.map(grp => {
      const dispDate = formatDateDisplay(grp.dateStr);
      const weekday = getDayOfWeek(grp.dateStr);
      const totalStr = formatRawCurrency(grp.totalAmount);
      const custStr = `${grp.customerCount} Customers`;

      return `
        <div class="payment-date-card ${grp.hasPending ? 'has-pending' : ''}" data-date="${grp.dateStr}">
          <div class="pay-calendar-box ${grp.hasPending ? 'pending' : ''}">
            <span class="ms-icon" style="font-size: 20px;">calendar_today</span>
          </div>
          <div class="pay-card-details">
            <div class="pay-line-1">
              <div style="display: flex; align-items: center; gap: 6px; min-width: 0;">
                <span class="pay-date-text">${dispDate}</span>
                ${grp.hasPending ? '<span class="cust-status-pending">PENDING</span>' : ''}
              </div>
              <span class="pay-total-amount">${totalStr}</span>
            </div>
            <div class="pay-line-2">
              <span class="pay-weekday-text">${weekday}</span>
              <span class="pay-count-badge">${custStr}</span>
            </div>
          </div>
          <span class="ms-icon" style="color: rgba(255, 255, 255, 0.38); font-size: 20px; margin-left: 6px;">chevron_right</span>
        </div>
      `;
    }).join('');

    container.querySelectorAll('.payment-date-card').forEach(card => {
      card.addEventListener('click', () => {
        const dStr = card.dataset.date;
        const grp = this.paymentDateGroups.find(g => g.dateStr === dStr);
        if (grp) {
          this.openPaymentDateDetailModal(grp);
        }
      });
    });
  }

  openPaymentDateDetailModal(group) {
    this.activePaymentDateGroup = group;

    const titleEl = document.getElementById('pdd-date-title');
    if (titleEl) titleEl.textContent = formatDateDisplay(group.dateStr);

    const subEl = document.getElementById('pdd-subtitle');
    const weekday = getDayOfWeek(group.dateStr);
    if (subEl) subEl.textContent = `${weekday} • ${group.customerCount} Customers`;

    const totalEl = document.getElementById('pdd-total-badge');
    if (totalEl) totalEl.textContent = formatCurrency(group.totalAmount);

    const container = document.getElementById('pdd-rows-container');
    if (!container) return;

    // Sort customer payment rows by ANO ascending as in screenshot 10
    const sorted = [...group.payments].sort((a, b) => (parseInt(a.ano, 10) || 0) - (parseInt(b.ano, 10) || 0));

    // Match customer names
    const custMap = {};
    for (const c of this.customers) {
      custMap[c.ano] = c.name;
    }

    container.innerHTML = sorted.map(p => {
      const ano = p.ano || '0';
      const name = p.customer_name || custMap[ano] || `Customer #${ano}`;
      const amtStr = formatCurrency(p.amt || p.amount || 0);
      const isPending = p.is_pending || (p.status === 'pending');
      const pType = (p.payment_type || 'CASH').toUpperCase();

      return `
        <div class="date-payment-row">
          <div class="date-payment-left">
            <div class="ano-circle-sm">${ano}</div>
            <div>
              <div style="font-size: 14.5px; font-weight: 800; color: #FFFFFF; margin-bottom: 3px;">
                ${name.toUpperCase()}
              </div>
              <div style="display: flex; gap: 6px;">
                <span class="tag-badge cash">${pType}</span>
                <span class="tag-badge ${isPending ? 'pending' : 'approved'}">${isPending ? 'PENDING' : 'APPROVED'}</span>
              </div>
            </div>
          </div>
          <div style="font-size: 16px; font-weight: 800; color: #FFFFFF;">
            ${amtStr}
          </div>
        </div>
      `;
    }).join('');

    this.openModal('payment-date-detail-modal');
  }

  /* --------------------------------------------------------------------------
     Posting Screen (Image 6 & 8 Parity)
     -------------------------------------------------------------------------- */
  initPostingView() {
    this.selectedPostingCustomer = null;
    this.selectedPostingDate = normalizeDateStr(new Date());
    this.selectedPostingMode = 'cash';
    this.isPostingDuplicate = false;

    const payAno = document.getElementById('pay-ano');
    if (payAno) payAno.value = '';

    const payAmt = document.getElementById('pay-amount');
    if (payAmt) payAmt.value = '';

    const inlinePreview = document.getElementById('pay-inline-customer');
    if (inlinePreview) inlinePreview.style.display = 'none';

    const dupWarning = document.getElementById('pay-duplicate-warning');
    if (dupWarning) dupWarning.style.display = 'none';

    const fillLink = document.getElementById('pay-fill-installment');
    if (fillLink) fillLink.style.display = 'none';

    const postDateInput = document.getElementById('pay-date-input');
    if (postDateInput) postDateInput.value = this.selectedPostingDate;

    const postDateLabel = document.getElementById('post-date-label');
    if (postDateLabel) postDateLabel.textContent = formatDateDisplay(this.selectedPostingDate);

    this.updatePostButtonState();
    this.renderPostingPending();
  }

  lookupPostingCustomer(anoQuery) {
    const q = anoQuery.trim();
    const inlineBox = document.getElementById('pay-inline-customer');
    const nameEl = document.getElementById('pay-customer-name');
    const balEl = document.getElementById('pay-customer-balance');
    const fillLink = document.getElementById('pay-fill-installment');

    if (!q) {
      this.selectedPostingCustomer = null;
      if (inlineBox) inlineBox.style.display = 'none';
      if (fillLink) fillLink.style.display = 'none';
      this.checkPostingDuplicate();
      this.updatePostButtonState();
      return;
    }

    const found = this.customers.find(c => String(c.ano) === q);
    if (found) {
      this.selectedPostingCustomer = found;
      if (inlineBox && nameEl && balEl) {
        nameEl.textContent = (found.name || 'Customer').toUpperCase();
        balEl.textContent = `Bal: ${formatCurrency(found.balance !== undefined ? found.balance : found.balance_amount)}`;
        inlineBox.style.display = 'flex';
      }

      const emi = found.installment || found.installment_amount || 0;
      if (fillLink) {
        if (emi > 0) {
          fillLink.textContent = `Fill Installment (${formatCurrency(emi)})`;
          fillLink.style.display = 'block';
          fillLink.onclick = () => {
            const amtInput = document.getElementById('pay-amount');
            if (amtInput) {
              amtInput.value = emi;
              this.updatePostButtonState();
            }
          };
        } else {
          fillLink.style.display = 'none';
        }
      }

      // Pre-fill installment if amount is empty
      const amtInput = document.getElementById('pay-amount');
      if (amtInput && !amtInput.value && emi > 0) {
        amtInput.value = emi;
      }
    } else {
      this.selectedPostingCustomer = null;
      if (inlineBox) inlineBox.style.display = 'none';
      if (fillLink) fillLink.style.display = 'none';
    }

    this.checkPostingDuplicate();
    this.updatePostButtonState();
  }

  checkPostingDuplicate() {
    const dupWarning = document.getElementById('pay-duplicate-warning');
    const dupText = document.getElementById('pay-duplicate-text');
    if (!dupWarning) return;

    if (!this.selectedPostingCustomer) {
      this.isPostingDuplicate = false;
      dupWarning.style.display = 'none';
      return;
    }

    const ano = String(this.selectedPostingCustomer.ano);
    const dateStr = normalizeDateStr(this.selectedPostingDate);

    const isDup = this.allPayments.some(p => {
      const pDate = normalizeDateStr(p.payment_date || p.pdate || p.created_at);
      return String(p.ano) === ano && pDate === dateStr;
    });

    this.isPostingDuplicate = isDup;
    if (isDup) {
      if (dupText) dupText.textContent = `Payment already recorded for this date`;
      dupWarning.style.display = 'flex';
    } else {
      dupWarning.style.display = 'none';
    }
  }

  updatePostButtonState() {
    const postBtn = document.getElementById('pay-post-btn');
    const postIcon = document.getElementById('pay-post-icon');
    const postText = document.getElementById('pay-post-text');
    if (!postBtn) return;

    const amtInput = document.getElementById('pay-amount');
    const amt = parseFloat(amtInput ? amtInput.value : 0) || 0;

    if (this.isPostingDuplicate) {
      postBtn.className = 'btn-post-payment duplicate';
      if (postIcon) postIcon.textContent = 'block';
      if (postText) postText.textContent = 'ALREADY POSTED';
      postBtn.disabled = true;
    } else if (this.selectedPostingCustomer && amt > 0) {
      postBtn.className = 'btn-post-payment active';
      if (postIcon) postIcon.textContent = 'check_circle';
      if (postText) postText.textContent = `POST (${formatCurrency(amt)})`;
      postBtn.disabled = false;
    } else {
      postBtn.className = 'btn-post-payment';
      if (postIcon) postIcon.textContent = 'check_circle';
      if (postText) postText.textContent = 'POST PAYMENT';
      postBtn.disabled = true;
    }
  }

  async handlePaymentSubmit() {
    if (!this.selectedPostingCustomer) {
      this.showToast('Please enter a valid Account Number', 'warning');
      return;
    }

    const amtInput = document.getElementById('pay-amount');
    const amt = parseFloat(amtInput ? amtInput.value : 0) || 0;

    if (amt <= 0) {
      this.showToast('Please enter an amount greater than 0', 'warning');
      return;
    }

    const eid = await window.dbService.getSession('eid');
    const deviceId = await window.apiClient.getDeviceId();
    const localUuid = generateUUID();

    let cashPortion = this.selectedPostingMode === 'cash' ? amt : 0;
    let upiPortion = this.selectedPostingMode === 'upi' ? amt : 0;

    if (this.selectedPostingMode === 'partial') {
      const cSplit = parseFloat(document.getElementById('pay-cash-split').value) || 0;
      const uSplit = parseFloat(document.getElementById('pay-upi-split').value) || 0;
      cashPortion = cSplit;
      upiPortion = uSplit;
    }

    const paymentItem = {
      local_uuid: localUuid,
      ano: parseInt(this.selectedPostingCustomer.ano, 10),
      vid: parseInt(this.selectedPostingCustomer.vid || this.selectedVid, 10),
      eid: parseInt(eid || 0, 10),
      amt: amt,
      cash_amount: cashPortion,
      upi_amount: upiPortion,
      payment_date: this.selectedPostingDate,
      payment_type: this.selectedPostingMode.toUpperCase(),
      customer_name: this.selectedPostingCustomer.name,
      device_id: deviceId,
      created_at: new Date().toISOString()
    };

    // Save to IndexedDB queue
    await window.dbService.queuePayment(paymentItem);

    // Locally deduct customer balance
    await window.dbService.updateCustomerLocalBalance(paymentItem.vid, paymentItem.ano, amt);
    const inMem = this.customers.find(c => String(c.ano) === String(paymentItem.ano));
    if (inMem) {
      inMem.balance = Math.max(0, (inMem.balance || 0) - amt);
      if (inMem.balance_amount !== undefined) inMem.balance_amount = inMem.balance;
    }

    // Keep in local pending for current session
    this.todayLocalPayments.unshift(paymentItem);
    this.allPayments.unshift({
      ...paymentItem,
      status: 'pending',
      is_pending: true
    });

    this.showToast(`₹${amt} recorded for #${paymentItem.ano}!`, 'check_circle');

    // Reset inputs for rapid subsequent postings
    this.lookupPostingCustomer('');
    if (document.getElementById('pay-ano')) document.getElementById('pay-ano').value = '';
    if (amtInput) amtInput.value = '';
    document.getElementById('pay-ano').focus();

    this.renderPostingPending();
    this.updatePendingBadges();

    // Trigger background sync
    window.syncManager.syncAll();
  }

  renderPostingPending() {
    const container = document.getElementById('posting-pending-container');
    if (!container) return;

    if (this.todayLocalPayments.length === 0) {
      container.innerHTML = `
        <div class="no-pending-box">
          No pending submissions
        </div>`;
      return;
    }

    // Group pending payments by normalized date
    const groups = {};
    for (const p of this.todayLocalPayments) {
      const dKey = normalizeDateStr(p.payment_date || p.created_at) || 'Pending';
      if (!groups[dKey]) groups[dKey] = [];
      groups[dKey].push(p);
    }

    const dateKeys = Object.keys(groups);
    container.innerHTML = dateKeys.map(dKey => {
      const items = groups[dKey];
      let total = 0;
      for (const it of items) total += parseFloat(it.amt || 0);
      const dispDate = formatDateDisplay(dKey);

      return `
        <div class="pending-stack-card" data-date="${dKey}">
          <div class="pending-avatar-box">
            <span class="ms-icon" style="font-size: 22px; color: #F59E0B;">layers</span>
          </div>
          <div class="pending-info-col">
            <div style="font-size: 15px; font-weight: 800; color: #FFFFFF;">${dispDate}</div>
            <div style="font-size: 12px; color: rgba(255, 255, 255, 0.55); font-weight: 500;">
              ${items.length} accounts • Tap to view & edit
            </div>
          </div>
          <div class="pending-total-pill">
            ${formatCurrency(total)}
          </div>
          <span class="ms-icon" style="color: rgba(255, 255, 255, 0.5); font-size: 20px; margin-left: 6px;">chevron_right</span>
        </div>
      `;
    }).join('');

    container.querySelectorAll('.pending-stack-card').forEach(card => {
      card.addEventListener('click', () => {
        const dStr = card.dataset.date;
        const items = groups[dStr];
        if (items) {
          this.openPaymentDateDetailModal({
            dateStr: dStr,
            customerCount: items.length,
            totalAmount: items.reduce((s, it) => s + parseFloat(it.amt || 0), 0),
            payments: items
          });
        }
      });
    });
  }

  /* --------------------------------------------------------------------------
     Add Customer Screen (Image 5 & 7 Parity)
     -------------------------------------------------------------------------- */
  async initAddCustomerView() {
    // 1. Calculate next account number = max(ano) + 1
    let maxAno = 1000;
    for (const c of this.customers) {
      const a = parseInt(c.ano, 10);
      if (!isNaN(a) && a > maxAno) maxAno = a;
    }
    const nextAno = maxAno + 1;

    const anoPill = document.getElementById('ctx-ano-pill');
    if (anoPill) anoPill.textContent = `#${nextAno}`;

    // 2. Village Bank Name
    const bankName = (this.selectedVillage && (this.selectedVillage.bank_name || this.selectedVillage.bank || 'BARODA')).toUpperCase();
    const bankEl = document.getElementById('ctx-bank-name');
    if (bankEl) bankEl.textContent = bankName;

    // 3. Employee Name
    const empName = await window.dbService.getSession('employee_name') || 'EMPLOYEE';
    const empEl = document.getElementById('ctx-emp-name');
    if (empEl) empEl.textContent = empName.toUpperCase();

    // 4. Rates
    const intRate = (this.selectedVillage && this.selectedVillage.interest_rate) || 16.7;
    const cutRate = (this.selectedVillage && this.selectedVillage.cutting_rate) || 1.7;
    const ratesLabel = document.getElementById('ctx-rates-label');
    if (ratesLabel) ratesLabel.textContent = `% Int: ${intRate}% • Cut: ${cutRate}%`;

    // Reset fields
    this.newCustLoanType = 'W';
    this.newCustDisbursementMode = 'CASH';
    this.newCustStartDate = new Date().toISOString().split('T')[0];
    this.newCustPhotos = { front: null, back: null, house: null };

    document.getElementById('new-pano').value = '';
    document.getElementById('new-name').value = '';
    document.getElementById('new-phone').value = '';
    document.getElementById('new-aadhaar').value = '';
    document.getElementById('new-notes').value = '';
    document.getElementById('new-period').value = '100';
    document.getElementById('new-total-amt').value = '';
    document.getElementById('new-installment').value = '';
    document.getElementById('new-base-amt').value = '';
    document.getElementById('new-cutting-amt').value = '';
    document.getElementById('new-interest-amt').value = '';
    document.getElementById('new-lat').value = '';
    document.getElementById('new-lng').value = '';

    const startLabel = document.getElementById('start-date-label');
    if (startLabel) startLabel.textContent = formatDateDisplay(this.newCustStartDate);
    this.calculateEndDate();

    // Reset photo buttons
    ['front', 'back', 'house'].forEach(k => {
      const btn = document.getElementById(`btn-photo-${k}`);
      if (btn) btn.classList.remove('has-photo');
    });
    if (document.getElementById('label-photo-front')) document.getElementById('label-photo-front').textContent = 'Aadhaar Front';
    if (document.getElementById('label-photo-back')) document.getElementById('label-photo-back').textContent = 'Aadhaar Back';
    if (document.getElementById('label-photo-house')) document.getElementById('label-photo-house').textContent = 'House Photo';

    this.updatePendingBadges();
  }

  async lookupParentCustomer(pano) {
    const p = pano.trim();
    if (!p) return;

    // Check loaded customers first
    let found = this.customers.find(c => String(c.ano) === p);
    if (!found) {
      try {
        found = await window.apiClient.getParentCustomerInfo(this.selectedVid, p);
      } catch (_) {}
    }

    if (found) {
      const nameInput = document.getElementById('new-name');
      const phoneInput = document.getElementById('new-phone');
      const notesInput = document.getElementById('new-notes');

      if (nameInput && !nameInput.value) nameInput.value = (found.name || '').toUpperCase();
      if (phoneInput && !phoneInput.value) phoneInput.value = found.phone || found.phone_number || '';
      if (notesInput && !notesInput.value) notesInput.value = found.notes || '';

      this.showToast(`Parent customer #${p} found`, 'check_circle');
    }
  }

  updateComponentsFromTotal() {
    if (this.isUpdatingAmounts) return;
    this.isUpdatingAmounts = true;

    const totalInput = document.getElementById('new-total-amt');
    const total = parseFloat(totalInput ? totalInput.value : 0) || 0;

    const intRate = (this.selectedVillage && this.selectedVillage.interest_rate) || 16.7;
    const cutRate = (this.selectedVillage && this.selectedVillage.cutting_rate) || 1.7;

    if (total > 0) {
      const interest = Math.round(total * intRate / 100.0);
      const cutting = Math.round(total * cutRate / 100.0);
      const base = total - interest - cutting;

      document.getElementById('new-interest-amt').value = interest;
      document.getElementById('new-cutting-amt').value = cutting;
      document.getElementById('new-base-amt').value = base;
    } else {
      document.getElementById('new-interest-amt').value = '';
      document.getElementById('new-cutting-amt').value = '';
      document.getElementById('new-base-amt').value = '';
    }

    this.isUpdatingAmounts = false;
    this.calculateInstallment();
    this.validateMath();
  }

  updateTotalFromComponents() {
    if (this.isUpdatingAmounts) return;
    this.isUpdatingAmounts = true;

    const base = parseFloat(document.getElementById('new-base-amt').value) || 0;
    const cut = parseFloat(document.getElementById('new-cutting-amt').value) || 0;
    const int = parseFloat(document.getElementById('new-interest-amt').value) || 0;
    const total = base + cut + int;

    document.getElementById('new-total-amt').value = total || '';

    this.isUpdatingAmounts = false;
    this.calculateInstallment();
    this.validateMath();
  }

  calculateInstallment() {
    const total = parseFloat(document.getElementById('new-total-amt').value) || 0;
    const period = parseInt(document.getElementById('new-period').value, 10) || 0;
    const instEl = document.getElementById('new-installment');

    if (instEl && period > 0 && total > 0) {
      instEl.value = Math.round(total / period);
    }
  }

  calculateEndDate() {
    const period = parseInt(document.getElementById('new-period').value, 10) || 0;
    const endLabel = document.getElementById('end-date-label');
    if (!endLabel || period <= 0 || !this.newCustStartDate) {
      if (endLabel) endLabel.textContent = '-';
      return;
    }

    try {
      const d = new Date(this.newCustStartDate);
      if (this.newCustLoanType === 'W') {
        d.setDate(d.getDate() + (period * 7));
      } else {
        d.setMonth(d.getMonth() + period);
      }
      endLabel.textContent = formatDateDisplay(d.toISOString().split('T')[0]);
    } catch (_) {
      endLabel.textContent = '-';
    }
  }

  validateMath() {
    const helper = document.getElementById('math-helper-label');
    if (!helper) return;

    const total = parseFloat(document.getElementById('new-total-amt').value) || 0;
    const base = parseFloat(document.getElementById('new-base-amt').value) || 0;
    const cut = parseFloat(document.getElementById('new-cutting-amt').value) || 0;
    const int = parseFloat(document.getElementById('new-interest-amt').value) || 0;

    const sum = base + cut + int;
    if (total > 0 && Math.abs(total - sum) > 1) {
      helper.textContent = `Warning: Base + Cut + Int (${sum}) ≠ Total (${total})`;
      helper.style.color = 'var(--danger)';
    } else {
      helper.textContent = 'Must equal base + cutting + interest';
      helper.style.color = 'var(--text-subtle)';
    }
  }

  async handleAddCustomerSubmit() {
    const name = document.getElementById('new-name').value.trim();
    const phone = document.getElementById('new-phone').value.trim();
    const totalAmt = parseFloat(document.getElementById('new-total-amt').value) || 0;
    const period = parseInt(document.getElementById('new-period').value, 10) || 0;

    if (!name) {
      this.showToast('Customer Name is required', 'warning');
      return;
    }
    if (totalAmt <= 0) {
      this.showToast('Please enter a valid Total Amount', 'warning');
      return;
    }

    // Auto calculate ANO = max(ano) + 1
    let maxAno = 1000;
    for (const c of this.customers) {
      const a = parseInt(c.ano, 10);
      if (!isNaN(a) && a > maxAno) maxAno = a;
    }
    const ano = maxAno + 1;

    const eid = await window.dbService.getSession('eid');
    const deviceId = await window.apiClient.getDeviceId();
    const localUuid = generateUUID();

    const newCustomer = {
      local_uuid: localUuid,
      ano: ano,
      vid: parseInt(this.selectedVid, 10),
      eid: parseInt(eid || 0, 10),
      name: name.toUpperCase(),
      phone_number: phone,
      pano: document.getElementById('new-pano').value.trim() || null,
      aadhaar_number: document.getElementById('new-aadhaar').value.trim() || null,
      notes: document.getElementById('new-notes').value.trim() || null,
      total_amount: totalAmt,
      base_amount: parseFloat(document.getElementById('new-base-amt').value) || 0,
      cutting_amount: parseFloat(document.getElementById('new-cutting-amt').value) || 0,
      interest_amount: parseFloat(document.getElementById('new-interest-amt').value) || 0,
      installment_amount: parseFloat(document.getElementById('new-installment').value) || 0,
      loan_type: this.newCustLoanType,
      period: period,
      start_date: this.newCustStartDate,
      disbursement_mode: this.newCustDisbursementMode,
      latitude: parseFloat(document.getElementById('new-lat').value) || null,
      longitude: parseFloat(document.getElementById('new-lng').value) || null,
      device_id: deviceId,
      created_at: new Date().toISOString()
    };

    // Save to IndexedDB pending queue
    await window.dbService.queueCustomer(newCustomer);

    // Optimistically add to local customers list
    this.customers.unshift({
      ...newCustomer,
      balance: totalAmt,
      balance_amount: totalAmt,
      loan_amount: totalAmt,
      status: 'pending'
    });

    this.showToast(`Customer #${ano} created!`, 'check_circle');
    this.updatePendingBadges();

    // Trigger sync & return to customers view
    window.syncManager.syncAll();
    this.switchView('customers');
  }

  /* --------------------------------------------------------------------------
     Submission Queue / Sync Screen
     -------------------------------------------------------------------------- */
  async renderSyncQueue() {
    const listContainer = document.getElementById('sync-pending-list');
    const countEl = document.getElementById('sync-pending-count');
    if (!listContainer) return;

    const payments = await window.dbService.getPendingPayments();
    const customers = await window.dbService.getPendingCustomers();
    const closes = await window.dbService.getPendingCloseAccounts();

    const total = payments.length + customers.length + closes.length;
    if (countEl) countEl.textContent = total;

    if (total === 0) {
      listContainer.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); font-size: 13px; padding: 24px;">
          All transactions are synced!
        </div>`;
      return;
    }

    const items = [
      ...customers.map(c => ({
        type: 'Customer Create',
        title: `${(c.name || 'New Customer').toUpperCase()} (#${c.ano})`,
        meta: `Amount: ${formatCurrency(c.total_amount)} • ${formatDateDisplay(c.created_at)}`,
        status: c.sync_status || 'pending',
        icon: 'person_add'
      })),
      ...payments.map(p => ({
        type: 'Payment',
        title: `A/C #${p.ano} - ${formatCurrency(p.amt)}`,
        meta: `Mode: ${p.payment_type} • Date: ${formatDateDisplay(p.payment_date)}`,
        status: p.sync_status || 'pending',
        icon: 'payments'
      })),
      ...closes.map(cl => ({
        type: 'Account Closure',
        title: `Close A/C #${cl.ano}`,
        meta: `Reason: ${cl.reason || 'Requested'} • ${formatDateDisplay(cl.created_at)}`,
        status: cl.sync_status || 'pending',
        icon: 'person_off'
      }))
    ];

    listContainer.innerHTML = items.map(item => `
      <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.06);">
        <div style="display: flex; align-items: center; gap: 12px;">
          <div style="width: 36px; height: 36px; border-radius: 50%; background: rgba(16, 185, 129, 0.15); color: var(--primary); display: flex; align-items: center; justify-content: center;">
            <span class="ms-icon" style="font-size: 18px;">${item.icon}</span>
          </div>
          <div>
            <div style="font-size: 14px; font-weight: 800; color: #FFFFFF;">${item.title}</div>
            <div style="font-size: 12px; color: var(--text-muted);">${item.meta}</div>
          </div>
        </div>
        <span class="tag-badge ${item.status === 'failed' ? 'not-found' : 'pending'}">${item.status.toUpperCase()}</span>
      </div>
    `).join('');
  }

  async updatePendingBadges() {
    const count = await window.dbService.getPendingCount();

    const dockBadge = document.getElementById('dock-sync-badge');
    if (dockBadge) {
      dockBadge.textContent = count;
      dockBadge.style.display = count > 0 ? 'inline-block' : 'none';
    }

    const addCustBadge = document.getElementById('addcust-pending-count');
    if (addCustBadge) {
      addCustBadge.textContent = count;
    }
  }

  /* --------------------------------------------------------------------------
     Connectivity & Progress Helpers
     -------------------------------------------------------------------------- */
  _initOnlineListener() {
    window.addEventListener('online', () => this._updateOnlineBanner());
    window.addEventListener('offline', () => this._updateOnlineBanner());
    this._updateOnlineBanner();
  }

  _updateOnlineBanner() {
    const banner = document.getElementById('connectivity-banner');
    if (!banner) return;

    if (!navigator.onLine) {
      banner.className = 'status-banner banner-offline';
      banner.textContent = 'OFFLINE MODE • Transactions queued locally';
      banner.style.display = 'block';
    } else {
      banner.style.display = 'none';
    }
  }

  showProgressBar(show) {
    const bar = document.getElementById('global-progress-bar');
    if (bar) bar.style.display = show ? 'block' : 'none';
  }

  showToast(msg, icon = 'check_circle') {
    const toast = document.getElementById('app-toast');
    const toastMsg = document.getElementById('toast-msg');
    const toastIcon = document.getElementById('toast-icon');
    if (!toast) return;

    if (toastMsg) toastMsg.textContent = msg;
    if (toastIcon) toastIcon.textContent = icon;

    toast.style.display = 'flex';
    clearTimeout(this._toastTimeout);
    this._toastTimeout = setTimeout(() => {
      toast.style.display = 'none';
    }, 2800);
  }
}

// Safe initialization: run immediately if DOM is ready, or on DOMContentLoaded
function startApp() {
  if (!window.app) {
    try {
      window.app = new AppController();
      window.app.init().catch(err => {
        console.error('[App] Init failed:', err);
        if (window.app) window.app.switchView('login');
      });
    } catch (err) {
      console.error('[App] Fatal start error:', err);
      if (window.app) window.app.switchView('login');
    }
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startApp);
} else {
  startApp();
}
