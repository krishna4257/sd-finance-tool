/*
 * Utility helpers for the SD Finance frontend.
 *
 * This module defines a collection of functions that are shared
 * across multiple pages. Keeping these definitions in one place
 * eliminates duplication and promotes consistent behaviour throughout
 * the application. Functions are attached to the global scope so
 * existing scripts can call them without imports. A more modern
 * bundling setup (e.g. ES modules) would allow explicit imports but
 * falls outside the scope of this project.
 */

// -------------------- Date Helpers --------------------

/**
 * Parses any date string (ISO yyyy-mm-dd or dd/mm/yyyy or dd-mm-yyyy)
 * or Date object and returns a Date instance, or null if invalid.
 */
function parseDDMMYYYY(dateString) {
  if (!dateString) return null;
  if (dateString instanceof Date) return isNaN(dateString.getTime()) ? null : dateString;
  const str = String(dateString).trim();
  if (!str) return null;

  // 1. Match YYYY-MM-DD
  const matchIso = str.match(/^(\d{4})[-/](\d{2})[-/](\d{2})/);
  if (matchIso) {
    return new Date(parseInt(matchIso[1], 10), parseInt(matchIso[2], 10) - 1, parseInt(matchIso[3], 10));
  }

  // 2. Match DD-MM-YYYY or DD/MM/YYYY
  const matchDd = str.match(/^(\d{2})[-/](\d{2})[-/](\d{4})/);
  if (matchDd) {
    return new Date(parseInt(matchDd[3], 10), parseInt(matchDd[2], 10) - 1, parseInt(matchDd[1], 10));
  }

  // 3. Fallback split
  const parts = str.split(/[-/]/);
  if (parts.length === 3) {
    if (parts[0].length === 4) {
      return new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    } else {
      return new Date(parseInt(parts[2], 10), parseInt(parts[1], 10) - 1, parseInt(parts[0], 10));
    }
  }

  const d = new Date(str);
  return isNaN(d.getTime()) ? null : d;
}

/**
 * Format any date value into the dd-mm-yyyy format.
 */
function formatDate(value) {
  if (value === null || value === undefined) return "";
  
  if (value instanceof Date) {
    if (isNaN(value.getTime())) return "";
    const d = String(value.getDate()).padStart(2, '0');
    const m = String(value.getMonth() + 1).padStart(2, '0');
    const y = value.getFullYear();
    return `${d}-${m}-${y}`;
  }

  const str = String(value).trim();
  if (!str) return "";

  // 1. Match YYYY-MM-DD
  const matchIso = str.match(/^(\d{4})[-/](\d{2})[-/](\d{2})(?:\s|T|$)/);
  if (matchIso) {
    const [, year, month, day] = matchIso;
    return `${day}-${month}-${year}`;
  }

  // 2. Match DD-MM-YYYY or DD/MM/YYYY
  const matchDdmmyyyy = str.match(/^(\d{2})[-/](\d{2})[-/](\d{4})(?:\s|T|$)/);
  if (matchDdmmyyyy) {
    const [, day, month, year] = matchDdmmyyyy;
    return `${day}-${month}-${year}`;
  }

  // Fallback try to parse
  const parsed = parseDDMMYYYY(str);
  if (parsed) {
    const d = String(parsed.getDate()).padStart(2, '0');
    const m = String(parsed.getMonth() + 1).padStart(2, '0');
    const y = parsed.getFullYear();
    return `${d}-${m}-${y}`;
  }

  return str;
}

function formatDateToDDMMYYYY(date) {
  return formatDate(date);
}

function formatDateToISO(str) {
  if (!str) return "";
  const parts = String(str).trim().split(/[-/]/);
  if (parts.length === 3) {
    if (parts[2].length === 4) {
      return `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`;
    }
    if (parts[0].length === 4) {
      return `${parts[0]}-${parts[1].padStart(2, '0')}-${parts[2].padStart(2, '0')}`;
    }
  }
  return str;
}

// Expose helpers globally so existing inline scripts can access them
window.parseDDMMYYYY = parseDDMMYYYY;
window.formatDate = formatDate;
window.formatDateToDDMMYYYY = formatDateToDDMMYYYY;
window.formatDateToISO = formatDateToISO;

