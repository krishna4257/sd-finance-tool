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
 * Parse a string in dd/mm/yyyy format into a Date object.
 * Returns null if the input cannot be parsed.
 *
 * @param {string} dateString The date string to parse.
 * @returns {Date|null} A Date instance or null on failure.
 */
function parseDDMMYYYY(dateString) {
  if (!dateString || typeof dateString !== 'string') return null;
  const parts = dateString.split('/');
  if (parts.length !== 3) return null;
  const day = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10) - 1; // JavaScript months are zero-indexed
  const year = parseInt(parts[2], 10);
  if (Number.isNaN(day) || Number.isNaN(month) || Number.isNaN(year)) {
    return null;
  }
  return new Date(year, month, day);
}

/**
 * Format a Date object into a dd/mm/yyyy string.
 * Returns an empty string for invalid or null dates.
 *
 * @param {Date} date The date to format.
 * @returns {string} A dd/mm/yyyy representation of the date.
 */
function formatDateToDDMMYYYY(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
}

// Expose helpers globally so existing inline scripts can access them
window.parseDDMMYYYY = parseDDMMYYYY;
window.formatDateToDDMMYYYY = formatDateToDDMMYYYY;

// -------------------- Currency Helpers --------------------

/**
 * Format a numeric amount as Indian currency without decimals.
 *
 * @param {number|string} amount The amount to format. Strings are
 *     coerced into numbers. Invalid numbers return an empty string.
 * @returns {string} The formatted string prefixed with ₹.
 */
function formatWithRupeeAndCommas(amount) {
  const number = parseFloat(amount);
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
window.formatWithRupeeAndCommas = formatWithRupeeAndCommas;
window.applyGlobalMoneyFormatting = applyGlobalMoneyFormatting;

// -------------------- DataTables Extensions --------------------

// Extend DataTables with a custom sort type for dd/mm/yyyy. This
// definition must occur before any DataTable initialisation. If
// DataTables is not present, it safely does nothing.
if (typeof $ !== 'undefined' && $.fn && $.fn.dataTable) {
  $.fn.dataTable.ext.type.order['date-ddmmyyyy-pre'] = function (d) {
    if (!d || typeof d !== 'string') return 0;
    const parts = d.split('/');
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
          
          if (isUnsortable) {
              columnDefs.push({ targets: index, orderable: false });
          } else {
              $(th).addClass("sortable-header");
              columnDefs.push({ targets: index, orderSequence: ['asc', 'desc'] });
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
      const columnDefs = options.columnDefs || [];
      this.find("thead th").each((index, th) => {
          const text = $(th).text().trim().toUpperCase();
          const hasHtml = $(th).html().includes("<input") || $(th).html().includes("<button");
          if (
              text === "" || 
              hasHtml ||
              text === "EDIT" || 
              text === "DELETE" || 
              text === "ACTION" || 
              text === "ACTIONS" || 
              text === "CUMULATIVE AMOUNT" || 
              text === "CUMULATIVE" || 
              text === "EDIT/DELETE"
          ) {
              columnDefs.push({ targets: index, orderable: false });
          } else {
              $(th).addClass("sortable-header");
              columnDefs.push({ targets: index, orderSequence: ['asc', 'desc'] });
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
});

// -------------------- Modernized Success Animations & Sounds --------------------

/**
 * Synthesizes a bright, high-quality double-tone chime sound (payment success style)
 * using Web Audio API. Requires no external audio file assets.
 */
function playSuccessSound() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    
    // Tone 1: E5 (659.25 Hz)
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(659.25, ctx.currentTime);
    gain1.gain.setValueAtTime(0.12, ctx.currentTime);
    gain1.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
    osc1.connect(gain1);
    gain1.connect(ctx.destination);
    
    // Tone 2: B5 (987.77 Hz) - delayed slightly for chime effect
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(987.77, ctx.currentTime + 0.08);
    gain2.gain.setValueAtTime(0, ctx.currentTime);
    gain2.gain.setValueAtTime(0.12, ctx.currentTime + 0.08);
    gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.45);
    osc2.connect(gain2);
    gain2.connect(ctx.destination);
    
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
window.playSuccessSound = playSuccessSound;
window.triggerSuccessFeedback = triggerSuccessFeedback;