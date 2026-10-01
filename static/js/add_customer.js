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
    return function (...args) {
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

    // Aadhaar Duplicate Tracking
    let currentAadhaarDuplicates = [];
    let confirmedAadhaarBypass = null;

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

    // --- Aadhaar Duplicate Check ---
    const aadhaarInput = document.getElementById('aadhaar_number');
    const aadhaarWarnBox = document.getElementById('aadhaarDuplicateWarning');
    const aadhaarWarnCount = document.getElementById('aadhaarWarnCount');

    const checkAadhaarDuplicate = debounce(function () {
        if (!aadhaarInput) return;
        const rawVal = aadhaarInput.value.trim();
        const cleanVal = rawVal.replace(/[^0-9]/g, "");

        if (cleanVal.length !== 12) {
            currentAadhaarDuplicates = [];
            confirmedAadhaarBypass = null;
            if (aadhaarWarnBox) aadhaarWarnBox.style.display = 'none';
            return;
        }

        fetch(`/api/customer/check_aadhaar?aadhaar=${cleanVal}`)
            .then(res => res.json())
            .then(data => {
                if (data.duplicate && data.accounts && data.accounts.length > 0) {
                    currentAadhaarDuplicates = data.accounts;
                    if (aadhaarWarnCount) aadhaarWarnCount.textContent = data.accounts.length;
                    if (aadhaarWarnBox) aadhaarWarnBox.style.display = 'block';
                } else {
                    currentAadhaarDuplicates = [];
                    confirmedAadhaarBypass = null;
                    if (aadhaarWarnBox) aadhaarWarnBox.style.display = 'none';
                }
            })
            .catch(err => {
                console.error("Error checking Aadhaar duplicate:", err);
            });
    }, 250);

    if (aadhaarInput) {
        aadhaarInput.addEventListener("input", function () {
            this.value = this.value.replace(/[^0-9]/g, "").slice(0, 12);
            checkAadhaarDuplicate();
        });
        aadhaarInput.addEventListener("blur", function () {
            checkAadhaarDuplicate();
        });
    }

    window.showAadhaarDuplicatesModal = function () {
        const modal = document.getElementById('duplicateAadhaarModal');
        const tbody = document.getElementById('dupeAccountsTableBody');
        const emptyNotice = document.getElementById('dupeAccountsEmptyNotice');
        const aadhaarSpan = document.getElementById('dupeModalAadhaar');
        const countBadge = document.getElementById('dupeModalCountBadge');

        if (!modal) return;

        const currentAadhaar = aadhaarInput ? aadhaarInput.value.replace(/[^0-9]/g, "") : "—";
        if (aadhaarSpan) aadhaarSpan.textContent = currentAadhaar || "—";
        if (countBadge) countBadge.textContent = `${currentAadhaarDuplicates.length} Accounts`;

        if (tbody) {
            tbody.innerHTML = '';
            if (currentAadhaarDuplicates.length === 0) {
                if (emptyNotice) emptyNotice.style.display = 'block';
            } else {
                if (emptyNotice) emptyNotice.style.display = 'none';
                currentAadhaarDuplicates.forEach(acc => {
                    const tr = document.createElement('tr');
                    tr.style.borderBottom = '1px solid var(--border)';
                    const isOpen = acc.status === 'open' || acc.status === 'active';
                    const statusBadge = isOpen
                        ? '<span style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; padding: 2px 8px; font-size: 11px; font-weight: 700;">OPEN</span>'
                        : '<span style="background: rgba(100, 116, 139, 0.15); color: #64748b; border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 12px; padding: 2px 8px; font-size: 11px; font-weight: 700;">CLOSED</span>';

                    tr.innerHTML = `
                        <td style="padding: 10px 14px; font-weight: 700; font-family: monospace;">#${acc.ano}</td>
                        <td style="padding: 10px 14px; font-weight: 600;">${acc.name}</td>
                        <td style="padding: 10px 14px; color: var(--text-secondary);"><i class="fas fa-map-marker-alt text-danger me-1"></i>${acc.village_name}</td>
                        <td style="padding: 10px 14px; font-family: monospace;">${acc.phone_number || '—'}</td>
                        <td style="padding: 10px 14px; font-weight: 600;">₹${Number(acc.total_amount).toLocaleString('en-IN')}</td>
                        <td style="padding: 10px 14px; font-weight: 700; color: ${Number(acc.balance_amount) > 0 ? '#ef4444' : 'var(--text)'};">₹${Number(acc.balance_amount).toLocaleString('en-IN')}</td>
                        <td style="padding: 10px 14px; text-align: center;">${statusBadge}</td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        }

        modal.style.display = 'flex';
    };

    window.closeAadhaarDuplicatesModal = function () {
        const modal = document.getElementById('duplicateAadhaarModal');
        if (modal) modal.style.display = 'none';
    };

    document.addEventListener('click', function (e) {
        const modal = document.getElementById('duplicateAadhaarModal');
        if (modal && e.target === modal) {
            modal.style.display = 'none';
        }
    });

    let isFetchingPano = false;
    let lastFetchedPano = "";

    function fetchParentDetails(goToNext = false) {
        const panoValue = panoInput.value.trim();
        if (!panoValue) {
            if (goToNext) {
                if (phoneNumberInput) phoneNumberInput.focus();
            }
            return;
        }

        if (isFetchingPano || lastFetchedPano === panoValue) {
            if (goToNext) {
                if (totalAmountInput) totalAmountInput.focus();
            }
            return;
        }

        isFetchingPano = true;
        message.textContent = "Loading customer details...";
        message.className = "message-box info";
        message.style.display = "block";

        fetch(`/get_parent_details?pano=${panoValue}`)
            .then(res => res.json())
            .then(data => {
                isFetchingPano = false;
                if (data.found) {
                    lastFetchedPano = panoValue;
                    if (data.name) nameInput.value = data.name;
                    if (data.phone_number) phoneNumberInput.value = data.phone_number;
                    const aadhaarInput = document.getElementById('aadhaar_number');
                    if (data.aadhaar_number && aadhaarInput) aadhaarInput.value = data.aadhaar_number;
                    const latInput = document.getElementById('latitude');
                    if (data.latitude && latInput) latInput.value = data.latitude;
                    const lonInput = document.getElementById('longitude');
                    if (data.longitude && lonInput) lonInput.value = data.longitude;

                    message.textContent = `✔️ Details populated from Parent Account ${panoValue}`;
                    message.className = "message-box success";
                    message.style.display = "block";

                    setFormFieldsEnabled(true);

                    if (goToNext) {
                        if (totalAmountInput) totalAmountInput.focus();
                    }
                } else {
                    message.textContent = `❌ Parent Account ${panoValue} not found`;
                    message.className = "message-box error";
                    message.style.display = "block";
                    if (goToNext) {
                        nameInput.focus();
                    }
                }
            })
            .catch(err => {
                isFetchingPano = false;
                console.error("Error fetching parent details:", err);
                message.textContent = "Error loading customer details";
                message.className = "message-box error";
                if (goToNext) {
                    if (phoneNumberInput) phoneNumberInput.focus();
                }
            });
    }

    if (panoInput) {
        panoInput.addEventListener('input', () => {
            lastFetchedPano = "";
        });
        panoInput.addEventListener("change", () => fetchParentDetails(false));
        panoInput.addEventListener("blur", () => fetchParentDetails(false));
    }

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

            if (e.target === panoInput) {
                fetchParentDetails(true);
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
    function calculateLoanFields(e) {
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
                } else if (type === 'D') {
                    endDate.setDate(endDate.getDate() + period);
                } else {
                    endDate.setMonth(endDate.getMonth() + period);
                }
                endDateInput.value = formatDateToDDMMYYYY(endDate);
            }
        } else {
            endDateInput.value = '';
        }

        if (!isNaN(amount) && !isNaN(period) && period > 0) {
            installmentAmountInput.value = (amount / period).toFixed(0);
        } else {
            installmentAmountInput.value = '';
        }

        // Automatic split calculation
        const interestInput = document.getElementById('interest_amount');
        const cuttingInput = document.getElementById('cutting_amount');
        const baseInput = document.getElementById('base_amount');
        const splitFieldsContainer = document.getElementById('splitFieldsContainer');

        if (!isNaN(amount) && amount > 0) {
            if (splitFieldsContainer) splitFieldsContainer.style.display = 'block';

            // Only auto-calculate interest and cutting if this was triggered by total_amount change
            // or if the fields are empty
            const interestRate = parseFloat(window.VILLAGE_INTEREST_RATE) || 0.0;
            const cuttingRate = parseFloat(window.VILLAGE_CUTTING_RATE) || 0.0;

            if (e && e.target === totalAmountInput) {
                if (interestInput) interestInput.value = (amount * interestRate / 100.0).toFixed(0);
                if (cuttingInput) cuttingInput.value = (amount * cuttingRate / 100.0).toFixed(0);
            } else {
                if (interestInput && interestInput.value === '') {
                    interestInput.value = (amount * interestRate / 100.0).toFixed(0);
                }
                if (cuttingInput && cuttingInput.value === '') {
                    cuttingInput.value = (amount * cuttingRate / 100.0).toFixed(0);
                }
            }

            const interestVal = Math.round(parseFloat(interestInput?.value) || 0.0);
            const cuttingVal = Math.round(parseFloat(cuttingInput?.value) || 0.0);
            if (baseInput) {
                baseInput.value = (amount - interestVal - cuttingVal).toFixed(0);
            }
        } else {
            if (splitFieldsContainer) splitFieldsContainer.style.display = 'none';
            if (interestInput) interestInput.value = '';
            if (cuttingInput) cuttingInput.value = '';
            if (baseInput) baseInput.value = '';
        }
    }

    [typeInput, periodInput, startDateInput, totalAmountInput]
        .forEach(el => el.addEventListener('input', calculateLoanFields));

    function updatePeriodPlaceholder() {
        const type = typeInput.value;
        if (type === 'W') {
            periodInput.placeholder = "Number of Weeks";
        } else if (type === 'M') {
            periodInput.placeholder = "Number of Months";
        } else if (type === 'D') {
            periodInput.placeholder = "Number of Days";
        }
    }
    typeInput.addEventListener('change', updatePeriodPlaceholder);
    
    // Auto-detect monthly village from name/context and preset Type to Monthly ('M')
    const vidInput = document.getElementById('vid');
    const vName = (window.VILLAGE_NAME || (vidInput ? vidInput.value : "")).trim().toUpperCase();
    if (vName.endsWith('-M') || vName.includes('-M')) {
        typeInput.value = 'M';
    }
    updatePeriodPlaceholder();

    const interestInput = document.getElementById('interest_amount');
    const cuttingInput = document.getElementById('cutting_amount');

    function updateBaseAmount() {
        const amount = parseFloat(totalAmountInput.value);
        const interestVal = Math.round(parseFloat(interestInput?.value) || 0.0);
        const cuttingVal = Math.round(parseFloat(cuttingInput?.value) || 0.0);
        const baseInput = document.getElementById('base_amount');
        if (baseInput && !isNaN(amount)) {
            baseInput.value = (amount - interestVal - cuttingVal).toFixed(0);
        }
    }

    if (interestInput) interestInput.addEventListener('input', updateBaseAmount);
    if (cuttingInput) cuttingInput.addEventListener('input', updateBaseAmount);

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

        // Aadhaar Duplicate Warning Guard
        const rawAadhaar = aadhaarInput ? aadhaarInput.value.trim() : "";
        const cleanAadhaar = rawAadhaar.replace(/[^0-9]/g, "");

        if (cleanAadhaar.length === 12 && currentAadhaarDuplicates && currentAadhaarDuplicates.length > 0 && confirmedAadhaarBypass !== cleanAadhaar) {
            const proceed = confirm(`⚠️ DUPLICATE AADHAAR WARNING:\n\nThis Aadhaar (${cleanAadhaar}) is already registered with ${currentAadhaarDuplicates.length} existing account(s) across villages.\n\n• Click OK to proceed and add this customer anyway.\n• Click Cancel to review the existing accounts.`);
            if (!proceed) {
                isSubmitting = false;
                window.showAadhaarDuplicatesModal();
                return;
            }
            confirmedAadhaarBypass = cleanAadhaar;
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
                    document.getElementById('name').value = '';
                    document.getElementById('aadhaar_number').value = '';
                    document.getElementById('pano').value = '';
                    document.getElementById('phone_number').value = '';

                    currentAadhaarDuplicates = [];
                    confirmedAadhaarBypass = null;
                    if (aadhaarWarnBox) aadhaarWarnBox.style.display = 'none';

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
    form.addEventListener("submit", function (e) {
        e.preventDefault();
        submitForm();
    });

    // --- Initial State ---
    setFormFieldsEnabled(true);
    anoInput.focus();

    function loadMetadata() {
        fetch('/api/add_customer/metadata')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const highestAnoDisplay = document.getElementById('highestAnoDisplay');
                    if (highestAnoDisplay) {
                        highestAnoDisplay.textContent = data.highest_ano;
                    }
                    if (data.highest_ano && !anoInput.value) {
                        anoInput.value = data.highest_ano + 1;
                    }

                    if (data.analytics) {
                        const countToday = document.getElementById('countToday');
                        const countWeek = document.getElementById('countWeek');
                        const countMonth = document.getElementById('countMonth');
                        if (countToday) countToday.textContent = data.analytics.today;
                        if (countWeek) countWeek.textContent = data.analytics.week;
                        if (countMonth) countMonth.textContent = data.analytics.month;
                    }
                }
            })
            .catch(err => {
                console.error("Error loading add_customer metadata:", err);
            });
    }

    loadMetadata();

    // Preserve previously selected loan configuration during repeated entries
    if (typeInput.value && periodInput.value && startDateInput.value) {
        loanFieldsSet = true;
        calculateLoanFields();
    }

});