// -------------------- Currency Helpers --------------------

/**
 * Format a numeric amount as Indian currency without decimals.
 *
 * @param {number|string} amount The amount to format. Strings are
 *     coerced into numbers. Invalid numbers return an empty string.
 * @returns {string} The formatted string prefixed with ₹.
 */
function formatWithRupeeAndCommas(amount) {
  const number = Math.round(parseFloat(amount));
  if (Number.isNaN(number)) return '';
  return `₹${number.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

/**
 * Apply currency formatting to elements annotated with the data-money
 * attribute. The element's text content is converted to a number,
 * stored back on the data-money attribute, and replaced with a
 * formatted string. If an element is being edited (data-editing=1)
 * it will be skipped.
 */
function applyGlobalMoneyFormatting() {
  const moneyFields = document.querySelectorAll('[data-money]');
  moneyFields.forEach(el => {
    if (el.dataset.editing === '1') return;
    let val = el.textContent.trim().replace(/[^\d.-]/g, '');
    if (val !== '') {
      const numeric = parseFloat(val);
      el.setAttribute('data-money', String(numeric));
      el.textContent = formatWithRupeeAndCommas(numeric);
    }
  });
}

// Expose formatting helpers globally
window.formatDate = formatDate;
window.formatDateToDDMMYYYY = formatDateToDDMMYYYY;
window.formatDDMMYYYY = formatDate;
window.formatDateIN = formatDate;
window.parseDDMMYYYY = parseDDMMYYYY;
window.formatDateToISO = formatDateToISO;
window.formatWithRupeeAndCommas = formatWithRupeeAndCommas;
window.applyGlobalMoneyFormatting = applyGlobalMoneyFormatting;

/**
 * Apply Indian date formatting (dd-mm-yyyy) to elements annotated with
 * data-date, .date-cell, .date-display, or plain text nodes/cells matching
 * ISO date pattern (yyyy-mm-dd).
 * Skips interactive inputs (e.g. <input type="date">) to preserve native UI pickers.
 */
function applyGlobalDateFormatting(root = document) {
  if (!root || !root.querySelectorAll) return;

  // 1. Explicit data-date elements
  const dateElements = root.querySelectorAll('[data-date]');
  dateElements.forEach(el => {
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') return;
    const raw = el.getAttribute('data-date');
    if (raw) {
      el.textContent = formatDate(raw);
    }
  });

  // 2. Elements with date classes
  const dateClasses = root.querySelectorAll('.date-cell, .date-display, [data-format-date]');
  dateClasses.forEach(el => {
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') return;
    const txt = el.textContent.trim();
    if (txt) {
      el.textContent = formatDate(txt);
    }
  });

  // 3. Automatically format table cells containing purely an ISO date YYYY-MM-DD
  const isoDateRegex = /^\s*(\d{4})[-/](\d{2})[-/](\d{2})\s*$/;
  const cells = root.querySelectorAll('td, .date-auto');
  cells.forEach(el => {
    if (el.children.length === 0) {
      const match = el.textContent.match(isoDateRegex);
      if (match) {
        el.textContent = `${match[3]}-${match[2]}-${match[1]}`;
      }
    }
  });
}

window.applyGlobalDateFormatting = applyGlobalDateFormatting;

// -------------------- DataTables Extensions --------------------

// Extend DataTables with a custom sort type for dd/mm/yyyy. This
// definition must occur before any DataTable initialisation. If
// DataTables is not present, it safely does nothing.
if (typeof $ !== 'undefined' && $.fn && $.fn.dataTable) {
  $.fn.dataTable.ext.type.order['date-ddmmyyyy-pre'] = function (d) {
    if (!d || typeof d !== 'string') return 0;
    const parts = d.split(/[-/]/);
    if (parts.length < 3) return 0;
    return parseInt(parts[2] + parts[1] + parts[0], 10);
  };

  // Global Interceptor to customize column sortability and styles
  const originalDataTable = $.fn.DataTable;
  $.fn.DataTable = function(options) {
      if (typeof options === 'string' || originalDataTable.isDataTable(this)) {
          return originalDataTable.apply(this, arguments);
      }
      options = $.extend(true, {}, options || {});
      options.searching = true;
      const columnDefs = options.columnDefs || [];
      
      this.find("thead th").each((index, th) => {
          const text = $(th).text().trim().toUpperCase();
          const hasHtml = $(th).html().includes("<input") || $(th).html().includes("<button");
          
          const isUnsortable = (
              text === "" || 
              hasHtml ||
              text === "EDIT" || 
              text === "DELETE" || 
              text === "ACTION" || 
              text === "ACTIONS" || 
              text === "CUMULATIVE AMOUNT" || 
              text === "CUMULATIVE" || 
              text === "EDIT/DELETE"
          );
          
          const isDateColumn = (
              text.includes("DATE") || 
              text.includes("DT") || 
              text.includes("PDT") || 
              text.includes("DUE")
          );
          
          if (isUnsortable) {
              columnDefs.push({ targets: index, orderable: false });
          } else {
              $(th).addClass("sortable-header");
              const def = { targets: index, orderSequence: ['asc', 'desc'] };
              if (isDateColumn) {
                  def.type = 'date-ddmmyyyy';
              }
              columnDefs.push(def);
          }
      });
      options.columnDefs = columnDefs;
      if (options.ordering === undefined) options.ordering = true;
      return originalDataTable.call(this, options);
  };
  // Copy all static properties of original constructor
  for (let key in originalDataTable) {
      if (originalDataTable.hasOwnProperty(key)) {
          $.fn.DataTable[key] = originalDataTable[key];
      }
  }
  $.fn.DataTable.isDataTable = originalDataTable.isDataTable;
  $.fn.DataTable.ext = originalDataTable.ext;
  $.fn.DataTable.settings = originalDataTable.settings;
  $.fn.DataTable.models = originalDataTable.models;
  $.fn.DataTable.Api = originalDataTable.Api;

  const originaldataTable = $.fn.dataTable;
  $.fn.dataTable = function(options) {
      if (typeof options === 'string' || originaldataTable.isDataTable(this)) {
          return originaldataTable.apply(this, arguments);
      }
      options = $.extend(true, {}, options || {});
      options.searching = true;
      const columnDefs = options.columnDefs || [];
      this.find("thead th").each((index, th) => {
          const text = $(th).text().trim().toUpperCase();
          const hasHtml = $(th).html().includes("<input") || $(th).html().includes("<button");
          
          const isUnsortable = (
              text === "" || 
              hasHtml ||
              text === "EDIT" || 
              text === "DELETE" || 
              text === "ACTION" || 
              text === "ACTIONS" || 
              text === "CUMULATIVE AMOUNT" || 
              text === "CUMULATIVE" || 
              text === "EDIT/DELETE"
          );
          
          const isDateColumn = (
              text.includes("DATE") || 
              text.includes("DT") || 
              text.includes("PDT") || 
              text.includes("DUE")
          );

          if (isUnsortable) {
              columnDefs.push({ targets: index, orderable: false });
          } else {
              $(th).addClass("sortable-header");
              const def = { targets: index, orderSequence: ['asc', 'desc'] };
              if (isDateColumn) {
                  def.type = 'date-ddmmyyyy';
              }
              columnDefs.push(def);
          }
      });
      options.columnDefs = columnDefs;
      if (options.ordering === undefined) options.ordering = true;
      return originaldataTable.call(this, options);
  };
  // Copy all static properties of original jQuery plugin method
  for (let key in originaldataTable) {
      if (originaldataTable.hasOwnProperty(key)) {
          $.fn.dataTable[key] = originaldataTable[key];
      }
  }
  $.fn.dataTable.isDataTable = originaldataTable.isDataTable;
  $.fn.dataTable.ext = originaldataTable.ext;
  $.fn.dataTable.settings = originaldataTable.settings;
  $.fn.dataTable.models = originaldataTable.models;
  $.fn.dataTable.Api = originaldataTable.Api;
}

// Automatically apply money formatting once the DOM is ready. This
// ensures any server rendered values are displayed consistently. If
// other scripts need to defer formatting (e.g. during edits) they
// should call applyGlobalMoneyFormatting manually.
document.addEventListener('DOMContentLoaded', () => {
  applyGlobalMoneyFormatting();
  applyGlobalDateFormatting();
});

// -------------------- Modernized Success Animations & Sounds --------------------

let sharedAudioCtx = null;

function getSharedAudioContext() {
  if (!sharedAudioCtx) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) {
      sharedAudioCtx = new AudioContext();
    }
  }
  return sharedAudioCtx;
}

// Automatically unlock the AudioContext on any early user gesture
function unlockAudio() {
  const ctx = getSharedAudioContext();
  if (ctx && ctx.state === 'suspended') {
    ctx.resume().then(() => {
      window.removeEventListener('click', unlockAudio);
      window.removeEventListener('keydown', unlockAudio);
    });
  }
}
window.addEventListener('click', unlockAudio);
window.addEventListener('keydown', unlockAudio);

/**
 * Synthesizes a bright, high-quality double-tone chime sound (payment success style)
 * using Web Audio API. Requires no external audio file assets.
 */
function playSuccessSound() {
  try {
    const ctx = getSharedAudioContext();
    if (!ctx) return;
    
    if (ctx.state === 'suspended') {
      ctx.resume();
    }
    
    // Tone 1: E5 (659.25 Hz)
    const osc1 = ctx.createOscillator();
    const osc1Gain = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(659.25, ctx.currentTime);
    osc1Gain.gain.setValueAtTime(0.12, ctx.currentTime);
    osc1Gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
    osc1.connect(osc1Gain);
    osc1Gain.connect(ctx.destination);
    
    // Tone 2: B5 (987.77 Hz) - delayed slightly for chime effect
    const osc2 = ctx.createOscillator();
    const osc2Gain = ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(987.77, ctx.currentTime + 0.08);
    osc2Gain.gain.setValueAtTime(0, ctx.currentTime);
    osc2Gain.gain.setValueAtTime(0.12, ctx.currentTime + 0.08);
    osc2Gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.45);
    osc2.connect(osc2Gain);
    osc2Gain.connect(ctx.destination);
    
    osc1.start(ctx.currentTime);
    osc1.stop(ctx.currentTime + 0.4);
    
    osc2.start(ctx.currentTime + 0.08);
    osc2.stop(ctx.currentTime + 0.5);
  } catch (e) {
    console.warn("Could not play success chime sound:", e);
  }
}

/**
 * Triggers a PhonePe-style modernized success animation:
 * 1. Flashes the background of the sectionElement green.
 * 2. Overlays a tick mark and success message.
 * 3. Plays a synthesized success sound.
 * 4. Highlights specified elements for 5 seconds.
 *
 * @param {Object} options Configuration options:
 * @param {HTMLElement} options.sectionElement The card/column container that receives the flash and overlay.
 * @param {Array<HTMLElement>} options.highlightElements List of elements to highlight for 5 seconds.
 * @param {string} options.message Text message to show under the success checkmark.
 * @param {number} options.highlightDuration Duration of the input highlight in ms (default 5000).
 * @param {Function} options.onComplete Callback executed after the success overlay fades out.
 */
function triggerSuccessFeedback({
  sectionElement,
  highlightElements = [],
  message = "Change successful",
  highlightDuration = 5000,
  onComplete = null
}) {
  if (!sectionElement) return;

  // 1. Play audio chime
  playSuccessSound();

  // 2. Trigger the green background flash animation
  sectionElement.classList.remove("success-flash-active");
  // Force reflow to restart animation if it was run recently
  void sectionElement.offsetWidth; 
  sectionElement.classList.add("success-flash-active");
  setTimeout(() => {
    sectionElement.classList.remove("success-flash-active");
  }, 1500);

  // 3. Create and show the PhonePe-like checkmark overlay
  let overlay = sectionElement.querySelector(".success-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.className = "success-overlay";
    overlay.innerHTML = `
      <div class="success-checkmark-wrapper">
        <svg class="success-checkmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
          <circle class="success-checkmark-circle" cx="26" cy="26" r="25" fill="none"/>
          <path class="success-checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>
        </svg>
        <div class="success-message"></div>
      </div>
    `;
    sectionElement.appendChild(overlay);
  }

  overlay.querySelector(".success-message").textContent = message;
  
  // Center overlay dynamically relative to the visible scrolled viewport
  overlay.style.top = (sectionElement.scrollTop || 0) + "px";
  overlay.style.height = (sectionElement.clientHeight || sectionElement.offsetHeight || 0) + "px";

  // Activate overlay
  overlay.classList.add("active");

  // Fade out overlay after 1.5 seconds
  setTimeout(() => {
    overlay.classList.remove("active");
    if (onComplete) onComplete();
  }, 1600);

  // 4. Highlight modified fields/rows for 5 seconds
  highlightElements.forEach(el => {
    if (!el) return;
    el.classList.add("field-highlight");
  });

  setTimeout(() => {
    highlightElements.forEach(el => {
      if (!el) return;
      el.classList.remove("field-highlight");
    });
  }, highlightDuration);
}

// Expose animation helpers globally
window.getSharedAudioContext = getSharedAudioContext;
window.playSuccessSound = playSuccessSound;
window.triggerSuccessFeedback = triggerSuccessFeedback;

/**
 * Safely escapes HTML entities to prevent Cross-Site Scripting (XSS).
 */
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
    .replace(/`/g, '&#96;');
}

