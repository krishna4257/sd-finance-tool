/**
 * SD Finance PWA - IndexedDB Storage Engine (SDFinanceDB)
 * High-performance offline caching and transactional queue.
 */

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

class DBService {
  constructor() {
    this.dbName = 'SDFinanceDB';
    this.version = 3;
    this.db = null;
  }

  async open() {
    if (this.db) return this.db;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.version);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Session & Settings store
        if (!db.objectStoreNames.contains('session')) {
          db.createObjectStore('session', { keyPath: 'key' });
        }

        // Villages assigned to employee
        if (!db.objectStoreNames.contains('villages')) {
          db.createObjectStore('villages', { keyPath: 'id' });
        }

        // Cached customers per village
        if (!db.objectStoreNames.contains('customers')) {
          const custStore = db.createObjectStore('customers', { keyPath: 'composite_key' });
          custStore.createIndex('vid', 'vid', { unique: false });
          custStore.createIndex('ano', 'ano', { unique: false });
          custStore.createIndex('name', 'name', { unique: false });
        }

        // Offline payments queue
        if (!db.objectStoreNames.contains('pending_payments')) {
          const payStore = db.createObjectStore('pending_payments', { keyPath: 'local_uuid' });
          payStore.createIndex('sync_status', 'sync_status', { unique: false });
          payStore.createIndex('created_at', 'created_at', { unique: false });
        }

        // Offline newly created customers queue
        if (!db.objectStoreNames.contains('pending_customers')) {
          const newCustStore = db.createObjectStore('pending_customers', { keyPath: 'local_uuid' });
          newCustStore.createIndex('sync_status', 'sync_status', { unique: false });
        }

        // Cached confirmed payments per village
        if (!db.objectStoreNames.contains('payments')) {
          const paymentsStore = db.createObjectStore('payments', { keyPath: 'composite_key' });
          paymentsStore.createIndex('vid', 'vid', { unique: false });
          paymentsStore.createIndex('payment_date', 'payment_date', { unique: false });
          paymentsStore.createIndex('ano', 'ano', { unique: false });
        }

        // Cached closed customers per village
        if (!db.objectStoreNames.contains('closed_customers')) {
          const closedStore = db.createObjectStore('closed_customers', { keyPath: 'composite_key' });
          closedStore.createIndex('vid', 'vid', { unique: false });
          closedStore.createIndex('ano', 'ano', { unique: false });
        }

