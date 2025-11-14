/**
 * Parses a date string in "dd/mm/yyyy" format into a JavaScript Date object.
 * @param {string} dateString - The date string to parse.
 * @returns {Date|null} A Date object or null if the format is invalid.
 */
function parseDDMMYYYY(dateString) {
  if (!dateString || typeof dateString !== 'string') return null;
  const parts = dateString.split('/');
  if (parts.length === 3) {
    const day = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1; // Month is 0-indexed
    const year = parseInt(parts[2], 10);
    if (!isNaN(day) && !isNaN(month) && !isNaN(year)) {
      return new Date(year, month, day);
    }
  }
  return null;
}

/**
 * Formats a JavaScript Date object into a "dd/mm/yyyy" string.
 * @param {Date} date - The Date object to format.
 * @returns {string} The formatted date string.
 */
function formatDateToDDMMYYYY(date) {
  if (!(date instanceof Date) || isNaN(date)) return '';
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0'); // Month is 0-indexed
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
}