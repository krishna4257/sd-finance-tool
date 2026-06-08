// File: static/js/add_customer.js

// This file handles all client-side logic for the "Add New Customer" page.
// It includes form validation, real-time calculations, and an improved user flow.

// --- Helper Functions ---
// Date parsing and formatting helpers are provided globally by utils.js.

/**
 * A debounced function to limit the rate of API calls.
 * @param {function} func - The function to debounce.
 * @param {number} delay - The delay in milliseconds.
 */
function debounce(func, delay) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), delay);
  };
}


// --- Main Page Logic ---
document.addEventListener('DOMContentLoaded', function () {
    // --- Element References ---
    const form = document.getElementById('customerForm');
    const message = document.getElementById('message');
    const parentInfoTooltip = document.getElementById('parentInfoTooltip');
    const parentInfoText = document.getElementById('parentInfoText');

    const anoInput = document.getElementById('ano');
    const nameInput = document.getElementById('name');
    const panoInput = document.getElementById('pano');
    const phoneNumberInput = document.getElementById('phone_number');
    const typeInput = document.getElementById('type');
    const periodInput = document.getElementById('period');
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    const totalAmountInput = document.getElementById('total_amount');
    const installmentAmountInput = document.getElementById('installment_amount');
    const submitButton = form.querySelector('button[type="submit"]');


    // List of all form fields (excluding readonly) for focus management and state control.
    const fields = [
      anoInput,
      nameInput,
      panoInput,
      phoneNumberInput,
      typeInput,
      periodInput,
      startDateInput,
      totalAmountInput
    ];

    // State variable to track if loan fields have been set,
    // enabling the conditional tab loop.
    let loanFieldsSet = false;

    // ✅ NEW STATE FLAG: Prevents duplicate submissions
    let isSubmitting = false;

    // --- Form State Controller ---
    /**
     * Disables or enables all form fields except the account number.
     * @param {boolean} enabled - True to enable, false to disable.
     */
    function setFormFieldsEnabled(enabled) {
        fields.forEach(field => {
            if (field !== anoInput && field) {
                field.disabled = !enabled;
            }
        });
        if (submitButton) submitButton.disabled = !enabled;
    }

    phoneNumberInput.addEventListener("input", function () {
        this.value = this.value.replace(/[^0-9]/g, "").slice(0, 10);
    });

    // Restrict invalid customer names
    nameInput.addEventListener("input", function () {
        // Allow only letters and spaces
        this.value = this.value.replace(/[^a-zA-Z\s]/g, "");

        // Prevent multiple spaces
        this.value = this.value.replace(/\s{2,}/g, " ");

        // Prevent leading spaces
        this.value = this.value.replace(/^\s+/g, "");
    });

    document.getElementById("ano").addEventListener("input", function () {
        this.value = this.value.replace(/[^0-9]/g, "");
    });
   
    function checkAno() {
    const ano = anoInput.value.trim();
    if (!ano) return;

    fetch(`/check_ano_exists?ano=${ano}`)
        .then(res => res.json())
        .then(data => {
            if (data.exists) {
                message.textContent = "❌ Account number already exists";
                message.className = "message-box error";
                message.style.display = "block";
                setFormFieldsEnabled(false);
                anoInput.focus();
            } else {
                message.style.display = "none";
                setFormFieldsEnabled(true);   // ✅ THIS IS THE KEY LINE
                nameInput.focus();
            }
        })
        .catch(err => {
            console.error(err);
            message.textContent = "Error checking account number";
            message.className = "message-box error";
            message.style.display = "block";
        });
}
anoInput.addEventListener("blur", checkAno);
anoInput.addEventListener("change", checkAno);
    // --- Dynamic Enter Key Loop ---
    function handleEnterKeyLoop(e) {
        if (e.key === 'Enter') {
            e.preventDefault();

            const currentIndex = fields.indexOf(e.target);
            let nextInput;

            if (currentIndex === -1) return;

            const tabOrderFull = [anoInput, nameInput, panoInput, phoneNumberInput, typeInput, periodInput, startDateInput, totalAmountInput];
            const tabOrderSimplified = [nameInput, panoInput, phoneNumberInput, totalAmountInput];
            const currentTabOrder = loanFieldsSet ? tabOrderSimplified : tabOrderFull;

            const nextIndex = currentTabOrder.indexOf(e.target) + 1;
            nextInput = currentTabOrder[nextIndex];
            
            if (e.target === anoInput) {
                checkAno();
                return;
            }

            if (!nextInput) {
                submitForm(); // ✅ Call the dedicated submission function
                return;
            }

            if (e.target === startDateInput) {
                loanFieldsSet = true;
            }
            
            nextInput.focus();
        }
    }

    fields.forEach(input => {
        if (input) input.addEventListener('keydown', handleEnterKeyLoop);
    });

    // --- Loan Field Calculation ---
    function calculateLoanFields() {
        const period = parseInt(periodInput.value);
        const amount = parseFloat(totalAmountInput.value);
        const start = startDateInput.value;
        const type = typeInput.value;

        if (start && period && type) {
            const startDate = parseDDMMYYYY(start);
            if (startDate) {
                let endDate = new Date(startDate);
                if (type === 'W') {
                    endDate.setDate(endDate.getDate() + (period * 7));
                } else {
                    endDate.setMonth(endDate.getMonth() + period);
                }
                endDateInput.value = formatDateToDDMMYYYY(endDate);
            }
        } else {
            endDateInput.value = '';
        }

        if (!isNaN(amount) && !isNaN(period) && period > 0) {
            installmentAmountInput.value = (amount / period).toFixed(2);
        } else {
            installmentAmountInput.value = '';
        }
    }
    
    [typeInput, periodInput, startDateInput, totalAmountInput]
  .forEach(el => el.addEventListener('input', calculateLoanFields));

    // --- Parent Link Check ---
    if (panoInput && parentInfoTooltip && parentInfoText) {
        let tooltipTimeout;

        const checkParentLink = () => {
            clearTimeout(tooltipTimeout);
            parentInfoTooltip.style.display = 'none';

            const panoValue = panoInput.value.trim();
            if (panoValue === '') {
                return;
            }

            fetch(`/check_parent_link?pano=${panoValue}`)
                .then(response => response.json())
                .then(data => {
                    if (data.found && data.accounts && data.accounts.length > 0) {
                        const accountsString = data.accounts.join(', ');
                        parentInfoText.textContent = `ℹ️ Linked with account(s): ${accountsString}.`;
                        
                        const panoRect = panoInput.getBoundingClientRect();
                        const formGlassRect = form.closest('.form-glass').getBoundingClientRect();
                        
                        parentInfoTooltip.style.top = `${panoRect.bottom - formGlassRect.top + window.scrollY + 5}px`;
                        parentInfoTooltip.style.left = `${panoRect.left - formGlassRect.left + window.scrollX}px`;
                        
                        parentInfoTooltip.style.display = 'block';
                        
                        tooltipTimeout = setTimeout(() => {
                            parentInfoTooltip.style.display = 'none';
                        }, 5000);
                    } else {
                        parentInfoTooltip.style.display = 'none';
                    }
                })
                .catch(err => {
                    console.error("Error checking parent link:", err);
                    parentInfoTooltip.style.display = 'none';
                });
        };
        
        panoInput.addEventListener('input', debounce(checkParentLink, 400));
        
        panoInput.addEventListener('blur', () => {
            clearTimeout(tooltipTimeout);
            parentInfoTooltip.style.display = 'none';
        });
        
        panoInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                clearTimeout(tooltipTimeout);
                parentInfoTooltip.style.display = 'none';
            }
        });
    }

    // --- Form Submission Logic (Centralized Function) ---
    function submitForm() {
        // ✅ CRITICAL: Prevent re-submission if already submitting
        if (isSubmitting) {
            console.log("Submission already in progress. Ignoring request.");
            return;
        }

        isSubmitting = true; // ✅ Set the flag to true
        
        const formData = new FormData(form);

        // Customer name validation
        const customerName = (nameInput.value || "").trim();

        // Remove spaces to calculate actual letters
        const lettersOnly = customerName.replace(/\s/g, "");

        // Must contain only alphabets and spaces
        const validNamePattern = /^[A-Za-z ]+$/;

        if (
            !customerName ||
            !validNamePattern.test(customerName) ||
            lettersOnly.length < 3
        ) {
            message.textContent = "Customer name must contain at least 3 letters and cannot contain numbers or special characters";
            message.className = "message-box error";
            message.style.display = 'block';

            nameInput.focus();
            isSubmitting = false;
            return;
        }
        
        message.textContent = "Saving...";
        message.className = "message-box";
        message.style.display = 'block';

        csrfFetch("/add_customer", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                message.textContent = `Error: ${data.error}`;
                message.className = "message-box error";
            } else {
                // Show success BEFORE clearing form
                message.textContent = `✔️ Customer ${data.new_ano} added successfully`;
                message.className = "message-box success success-highlight";
                document.getElementById('highestAnoDisplay').textContent = data.highest_ano;
                
                // Update analytics in real-time
                if (data.analytics) {
                    document.getElementById('countToday').textContent = data.analytics.today;
                    document.getElementById('countWeek').textContent = data.analytics.week;
                    document.getElementById('countMonth').textContent = data.analytics.month;
                }
                
                anoInput.value = data.highest_ano + 1;
                // Clear all dynamic fields to prepare for a new entry
                document.getElementById('ano').value = '';
                document.getElementById('name').value = '';
                document.getElementById('aadhaar_number').value = '';
                document.getElementById('pano').value = '';
                document.getElementById('phone_number').value = '';

                document.getElementById('total_amount').value = '';

                // Keep these fields persistent for repeated customer entry
                // type
                // period
                // start_date

                // Recalculate derived fields using preserved values
                calculateLoanFields();

                document.getElementById('longitude').value = '';
                document.getElementById('latitude').value = '';
                
                
                if (parentInfoTooltip) parentInfoTooltip.style.display = 'none';

                setFormFieldsEnabled(false); // Disable form again

                anoInput.focus(); // Move cursor back to the A.no field
                
                // Keep simplified fast-entry workflow active
                loanFieldsSet = true;
            }
        })
        .catch(err => {
            message.textContent = `A network error occurred: ${err.message}`;
            message.className = "message-box error";
        })
        .finally(() => {
            isSubmitting = false; // ✅ Reset the flag regardless of outcome
        });
    }

    // --- Event Listeners for Submission ---
    form.addEventListener("submit", function(e) {
        e.preventDefault();
        submitForm();
    });
    
    // --- Initial State ---
    setFormFieldsEnabled(true);
    anoInput.focus();

    const highestAno = parseInt(
      document.getElementById("highestAnoDisplay")?.innerText || "0",
      10
    );

    if (!isNaN(highestAno)) {
      anoInput.value = highestAno + 1;
    }

    // Preserve previously selected loan configuration during repeated entries
    if (typeInput.value && periodInput.value && startDateInput.value) {
        loanFieldsSet = true;
        calculateLoanFields();
    }

});