        // Offline account closure queue
        if (!db.objectStoreNames.contains('pending_close_accounts')) {
          const closeStore = db.createObjectStore('pending_close_accounts', { keyPath: 'local_uuid' });
          closeStore.createIndex('sync_status', 'sync_status', { unique: false });
        }
      };

      request.onsuccess = (event) => {
        this.db = event.target.result;
        resolve(this.db);
      };

      request.onerror = (event) => {
        console.error('Failed to open IndexedDB:', event.target.error);
        reject(event.target.error);
      };

      request.onblocked = (event) => {
        console.warn('IndexedDB upgrade blocked, proceed with existing or retry');
        if (event.target && event.target.result) {
          this.db = event.target.result;
          resolve(this.db);
        }
      };

      // Timeout watchdog: never hang indefinitely if IndexedDB is blocked
      setTimeout(() => {
        if (!this.db) {
          console.warn('IndexedDB open timeout; resolving without crashing');
          resolve(null);
        }
      }, 1500);
    });
  }

  async _tx(storeName, mode = 'readonly') {
    const db = await this.open();
    if (!db) throw new Error('IndexedDB not ready');
    return db.transaction(storeName, mode).objectStore(storeName);
  }

  // --- Session Storage ---
  async setSession(key, value) {
    try {
      localStorage.setItem('sdfin_sess_' + key, JSON.stringify(value));
    } catch (_) {}

    try {
      const store = await this._tx('session', 'readwrite');
      return new Promise((resolve) => {
        const req = store.put({ key, value });
        req.onsuccess = () => resolve();
        req.onerror = () => resolve();
      });
    } catch (_) {}
  }

  async getSession(key) {
    // Fast path: localStorage
    try {
      const raw = localStorage.getItem('sdfin_sess_' + key);
      if (raw !== null && raw !== undefined) {
        return JSON.parse(raw);
      }
    } catch (_) {}

    try {
      const store = await this._tx('session', 'readonly');
      return new Promise((resolve) => {
        const req = store.get(key);
        req.onsuccess = () => resolve(req.result ? req.result.value : null);
        req.onerror = () => resolve(null);
      });
    } catch (_) {
      return null;
    }
  }

  async clearSession() {
    try {
      const keys = ['token', 'eid', 'username', 'employee_name', 'role', 'selected_vid', 'login_time'];
      for (const k of keys) {
        localStorage.removeItem('sdfin_sess_' + k);
      }
    } catch (_) {}

    try {
      const store = await this._tx('session', 'readwrite');
      return new Promise((resolve) => {
        const req = store.clear();
        req.onsuccess = () => resolve();
        req.onerror = () => resolve();
      });
    } catch (_) {}
  }

  // --- Villages ---
  async saveVillages(villages) {
    const store = await this._tx('villages', 'readwrite');
    await new Promise((res) => { const req = store.clear(); req.onsuccess = () => res(); });
    for (const v of villages) {
      store.put({ id: v.id || v.vid, name: v.name || v.vname, ...v });
    }
  }

  async getVillages() {
    const store = await this._tx('villages', 'readonly');
    return new Promise((resolve) => {
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
  }

  // --- Customers Cache ---
  async saveCustomers(vid, customerList) {
    const store = await this._tx('customers', 'readwrite');
    for (const c of customerList) {
      const composite_key = `${vid}_${c.ano}`;
      store.put({
        composite_key,
        vid: parseInt(vid, 10),
        ano: parseInt(c.ano, 10),
        name: c.name || c.customer_name || '',
        phone: c.phone || '',
        loan_amount: parseFloat(c.total_amount || c.loan_amount || 0),
        balance: parseFloat(c.balance || c.current_balance || 0),
        installment: parseFloat(c.installment || c.emi || 0),
        status: c.status || 'active',
        raw: c
      });
    }
  }

  async getCustomersByVillage(vid) {
    const store = await this._tx('customers', 'readonly');
    const index = store.index('vid');
    return new Promise((resolve) => {
      const req = index.getAll(parseInt(vid, 10));
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
  }

  async searchCustomers(vid, query) {
    const all = await this.getCustomersByVillage(vid);
    if (!query || !query.trim()) return all;

    const q = query.trim().toLowerCase();
    return all.filter((c) => {
      const matchAno = c.ano && c.ano.toString().includes(q);
      const matchName = c.name && c.name.toLowerCase().includes(q);
      const matchPhone = c.phone && c.phone.includes(q);
      return matchAno || matchName || matchPhone;
    });
  }

  async updateCustomerLocalBalance(vid, ano, paidAmount) {
    const store = await this._tx('customers', 'readwrite');
    const composite_key = `${vid}_${ano}`;
    return new Promise((resolve) => {
      const req = store.get(composite_key);
      req.onsuccess = () => {
        if (req.result) {
          const c = req.result;
          c.balance = Math.max(0, c.balance - paidAmount);
          store.put(c);
        }
        resolve();
      };
      req.onerror = () => resolve();
    });
  }

  // --- Pending Payments Queue ---
  async queuePayment(payment) {
    const store = await this._tx('pending_payments', 'readwrite');
    payment.sync_status = 'pending';
    payment.created_at = payment.created_at || new Date().toISOString();
    return new Promise((resolve, reject) => {
      const req = store.put(payment);
      req.onsuccess = () => resolve(payment);
      req.onerror = () => reject(req.error);
    });
  }

  async getPendingPayments() {
    const store = await this._tx('pending_payments', 'readonly');
    return new Promise((resolve) => {
      const req = store.getAll();
      req.onsuccess = () => {
        const results = (req.result || []).filter(p => p.sync_status !== 'synced');
        resolve(results);
      };
      req.onerror = () => resolve([]);
    });
  }

  async getAllPayments() {
    const store = await this._tx('pending_payments', 'readonly');
    return new Promise((resolve) => {
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
  }

  async updatePaymentStatus(localUuid, status, error = null) {
    const store = await this._tx('pending_payments', 'readwrite');
    return new Promise((resolve) => {
      const req = store.get(localUuid);
      req.onsuccess = () => {
        if (req.result) {
          const p = req.result;
          p.sync_status = status;
          p.sync_error = error;
          p.synced_at = status === 'synced' ? new Date().toISOString() : null;
          store.put(p);
        }
        resolve();
      };
      req.onerror = () => resolve();
    });
  }

  // --- Pending Customers Queue ---
  async queueCustomer(customer) {
    const store = await this._tx('pending_customers', 'readwrite');
    customer.sync_status = 'pending';
    customer.created_at = customer.created_at || new Date().toISOString();
    return new Promise((resolve, reject) => {
      const req = store.put(customer);
      req.onsuccess = () => resolve(customer);
      req.onerror = () => reject(req.error);
    });
  }

  async getPendingCustomers() {
    const store = await this._tx('pending_customers', 'readonly');
    return new Promise((resolve) => {
      const req = store.getAll();
      req.onsuccess = () => {
        const results = (req.result || []).filter(c => c.sync_status !== 'synced');
        resolve(results);
      };
      req.onerror = () => resolve([]);
    });
  }

  async updateCustomerStatus(localUuid, status, error = null) {
    const store = await this._tx('pending_customers', 'readwrite');
    return new Promise((resolve) => {
      const req = store.get(localUuid);
      req.onsuccess = () => {
        if (req.result) {
          const c = req.result;
          c.sync_status = status;
          c.sync_error = error;
          store.put(c);
        }
        resolve();
      };
      req.onerror = () => resolve();
    });
  }

  async getPendingCount() {
    const payments = await this.getPendingPayments();
    const customers = await this.getPendingCustomers();
    const closes = await this.getPendingCloseAccounts();
    return payments.length + customers.length + closes.length;
  }

  // --- Confirmed Payments Store ---
  async savePayments(vid, paymentList) {
    const store = await this._tx('payments', 'readwrite');
    for (const p of paymentList) {
      const pid = p.pid || p.id || generateUUID();
      const composite_key = `${vid}_${pid}`;
      store.put({
        composite_key,
        vid: parseInt(vid, 10),
        pid: pid,
        ano: parseInt(p.ano, 10),
        amt: parseFloat(p.amt || p.amount || 0),
        payment_date: normalizeDateStr(p.payment_date || p.pdate || p.created_at || ''),
        payment_type: p.payment_type || 'CASH',
        cash_amount: parseFloat(p.cash_amount || 0),
        upi_amount: parseFloat(p.upi_amount || 0),
        created_at: p.created_at || '',
        customer_name: p.customer_name || (p.raw && p.raw.customer_name) || '',
        raw: p
      });
    }
  }

  async getPayments(vid) {
    const store = await this._tx('payments', 'readonly');
    const index = store.index('vid');
    return new Promise((resolve) => {
      const req = index.getAll(parseInt(vid, 10));
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
  }

  // --- Confirmed Closed Customers Store ---
  async saveClosedCustomers(vid, closedList) {
    if (!closedList || closedList.length === 0) return;
    const store = await this._tx('closed_customers', 'readwrite');
    for (const c of closedList) {
      const cid = c.cid || c.ano || generateUUID();
      const composite_key = `${vid}_${cid}`;
      store.put({
        composite_key,
        vid: parseInt(vid, 10),
        cid: cid,
        ano: parseInt(c.ano, 10),
        name: c.name || '',
        balance_amount: parseFloat(c.balance_amount || c.balance || 0),
        closed_at: normalizeDateStr(c.closed_at || c.updated_at || c.freeze_date || ''),
        raw: c
      });
    }
  }

  async getClosedCustomers(vid) {
    const store = await this._tx('closed_customers', 'readonly');
    const index = store.index('vid');
    return new Promise((resolve) => {
      const req = index.getAll(parseInt(vid, 10));
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
  }

  // --- Pending Close Accounts Queue ---
  async queueCloseAccount(item) {
    const store = await this._tx('pending_close_accounts', 'readwrite');
    item.sync_status = 'pending';
    item.created_at = item.created_at || new Date().toISOString();
    return new Promise((resolve, reject) => {
      const req = store.put(item);
      req.onsuccess = () => resolve(item);
      req.onerror = () => reject(req.error);
    });
  }

  async getPendingCloseAccounts() {
    const store = await this._tx('pending_close_accounts', 'readonly');
    return new Promise((resolve) => {
      const req = store.getAll();
      req.onsuccess = () => {
        const results = (req.result || []).filter(c => c.sync_status !== 'synced');
        resolve(results);
      };
      req.onerror = () => resolve([]);
    });
  }

  async updateCloseAccountStatus(localUuid, status, error = null) {
    const store = await this._tx('pending_close_accounts', 'readwrite');
    return new Promise((resolve) => {
      const req = store.get(localUuid);
      req.onsuccess = () => {
        if (req.result) {
          const item = req.result;
          item.sync_status = status;
          item.sync_error = error;
          store.put(item);
        }
        resolve();
      };
      req.onerror = () => resolve();
    });
  }

  // Aliases for convenience
  async addPendingPayment(payment) {
    return this.queuePayment(payment);
  }

  async addPendingCustomer(customer) {
    return this.queueCustomer(customer);
  }

  async updateCustomerBalance(vid, ano, newBalance) {
    const store = await this._tx('customers', 'readwrite');
    const composite_key = `${vid}_${ano}`;
    return new Promise((resolve) => {
      const req = store.get(composite_key);
      req.onsuccess = () => {
        if (req.result) {
          const c = req.result;
          c.balance = newBalance;
          c.balance_amount = newBalance;
          store.put(c);
        }
        resolve();
      };
      req.onerror = () => resolve();
    });
  }

  async getCustomers(vid) {
    return this.getCustomersByVillage(vid);
  }
}

window.dbService = new DBService();
