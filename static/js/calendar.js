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
      dayEl.classList.add('calendar-day');
      dayEl.textContent = i;

      const today = new Date();
      if (i === today.getDate() && month === today.getMonth() && year === today.getFullYear()) {
        dayEl.classList.add('today');
      }

      dayEl.addEventListener('click', () => {
        if (activeInputElement) {
          const selectedDate = new Date(year, month, i);
          activeInputElement.value = formatDateToDDMMYYYY(selectedDate);
          calendar.style.display = 'none';
          activeInputElement = null;
        }
      });
      calendarGrid.appendChild(dayEl);
    }
  }

  function showCalendar(inputElement) {
    activeInputElement = inputElement;
    const inputRect = inputElement.getBoundingClientRect();
    calendar.style.display = 'block';
    calendar.style.top = `${inputRect.bottom + window.scrollY + 5}px`;
    calendar.style.left = `${inputRect.left + window.scrollX}px`;

    // Try to set calendar to the input's current date
    const dateValue = parseDDMMYYYY(inputElement.value);
    if (dateValue) {
        currentMonth = dateValue.getMonth();
        currentYear = dateValue.getFullYear();
    } else {
        const today = new Date();
        currentMonth = today.getMonth();
        currentYear = today.getFullYear();
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
    if (!calendar.contains(e.target) && activeInputElement && !activeInputElement.contains(e.target)) {
      calendar.style.display = 'none';
      activeInputElement = null;
    }
  });

    // --- Initialization ---

    // New function to handle automatic date formatting (dd/mm/yyyy)
    function autoFormatDate(e) {
    const input = e.target;
    // Remove all non-digit characters from the input
    let value = input.value.replace(/\D/g, '');
    let formattedValue = '';

    // Add the 'dd' part
    if (value.length > 0) {
        formattedValue = value.substring(0, 2);
    }
    // Add the '/' and 'mm' part
    if (value.length > 2) {
        formattedValue += '/' + value.substring(2, 4);
    }
    // Add the '/' and 'yyyy' part
    if (value.length > 4) {
        formattedValue += '/' + value.substring(4, 8);
    }
    
    // Update the input field with the formatted value
    input.value = formattedValue;
    }

    // Find all text inputs with a 'date' placeholder, wrap them, and attach functionality
    const dateInputs = document.querySelectorAll('input[type="text"][placeholder*="dd/mm/yyyy"]');

    dateInputs.forEach(input => {
    // Check if the wrapper already exists to prevent re-wrapping on re-renders
    if (input.parentNode.classList.contains('date-input-wrapper')) {
        return;
    }

    // 1. Create a wrapper div
    const wrapper = document.createElement('div');
    wrapper.classList.add('date-input-wrapper');

    // 2. Insert the wrapper and move the input inside it
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);

    // 3. Create and append the icon
    const icon = document.createElement('span');
    icon.innerHTML = '📆';
    icon.classList.add('calendar-icon');
    wrapper.appendChild(icon);

    // 4. Enable manual typing and add auto-formatting
    input.removeAttribute('readonly'); // Allow typing
    input.style.cursor = 'text'; // Use a normal text cursor
    input.addEventListener('input', autoFormatDate); // Add the auto-slashing logic
    input.setAttribute('maxlength', '10'); // Limit input to dd/mm/yyyy length

    // 5. Add click listener ONLY to the icon to open the calendar
    icon.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent the document click listener from firing
        showCalendar(input);
    });
    });
});
