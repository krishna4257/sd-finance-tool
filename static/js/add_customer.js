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
    const dwInput = document.getElementById('dw');
    const dsInput = document.getElementById('ds');
    const fdtInput = document.getElementById('fdt');
    // Load saved values from localStorage (only if empty)
    if (!dwInput.value && localStorage.getItem("saved_dw")) {
        dwInput.value = localStorage.getItem("saved_dw");
    }
    if (!dsInput.value && localStorage.getItem("saved_ds")) {
        dsInput.value = localStorage.getItem("saved_ds");
    }
    if (!fdtInput.value && localStorage.getItem("saved_fdt")) {
        fdtInput.value = localStorage.getItem("saved_fdt");
    }
    const tdtInput = document.getElementById('tdt');
    const amtInput = document.getElementById('amt');
    const daInput = document.getElementById('da');
    const submitButton = form.querySelector('button[type="submit"]');

    dwInput.addEventListener("change", () => {
        localStorage.setItem("saved_dw", dwInput.value);
    });
    dsInput.addEventListener("input", () => {
        localStorage.setItem("saved_ds", dsInput.value);
    });
    fdtInput.addEventListener("input", () => {
        localStorage.setItem("saved_fdt", fdtInput.value);
    });


    // List of all form fields (excluding readonly) for focus management and state control.
    const fields = [anoInput, nameInput, panoInput, dwInput, dsInput, fdtInput, amtInput];

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

    // --- A.no Duplication Check ---
    function checkAno() {
        const anoValue = anoInput.value.trim();
        message.style.display = 'none';
        setFormFieldsEnabled(false); // Disable form while checking

        if (anoValue === '') {
            return;
        }

        fetch(`/check_ano_exists?ano=${anoValue}`)
            .then(res => res.json())
            .then(data => {
                if (data.exists) {
                    message.textContent = `❌ Account Number ${anoValue} already exists. Please enter a new one.`;
                    message.className = "message-box error";
                    message.style.display = 'block';
                    anoInput.focus();
                } else {
                    message.style.display = 'none';
                    setFormFieldsEnabled(true);
                    nameInput.focus(); // Focus on name input after successful check
                }
            })
            .catch(err => {
                console.error("Error checking ANO:", err);
                message.textContent = `Error checking A.no: ${err.message}`;
                message.className = "message-box error";
                message.style.display = 'block';
                setFormFieldsEnabled(false);
            });
    }

    anoInput.addEventListener('blur', checkAno);
    anoInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            checkAno();
        }
    });

    // --- Dynamic Enter Key Loop ---
    function handleEnterKeyLoop(e) {
        if (e.key === 'Enter') {
            e.preventDefault();

            const currentIndex = fields.indexOf(e.target);
            let nextInput;

            if (currentIndex === -1) return;

            const tabOrderFull = [nameInput, panoInput, dwInput, dsInput, fdtInput, amtInput];
            const tabOrderSimplified = [nameInput, panoInput, amtInput];
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

            if (e.target === fdtInput) {
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
        const ds = parseInt(dsInput.value);
        const amt = parseFloat(amtInput.value);
        const fdt = fdtInput.value;
        const dw = dwInput.value;

        if (fdt && ds && dw) {
            const startDate = parseDDMMYYYY(fdt);
            if (startDate) {
                let endDate = new Date(startDate);
                if (dw === 'W') {
                    endDate.setDate(endDate.getDate() + (ds * 7));
                } else {
                    endDate.setMonth(endDate.getMonth() + ds);
                }
                tdtInput.value = formatDateToDDMMYYYY(endDate);
            } else {
                tdtInput.value = '';
            }
        } else {
            tdtInput.value = '';
        }

        if (!isNaN(amt) && !isNaN(ds) && ds > 0) {
            daInput.value = (amt / ds).toFixed(2);
        } else {
            daInput.value = '';
        }
    }
    
    [dwInput, dsInput, fdtInput, amtInput].forEach(input => {
        if (input) input.addEventListener('input', calculateLoanFields);
    });

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
        
        message.textContent = "Saving...";
        message.className = "message-box";
        message.style.display = 'block';

        fetch("/add_customer", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                message.textContent = `Error: ${data.error}`;
                message.className = "message-box error";
            } else {
                message.textContent = data.message;
                message.className = "message-box success";
                document.getElementById('highestAnoDisplay').textContent = data.highest_ano;
                
                // Clear all dynamic fields to prepare for a new entry
                document.getElementById('ano').value = '';
                document.getElementById('name').value = '';
                document.getElementById('add2').value = '';
                document.getElementById('add3').value = '';
                document.getElementById('pano').value = '';
                document.getElementById('amt').value = '';
                // document.getElementById('dw').value = 'W';
                // document.getElementById('ds').value = '';
                // document.getElementById('fdt').value = '';
                document.getElementById('tdt').value = '';
                document.getElementById('da').value = '';
                
                if (parentInfoTooltip) parentInfoTooltip.style.display = 'none';

                setFormFieldsEnabled(false); // Disable form again
                anoInput.focus(); // Move cursor back to the A.no field
                
                loanFieldsSet = false; // Reset the loop state
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
    setFormFieldsEnabled(false);
    anoInput.focus();


    dwInput.addEventListener("change", () => {
        localStorage.setItem("saved_dw", dwInput.value);
    });

    dsInput.addEventListener("input", () => {
        localStorage.setItem("saved_ds", dsInput.value);
    });

    fdtInput.addEventListener("input", () => {
        localStorage.setItem("saved_fdt", fdtInput.value);
    });


});
