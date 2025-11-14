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
}

// Automatically apply money formatting once the DOM is ready. This
// ensures any server rendered values are displayed consistently. If
// other scripts need to defer formatting (e.g. during edits) they
// should call applyGlobalMoneyFormatting manually.
document.addEventListener('DOMContentLoaded', () => {
  applyGlobalMoneyFormatting();
});