window.escapeHtml = escapeHtml;

// -------------------- UUID & Token Utilities --------------------

/**
 * Generate a standard RFC4122 v4 UUID.
 */
function generateUUID() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}
window.generateUUID = generateUUID;

/**
 * Uniformly locate CSRF token from meta tags, hidden inputs, or cookies.
 */
function getCSRFToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta && meta.getAttribute('content')) {
    return meta.getAttribute('content');
  }
  const input = document.querySelector('input[name="csrf_token"]');
  if (input && input.value) {
    return input.value;
  }
  const cookies = document.cookie ? document.cookie.split(';') : [];
  for (let i = 0; i < cookies.length; i++) {
    const c = cookies[i].trim();
    if (c.startsWith('csrf_token=') || c.startsWith('XSRF-TOKEN=')) {
      return decodeURIComponent(c.substring(c.indexOf('=') + 1));
    }
  }
  return '';
}
window.getCSRFToken = getCSRFToken;

// -------------------- Modernized Toast Notification System --------------------

/**
 * Show a sleek, accessible, non-blocking toast notification.
 *
 * @param {string} message Message text to display.
 * @param {'success'|'error'|'warning'|'info'} type Notification severity.
 * @param {number} duration Display duration in milliseconds (default 4000).
 */
function showToast(message, type = 'info', duration = 4000) {
  if (!message) return null;
  let container = document.getElementById('sd-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'sd-toast-container';
    container.className = 'sd-toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `sd-toast sd-toast-${type}`;

  const icons = {
    success: '<i class="fas fa-check-circle"></i>',
    error: '<i class="fas fa-exclamation-circle"></i>',
    warning: '<i class="fas fa-exclamation-triangle"></i>',
    info: '<i class="fas fa-info-circle"></i>'
  };
  const iconHtml = icons[type] || icons.info;

  toast.innerHTML = `
    <span class="sd-toast-icon">${iconHtml}</span>
    <span class="sd-toast-text">${escapeHtml(message)}</span>
    <button class="sd-toast-close" type="button" aria-label="Close">&times;</button>
  `;

  const closeBtn = toast.querySelector('.sd-toast-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      toast.classList.remove('sd-toast-show');
      setTimeout(() => toast.remove(), 250);
    });
  }

  container.appendChild(toast);
  requestAnimationFrame(() => {
    toast.classList.add('sd-toast-show');
  });

  if (duration > 0) {
    setTimeout(() => {
      if (toast.parentElement) {
        toast.classList.remove('sd-toast-show');
        setTimeout(() => toast.remove(), 250);
      }
    }, duration);
  }
  return toast;
}

