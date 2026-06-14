document.addEventListener('DOMContentLoaded', () => {
  const calendar = document.getElementById('customCalendar');
  if (!calendar) return;

  const monthDisplay = document.getElementById('monthDisplay');
  const calendarGrid = document.getElementById('calendarGrid');
  const prevMonthBtn = document.getElementById('prevMonth');
  const nextMonthBtn = document.getElementById('nextMonth');

  let currentMonth = new Date().getMonth();
  let currentYear = new Date().getFullYear();
  let activeInputElement = null;
  let currentSelectedDate = null;
  let rangeStart = null;
  let rangeEnd = null;

  function getSeparator(input) {
    return '-';
  }

  function formatDate(date, input) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
    const separator = getSeparator(input);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}${separator}${month}${separator}${year}`;
  }

  function parseDate(dateString, input) {
    if (!dateString) return null;
    const cleanStr = String(dateString).trim();
    if (!cleanStr) return null;
    
    // 1. Match ISO yyyy-mm-dd
    const matchIso = cleanStr.match(/^(\d{4})[-/](\d{2})[-/](\d{2})/);
    if (matchIso) {
      return new Date(parseInt(matchIso[1], 10), parseInt(matchIso[2], 10) - 1, parseInt(matchIso[3], 10));
    }
    
    // 2. Match dd-mm-yyyy or dd/mm/yyyy
    const matchDd = cleanStr.match(/^(\d{2})[-/](\d{2})[-/](\d{4})/);
    if (matchDd) {
      return new Date(parseInt(matchDd[3], 10), parseInt(matchDd[2], 10) - 1, parseInt(matchDd[1], 10));
    }
    
    // 3. Fallback split
    const parts = cleanStr.split(/[-/]/);
    if (parts.length === 3) {
      if (parts[0].length === 4) {
        return new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
      } else {
        return new Date(parseInt(parts[2], 10), parseInt(parts[1], 10) - 1, parseInt(parts[0], 10));
      }
    }
    
    const d = new Date(cleanStr);
    return isNaN(d.getTime()) ? null : d;
  }

  function renderCalendar(month, year) {
    calendarGrid.innerHTML = '';
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

    monthDisplay.textContent = `${monthNames[month]} ${year}`;

    // Render day names
    dayNames.forEach(day => {
      const dayNameEl = document.createElement('div');
      dayNameEl.classList.add('calendar-day-name');
      dayNameEl.textContent = day;
      calendarGrid.appendChild(dayNameEl);
    });

    // Add blank spaces for days before the 1st
    for (let i = 0; i < firstDay; i++) {
      calendarGrid.appendChild(document.createElement('div'));
    }

    // Render days of the month
    for (let i = 1; i <= daysInMonth; i++) {
      const dayEl = document.createElement('div');
      dayEl.classList.add('day-cell');
      dayEl.textContent = i;

      const date = new Date(year, month, i);
      const today = new Date();
      if (i === today.getDate() && month === today.getMonth() && year === today.getFullYear()) {
        dayEl.classList.add('today');
      }

      const options = activeInputElement ? (activeInputElement.customCalendarOptions || {}) : {};

      if (options.mode === 'range') {
        if (rangeStart && date.toDateString() === rangeStart.toDateString()) {
          dayEl.classList.add('selected', 'range-start');
        } else if (rangeEnd && date.toDateString() === rangeEnd.toDateString()) {
          dayEl.classList.add('selected', 'range-end');
        } else if (rangeStart && rangeEnd && date > rangeStart && date < rangeEnd) {
          dayEl.classList.add('in-range');
        }
      } else {
        if (currentSelectedDate && date.toDateString() === currentSelectedDate.toDateString()) {
          dayEl.classList.add('selected');
        }
      }

      // Add hover interaction for range selection
      if (options.mode === 'range') {
        dayEl.addEventListener('mouseenter', () => {
          if (rangeStart && !rangeEnd) {
            const cells = calendarGrid.querySelectorAll('.day-cell');
            cells.forEach(cell => {
              const cellDay = parseInt(cell.textContent, 10);
              if (isNaN(cellDay)) return;
              const cellDate = new Date(year, month, cellDay);
              if (cellDate > rangeStart && cellDate <= date) {
                cell.classList.add('in-range');
              } else if (cellDate.toDateString() !== rangeStart.toDateString()) {
                cell.classList.remove('in-range');
              }
            });
          }
        });
      }

      dayEl.addEventListener('click', () => {
        if (activeInputElement) {
          const selectedDate = new Date(year, month, i);
          
          if (options.mode === 'range') {
            if (!rangeStart || (rangeStart && rangeEnd)) {
              rangeStart = selectedDate;
              rangeEnd = null;
              activeInputElement.value = formatDate(rangeStart, activeInputElement);
              activeInputElement.dispatchEvent(new Event('input', { bubbles: true }));
              activeInputElement.dispatchEvent(new Event('change', { bubbles: true }));
              renderCalendar(month, year);
            } else {
              // Clicked end date
              if (selectedDate < rangeStart) {
                // If end date is before start date, make it the new start date
                rangeStart = selectedDate;
                rangeEnd = null;
                activeInputElement.value = formatDate(rangeStart, activeInputElement);
                activeInputElement.dispatchEvent(new Event('input', { bubbles: true }));
                activeInputElement.dispatchEvent(new Event('change', { bubbles: true }));
                renderCalendar(month, year);
              } else {
                rangeEnd = selectedDate;
                activeInputElement.value = `${formatDate(rangeStart, activeInputElement)} to ${formatDate(rangeEnd, activeInputElement)}`;
                activeInputElement.dispatchEvent(new Event('input', { bubbles: true }));
                activeInputElement.dispatchEvent(new Event('change', { bubbles: true }));
                
                calendar.style.display = 'none';
                activeInputElement = null;
                if (options.onClose) {
                  options.onClose();
                }
              }
            }
          } else {
            // Single mode
            activeInputElement.value = formatDate(selectedDate, activeInputElement);
            activeInputElement.dispatchEvent(new Event('input', { bubbles: true }));
            activeInputElement.dispatchEvent(new Event('change', { bubbles: true }));
            
            calendar.style.display = 'none';
            activeInputElement = null;
            if (options.onClose) {
              options.onClose();
            }
          }
        }
      });
      calendarGrid.appendChild(dayEl);
    }
  }

  function showCalendar(inputElement) {
    activeInputElement = inputElement;
    const inputRect = inputElement.getBoundingClientRect();
    const calWidth = 280;
    const gap = 6;

    let top = inputRect.bottom + gap;
    let left = inputRect.left;

    if (left + calWidth > window.innerWidth - 8) {
      left = window.innerWidth - calWidth - 8;
    }
    if (top + 320 > window.innerHeight) {
      top = inputRect.top - 320 - gap;
    }

    calendar.style.top = `${top}px`;
    calendar.style.left = `${left}px`;
    calendar.style.display = 'block';

    const options = inputElement.customCalendarOptions || {};
    
    if (options.mode === 'range') {
      const parts = inputElement.value.split(" to ");
      rangeStart = parseDate(parts[0], inputElement);
      rangeEnd = parts.length === 2 ? parseDate(parts[1], inputElement) : null;
      if (rangeStart) {
        currentMonth = rangeStart.getMonth();
        currentYear = rangeStart.getFullYear();
      } else {
        const today = new Date();
        currentMonth = today.getMonth();
        currentYear = today.getFullYear();
      }
    } else {
      currentSelectedDate = parseDate(inputElement.value, inputElement);
      if (currentSelectedDate) {
        currentMonth = currentSelectedDate.getMonth();
        currentYear = currentSelectedDate.getFullYear();
      } else {
        const today = new Date();
        currentMonth = today.getMonth();
        currentYear = today.getFullYear();
      }
    }
    
    renderCalendar(currentMonth, currentYear);
  }

  prevMonthBtn.addEventListener('click', () => {
    currentMonth--;
    if (currentMonth < 0) {
      currentMonth = 11;
      currentYear--;
    }
    renderCalendar(currentMonth, currentYear);
  });

  nextMonthBtn.addEventListener('click', () => {
    currentMonth++;
    if (currentMonth > 11) {
      currentMonth = 0;
      currentYear++;
    }
    renderCalendar(currentMonth, currentYear);
  });

  // Hide calendar if clicking outside
  document.addEventListener('click', (e) => {
    if (activeInputElement && !calendar.contains(e.target) && !activeInputElement.contains(e.target)) {
      const input = activeInputElement;
      const options = input.customCalendarOptions || {};
      calendar.style.display = 'none';
      activeInputElement = null;
      if (options.onClose) {
        options.onClose();
      }
    }
  });

  if (calendarGrid) {
    calendarGrid.addEventListener('mouseleave', () => {
      const options = activeInputElement ? (activeInputElement.customCalendarOptions || {}) : {};
      if (options.mode === 'range' && rangeStart && !rangeEnd) {
        const cells = calendarGrid.querySelectorAll('.day-cell');
        cells.forEach(cell => {
          cell.classList.remove('in-range');
        });
      }
    });
  }

  // New function to handle automatic date formatting (dd/mm/yyyy)
  function autoFormatDate(e) {
    const input = e.target;
    const separator = getSeparator(input);
    const isRange = input.customCalendarOptions && input.customCalendarOptions.mode === 'range';
    
    let value = input.value.replace(/\D/g, '');
    let formattedValue = '';

    if (isRange) {
      // Range formatting: dd/mm/yyyy to dd/mm/yyyy
      if (value.length > 0) {
        formattedValue = value.substring(0, 2);
      }
      if (value.length > 2) {
        formattedValue += separator + value.substring(2, 4);
      }
      if (value.length > 4) {
        formattedValue += separator + value.substring(4, 8);
      }
      if (value.length > 8) {
        formattedValue += ' to ' + value.substring(8, 10);
      }
      if (value.length > 10) {
        formattedValue += separator + value.substring(10, 12);
      }
      if (value.length > 12) {
        formattedValue += separator + value.substring(12, 16);
      }
    } else {
      // Single formatting
      if (value.length > 0) {
        formattedValue = value.substring(0, 2);
      }
      if (value.length > 2) {
        formattedValue += separator + value.substring(2, 4);
      }
      if (value.length > 4) {
        formattedValue += separator + value.substring(4, 8);
      }
    }
    
    input.value = formattedValue;
  }

  // --- Programmatic API initialization ---
  window.initCustomCalendar = function(input, options = {}) {
    if (!input) return;

    let wrapper = input.parentNode;
    let icon = null;
    if (wrapper.classList.contains('date-input-wrapper')) {
      icon = wrapper.querySelector('.calendar-icon');
    }

    // 1. Create wrapper and icon if wrapper doesn't exist and noWrapper is false
    if (!options.noWrapper && !wrapper.classList.contains('date-input-wrapper')) {
      wrapper = document.createElement('div');
      wrapper.classList.add('date-input-wrapper');
      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);

      icon = document.createElement('span');
      icon.innerHTML = '<i class="far fa-calendar-alt"></i>';
      icon.classList.add('calendar-icon');
      wrapper.appendChild(icon);
    }

    // 2. Set options
    input.customCalendarOptions = options;
    input.removeAttribute('readonly'); 
    input.style.cursor = 'text'; 
    input.setAttribute('maxlength', options.mode === 'range' ? '24' : '10');

    // 3. Attach listeners idempotently
    if (icon && !icon.dataset.hasCalendarListener) {
      icon.addEventListener('click', (e) => {
        e.stopPropagation();
        showCalendar(input);
      });
      icon.dataset.hasCalendarListener = 'true';
    }

    if (options.clickOpens && !input.dataset.hasCalendarClickListener) {
      input.addEventListener('click', (e) => {
        e.stopPropagation();
        showCalendar(input);
      });
      input.dataset.hasCalendarClickListener = 'true';
    }

    if (!input.dataset.hasCalendarInputListener) {
      input.addEventListener('input', autoFormatDate);
      input.dataset.hasCalendarInputListener = 'true';
    }
  };

  // --- Automatic initialization for static fields ---
  const dateInputs = document.querySelectorAll('input[type="text"][placeholder*="dd/mm/yyyy"], input[type="text"][placeholder*="dd-mm-yyyy"]');
  dateInputs.forEach(input => {
    // If it's a range filter, initialize it as range mode
    const isRange = input.id === 'filterDateRange' || input.placeholder.includes('range');
    window.initCustomCalendar(input, {
      mode: isRange ? 'range' : 'single'
    });
  });
});
