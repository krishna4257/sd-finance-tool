/**
 * SD Finance PWA - Mobile API Client
 * Interfaces directly with Flask /api/mobile endpoints using X-Mobile-Token.
 */
class ApiClient {
  constructor() {
    // Purge any stale development/local Wi-Fi IPs if running on production domain
    try {
      const savedBase = localStorage.getItem('sdfin_api_base_url');
      if (savedBase && (savedBase.includes('192.168.') || savedBase.includes('localhost') || savedBase.includes('127.0.0.1')) && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        localStorage.removeItem('sdfin_api_base_url');
      }
    } catch (_) {}
    // Default to same-origin relative path; can be customized via settings in localStorage if needed
    this.baseUrl = localStorage.getItem('sdfin_api_base_url') || '/api/mobile';
  }

  setBaseUrl(url) {
    this.baseUrl = url.replace(/\/$/, '');
    localStorage.setItem('sdfin_api_base_url', this.baseUrl);
  }

  async getDeviceId() {
    let id = localStorage.getItem('sdfin_device_id');
    if (!id) {
      id = 'pwa_ios_' + Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
      localStorage.setItem('sdfin_device_id', id);
    }
    return id;
  }

  async _headers(isJson = true) {
    const token = await window.dbService.getSession('token');
    const headers = {};
    if (isJson) headers['Content-Type'] = 'application/json';
    if (token) headers['X-Mobile-Token'] = token;
    return headers;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
    const defaultHeaders = await this._headers(options.body instanceof FormData ? false : true);

    const mergedOptions = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers || {})
      }
    };

    try {
      const response = await fetch(url, mergedOptions);
      
      let data = null;
      try {
        data = await response.json();
      } catch (jsonErr) {
        // Body was empty or non-JSON
      }

      if (!response.ok) {
        const errorMsg = (data && data.error) ? data.error : `HTTP ${response.status}: ${response.statusText}`;
        const err = new Error(errorMsg);
        err.status = response.status;
        err.data = data;
        throw err;
      }

      if (!data) {
        throw new Error('Server returned an empty or invalid response');
      }

      return data;
    } catch (err) {
      if (!window.navigator.onLine || err.message.includes('Failed to fetch') || err.status === 503) {
        const offlineErr = new Error('Network unavailable. Action will be queued offline.');
        offlineErr.isOffline = true;
        throw offlineErr;
      }
      throw err;
    }
  }

  async ping() {
    return this.request('/ping');
  }

  async login(username, password) {
    const deviceId = await this.getDeviceId();
    const payload = {
      username: username.trim(),
      password: password,
      device_id: deviceId,
      device_model: navigator.userAgent
    };

    const res = await this.request('/login', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (!res || !res.token) {
      const errMsg = (res && res.error) ? res.error : 'Login failed: Invalid server credentials';
      throw new Error(errMsg);
    }

    const employeeName = res.employee_name || res.username || username;
    const role = res.role || res.level || 'employee';

    await window.dbService.setSession('token', res.token);
    await window.dbService.setSession('eid', res.eid);
    await window.dbService.setSession('username', res.username || username);
    await window.dbService.setSession('employee_name', employeeName);
    await window.dbService.setSession('role', role);
    await window.dbService.setSession('login_time', new Date().toISOString());

    return {
      ...res,
      employee_name: employeeName,
      role: role
    };
  }

  async logout() {
    await window.dbService.clearSession();
  }

  async getVillages() {
    const data = await this.request('/villages');
    const villages = Array.isArray(data) ? data : (data.villages || []);
    if (villages.length > 0) {
      await window.dbService.saveVillages(villages);
    }
    return villages;
  }

  async getCustomers(vid) {
    const data = await this.request(`/customers?vid=${vid}`);
    const customers = Array.isArray(data) ? data : (data.customers || []);
    if (customers.length > 0) {
      await window.dbService.saveCustomers(vid, customers);
    }
    return customers;
  }

  async getPayments(vid) {
    const data = await this.request(`/payments?vid=${vid}`);
    const payments = Array.isArray(data) ? data : (data.payments || []);
    if (payments.length > 0) {
      await window.dbService.savePayments(vid, payments);
    }
    return payments;
  }

  async getClosedCustomers(vid) {
    const data = await this.request(`/closed_customers?vid=${vid}`);
    const closed = Array.isArray(data) ? data : (data.customers || data.closed_customers || []);
    if (closed.length > 0 && window.dbService) {
      await window.dbService.saveClosedCustomers(vid, closed);
    }
    return closed;
  }

  async getParentCustomerInfo(vid, pano) {
    return this.request(`/parent_customer_info?vid=${vid}&pano=${pano}`);
  }

  async closeAccountFeed(payload) {
    return this.request('/close_account_feed', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async getCashbag() {
    return this.request('/cashbag');
  }

  async getSubmissionsStatus() {
    return this.request('/submissions/status');
  }

  async postPaymentBatch(batchPayload) {
    return this.request('/payment_feed_batch', {
      method: 'POST',
      body: JSON.stringify(batchPayload)
    });
  }

  async postCustomer(customerPayload) {
    return this.request('/customer_feed', {
      method: 'POST',
      body: JSON.stringify(customerPayload)
    });
  }

  async updateCustomerDocs(formData) {
    return this.request('/customer_docs_update', {
      method: 'POST',
      body: formData
    });
  }
}

window.apiClient = new ApiClient();