window.showToast = showToast;
window.showSuccessToast = (msg, d) => showToast(msg, 'success', d || 3500);
window.showErrorToast = (msg, d) => showToast(msg, 'error', d || 6000);
window.showWarningToast = (msg, d) => showToast(msg, 'warning', d || 4500);
window.showInfoToast = (msg, d) => showToast(msg, 'info', d || 3500);

// -------------------- Transparent Network & Fetch Wrapper --------------------

(function() {
  if (window.__SD_FETCH_INITIALIZED__) return;
  window.__SD_FETCH_INITIALIZED__ = true;

  const originalFetch = window.fetch;

  async function secureFetch(resource, init = {}) {
    init = init || {};
    const method = (init.method || 'GET').toUpperCase();
    const isMutating = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method);

    // 1. Auto-inject CSRF token for mutating requests
    if (isMutating) {
      const token = window.getCSRFToken();
      if (token) {
        if (init.headers instanceof Headers) {
          if (!init.headers.has('X-CSRFToken') && !init.headers.has('X-CSRF-Token')) {
            init.headers.append('X-CSRFToken', token);
          }
        } else if (Array.isArray(init.headers)) {
          const has = init.headers.some(([k]) => k.toLowerCase() === 'x-csrftoken' || k.toLowerCase() === 'x-csrf-token');
          if (!has) {
            init.headers.push(['X-CSRFToken', token]);
          }
        } else {
          init.headers = init.headers || {};
          if (!init.headers['X-CSRFToken'] && !init.headers['X-CSRF-Token']) {
            init.headers['X-CSRFToken'] = token;
          }
        }
      }

      // 2. Attach Client Request Id (Idempotency) if not provided
      const reqId = window.generateUUID();
      if (init.headers instanceof Headers) {
        if (!init.headers.has('X-Client-Request-Id')) {
          init.headers.append('X-Client-Request-Id', reqId);
        }
      } else if (Array.isArray(init.headers)) {
        if (!init.headers.some(([k]) => k.toLowerCase() === 'x-client-request-id')) {
          init.headers.push(['X-Client-Request-Id', reqId]);
        }
      } else {
        init.headers = init.headers || {};
        if (!init.headers['X-Client-Request-Id']) {
          init.headers['X-Client-Request-Id'] = reqId;
        }
      }
    }

    let response;
    try {
      response = await originalFetch.call(window, resource, init);
    } catch (err) {
      console.warn('[Network Error] fetch failed:', err);
      throw err;
    }

    // 3. Intercept 401 Session Expiration
    if (response.status === 401) {
      const isLoginPage = window.location.pathname.startsWith('/login') ||
                          window.location.pathname.startsWith('/banking/login');
      if (!isLoginPage && !window.__SD_SESSION_EXPIRED_NOTIFIED__) {
        window.__SD_SESSION_EXPIRED_NOTIFIED__ = true;
        window.showToast('Your session has expired. Redirecting to login...', 'warning', 3000);
        setTimeout(() => {
          const current = encodeURIComponent(window.location.pathname + window.location.search);
          window.location.href = `/login?next=${current}`;
        }, 1500);
      }
    }

    return response;
  }

  window.fetch = secureFetch;
  window.csrfFetch = secureFetch;

  /**
   * Resilient fetch with exponential backoff for flaky cellular connections.
   */
  async function fetchWithRetry(resource, init = {}, options = {}) {
    const maxRetries = options.maxRetries || 3;
    let delayMs = options.baseDelayMs || 800;
    const retryAll = options.retryAll || false;
    const method = (init.method || 'GET').toUpperCase();
    const isIdempotent = ['GET', 'HEAD', 'OPTIONS'].includes(method) || retryAll;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        const response = await window.fetch(resource, init);
        if (isIdempotent && [502, 503, 504].includes(response.status) && attempt < maxRetries) {
          await new Promise(r => setTimeout(r, delayMs));
          delayMs *= 1.5;
          continue;
        }
        return response;
      } catch (err) {
        if (isIdempotent && attempt < maxRetries) {
          await new Promise(r => setTimeout(r, delayMs));
          delayMs *= 1.5;
          continue;
        }
        throw err;
      }
    }
  }

  window.fetchWithRetry = fetchWithRetry;
})();