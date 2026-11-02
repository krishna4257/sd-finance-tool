/**
 * SIVA DURGA FINANCE — INVESTOR FOLIO MODULE
 * Dynamic Calculations, AJAX Handlers, and Modal Workflows for Investor Accounts
 */

(function (window) {
  'use strict';

  const Folio = {};

  /**
   * Initializes dynamic calculations across all village allocations on the page.
   */
  Folio.initCalculations = function () {
    const rows = document.querySelectorAll('[data-allocation-row]');
    let totalAccruedInterest = 0;

    rows.forEach(row => {
      const principal = parseFloat(row.dataset.principal || 0);
      const startDate = row.dataset.startDate;
      const rate = parseFloat(row.dataset.rate || 24.0);

      if (principal > 0 && startDate) {
        const calc = SD_BANKING.calcCompoundInterest(principal, startDate, null, rate);

        const daysEl = row.querySelector('.allocation-days');
        const interestEl = row.querySelector('.allocation-interest');
        const totalEl = row.querySelector('.allocation-total');

        if (daysEl) daysEl.textContent = `${calc.daysElapsed} days`;
        if (interestEl) interestEl.textContent = SD_BANKING.formatINR(calc.accruedInterest);
        if (totalEl) totalEl.textContent = SD_BANKING.formatINR(calc.totalPayoff);

        totalAccruedInterest += calc.accruedInterest;
      }
    });

    // Update global card if present
    const totalAccruedCard = document.getElementById('statTotalAccruedInterest');
    if (totalAccruedCard && totalAccruedCard.dataset.autoCalc === 'true') {
      totalAccruedCard.textContent = SD_BANKING.formatINR(totalAccruedInterest);
    }
  };

  /**
   * Handle Deposit Capital Submission
   */
  Folio.handleDepositSubmit = async function (formEvent, investorId) {
    if (formEvent) formEvent.preventDefault();
    const form = formEvent ? formEvent.target : document.getElementById('depositCapitalForm');
    if (!form) return;

    const amount = parseFloat(form.querySelector('[name="amount"]').value || 0);
    const paymentMode = form.querySelector('[name="payment_mode"]').value;
    const txnDate = form.querySelector('[name="txn_date"]').value;
    const notes = form.querySelector('[name="notes"]').value;
    const isBackdated = form.querySelector('[name="is_backdated"]') ? form.querySelector('[name="is_backdated"]').checked : false;

    if (amount <= 0) {
      SD_BANKING.showToast('Please enter a valid deposit amount greater than ₹0', 'error');
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="inline-block animate-spin mr-2">⏳</span> Depositing...';
    }

    try {
      const res = await SD_BANKING.bankingFetch(`/banking/api/investors/${investorId}/deposit`, {
        method: 'POST',
        body: {
          amount: amount,
          payment_mode: paymentMode,
          txn_date: txnDate,
          notes: notes,
          is_backdated: isBackdated
        }
      });

      if (res && res.success !== false) {
        SD_BANKING.showToast(`Capital deposit of ${SD_BANKING.formatINR(amount)} recorded successfully!`, 'success');
        setTimeout(() => window.location.reload(), 800);
      } else {
        throw new Error((res && res.error) || 'Deposit failed');
      }
    } catch (err) {
      SD_BANKING.showToast(err.message || 'Error processing deposit', 'error');
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Confirm Deposit';
      }
    }
  };

  /**
   * Handle Withdraw Idle Cash (Strictly Protected by Master Admin PIN)
   */
  Folio.handleWithdrawSubmit = async function (formEvent, investorId, maxIdleBalance) {
    if (formEvent) formEvent.preventDefault();
    const form = formEvent ? formEvent.target : document.getElementById('withdrawCashForm');
    if (!form) return;

    const amount = parseFloat(form.querySelector('[name="amount"]').value || 0);
    const paymentMode = form.querySelector('[name="payment_mode"]').value;
    const txnDate = form.querySelector('[name="txn_date"]').value;
    const notes = form.querySelector('[name="notes"]').value;

    if (amount <= 0) {
      SD_BANKING.showToast('Please enter a valid withdrawal amount', 'error');
      return;
    }

    if (maxIdleBalance !== undefined && amount > maxIdleBalance) {
      SD_BANKING.showToast(`Withdrawal amount cannot exceed available Idle Cash balance of ${SD_BANKING.formatINR(maxIdleBalance)}`, 'error');
      return;
    }

    try {
      // Step 1: Prompt Master Admin PIN
      const auth = await SD_BANKING.promptAdminPin({
        title: 'Authorize Idle Cash Withdrawal',
        message: `Confirm payout of ${SD_BANKING.formatINR(amount)} via ${paymentMode}. Enter Admin PIN:`,
        actionLabel: 'Authorize Cash-Out'
      });

      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="inline-block animate-spin mr-2">⏳</span> Authorizing...';
      }

      // Step 2: Post to API
      const res = await SD_BANKING.bankingFetch(`/banking/api/investors/${investorId}/withdraw`, {
        method: 'POST',
        body: {
          amount: amount,
          payment_mode: paymentMode,
          txn_date: txnDate,
          notes: notes,
          pin: auth.pin
        }
      });

      if (res && res.success !== false) {
        SD_BANKING.showToast(`Withdrawal of ${SD_BANKING.formatINR(amount)} authorized successfully!`, 'success');
        setTimeout(() => window.location.reload(), 800);
      } else {
        throw new Error((res && res.error) || 'Withdrawal rejected');
      }
    } catch (err) {
      if (err.message !== 'Verification cancelled') {
        SD_BANKING.showToast(err.message || 'Error executing withdrawal', 'error');
      }
    }
  };

  /**
   * Handle Add Personal Expense / Drawings
   */
  Folio.handlePersonalExpenseSubmit = async function (formEvent, investorId) {
    if (formEvent) formEvent.preventDefault();
    const form = formEvent ? formEvent.target : document.getElementById('addPersonalExpenseForm');
    if (!form) return;

    const itemDesc = form.querySelector('[name="item_description"]').value.trim();
    const amount = parseFloat(form.querySelector('[name="amount"]').value || 0);
    const paymentMode = form.querySelector('[name="payment_mode"]').value;
    const expenseDate = form.querySelector('[name="expense_date"]').value;
    const receiptNo = form.querySelector('[name="receipt_no"]').value.trim();

    if (!itemDesc) {
      SD_BANKING.showToast('Please provide an item description (e.g. Courier, Vehicle repair, Household)', 'error');
      return;
    }

    if (amount <= 0) {
      SD_BANKING.showToast('Please enter a valid expense amount', 'error');
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="inline-block animate-spin mr-2">⏳</span> Recording...';
    }

    try {
      const res = await SD_BANKING.bankingFetch(`/banking/api/investors/${investorId}/personal-expense`, {
        method: 'POST',
        body: {
          item_description: itemDesc,
          amount: amount,
          payment_mode: paymentMode,
          expense_date: expenseDate,
          receipt_no: receiptNo
        }
      });

      if (res && res.success !== false) {
        SD_BANKING.showToast(`Personal expense of ${SD_BANKING.formatINR(amount)} booked to investor folio!`, 'success');
        setTimeout(() => window.location.reload(), 800);
      } else {
        throw new Error((res && res.error) || 'Failed to record expense');
      }
    } catch (err) {
      SD_BANKING.showToast(err.message || 'Error recording personal expense', 'error');
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Save Personal Expense';
      }
    }
  };

  /**
   * Reverse an investor personal expense / drawing
   */
  Folio.reversePersonalExpense = function (expenseId, amount) {
    SD_BANKING.promptReversal({
      txnType: 'Personal Drawing / Expense',
      txnId: expenseId,
      amount: amount,
      endpoint: `/banking/api/personal-expenses/${expenseId}/reverse`
    });
  };

  /**
   * Print Investor Statement
   */
  Folio.printStatement = function (investorId) {
    const url = `/banking/investors/${investorId}/statement?print=true`;
    const win = window.open(url, '_blank');
    if (win) win.focus();
  };

  /**
   * Toggle Card Collapse on Heading Click
   */
  Folio.toggleCardCollapse = function (bodyId, chevronId) {
    const bodyEl = document.getElementById(bodyId);
    const chevEl = document.getElementById(chevronId);
    if (!bodyEl) return;
    const isHidden = bodyEl.classList.contains('hidden');
    if (isHidden) {
      bodyEl.classList.remove('hidden');
      if (chevEl) chevEl.classList.remove('rotate-180');
    } else {
      bodyEl.classList.add('hidden');
      if (chevEl) chevEl.classList.add('rotate-180');
    }
  };

  /**
   * Toggle Deactivated Deployments Box
   */
  Folio.toggleDeactivatedDeployments = function () {
    const box = document.getElementById('deactivatedDeploymentsBox');
    const chev = document.getElementById('deactChevron');
    const label = document.getElementById('deactToggleLabel');
    if (!box) return;
    const isHidden = box.classList.contains('hidden');
    if (isHidden) {
      box.classList.remove('hidden');
      if (chev) chev.classList.add('rotate-180');
      if (label) label.textContent = label.textContent.replace('Show', 'Hide');
    } else {
      box.classList.add('hidden');
      if (chev) chev.classList.remove('rotate-180');
      if (label) label.textContent = label.textContent.replace('Hide', 'Show');
    }
  };

  /**
   * Toggle Settled Drawings Box
   */
  Folio.toggleSettledDrawings = function () {
    const box = document.getElementById('settledDrawingsBox');
    const chev = document.getElementById('settledChevron');
    const label = document.getElementById('settledToggleLabel');
    if (!box) return;
    const isHidden = box.classList.contains('hidden');
    if (isHidden) {
      box.classList.remove('hidden');
      if (chev) chev.classList.add('rotate-180');
      if (label) label.textContent = label.textContent.replace('Show', 'Hide');
    } else {
      box.classList.add('hidden');
      if (chev) chev.classList.remove('rotate-180');
      if (label) label.textContent = label.textContent.replace('Hide', 'Show');
    }
  };

  /**
   * Elaborate Modal: All Village Group Deployments
   */
  Folio.currentDepFilter = 'ALL';

  Folio.openAllDeploymentsModal = function () {
    const m = document.getElementById('allDeploymentsModal');
    if (m) {
      m.classList.remove('hidden');
      m.classList.add('flex');
      if (window.lucide) lucide.createIcons();
      Folio.initCalculations();
    }
  };

  Folio.closeAllDeploymentsModal = function () {
    const m = document.getElementById('allDeploymentsModal');
    if (m) {
      m.classList.add('hidden');
      m.classList.remove('flex');
    }
  };

  Folio.setDepFilter = function (filterType) {
    Folio.currentDepFilter = filterType;
    const btns = {
      'ALL': document.getElementById('depFilterAll'),
      'ACTIVE': document.getElementById('depFilterActive'),
      'INACTIVE': document.getElementById('depFilterInactive')
    };
    Object.keys(btns).forEach(key => {
      const b = btns[key];
      if (!b) return;
      if (key === filterType) {
        b.className = 'px-3 py-1 rounded-lg text-xs font-bold bg-blue-600 text-white shadow-sm';
      } else {
        b.className = 'px-3 py-1 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800';
      }
    });
    Folio.filterAllDeploymentsModal();
  };

  Folio.filterAllDeploymentsModal = function () {
    const searchInp = document.getElementById('depModalSearch');
    const q = searchInp ? searchInp.value.toLowerCase().trim() : '';
    const rows = document.querySelectorAll('.dep-modal-row');
    rows.forEach(r => {
      const status = r.dataset.depStatus;
      const searchData = r.dataset.depSearch || '';
      const matchesSearch = !q || searchData.includes(q);
      const matchesStatus = (Folio.currentDepFilter === 'ALL') || (status === Folio.currentDepFilter);
      if (matchesSearch && matchesStatus) {
        r.style.display = '';
      } else {
        r.style.display = 'none';
      }
    });
  };

  /**
   * Elaborate Modal: All Personal Expenses / Drawings
   */
  Folio.currentPeFilter = 'ALL';

  Folio.openAllPersonalExpensesModal = function () {
    const m = document.getElementById('allPersonalExpensesModal');
    if (m) {
      m.classList.remove('hidden');
      m.classList.add('flex');
      if (window.lucide) lucide.createIcons();
    }
  };

  Folio.closeAllPersonalExpensesModal = function () {
    const m = document.getElementById('allPersonalExpensesModal');
    if (m) {
      m.classList.add('hidden');
      m.classList.remove('flex');
    }
  };

  Folio.setPeFilter = function (filterType) {
    Folio.currentPeFilter = filterType;
    const btns = {
      'ALL': document.getElementById('peFilterAll'),
      'UNSETTLED': document.getElementById('peFilterUnsettled'),
      'SETTLED': document.getElementById('peFilterSettled')
    };
    Object.keys(btns).forEach(key => {
      const b = btns[key];
      if (!b) return;
      if (key === filterType) {
        b.className = 'px-3 py-1 rounded-lg text-xs font-bold bg-rose-600 text-white shadow-sm';
      } else {
        b.className = 'px-3 py-1 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800';
      }
    });
    Folio.filterAllPersonalExpensesModal();
  };

  Folio.filterAllPersonalExpensesModal = function () {
    const searchInp = document.getElementById('peModalSearch');
    const q = searchInp ? searchInp.value.toLowerCase().trim() : '';
    const rows = document.querySelectorAll('.pe-modal-row');
    rows.forEach(r => {
      const status = r.dataset.peStatus;
      const searchData = r.dataset.peSearch || '';
      const matchesSearch = !q || searchData.includes(q);
      const matchesStatus = (Folio.currentPeFilter === 'ALL') || (status === Folio.currentPeFilter);
      if (matchesSearch && matchesStatus) {
        r.style.display = '';
      } else {
        r.style.display = 'none';
      }
    });
  };

  /**
   * Settle Personal Expense Modal Workflows
   */
  Folio.openSettleExpenseModal = function (expenseId, itemDesc, amount) {
    const m = document.getElementById('settleExpenseModal');
    if (!m) return;
    const idInp = document.getElementById('settleExpenseId');
    const descEl = document.getElementById('settleExpenseDesc');
    const amtEl = document.getElementById('settleExpenseAmount');
    const dtInp = document.getElementById('settleDateInput');
    const refInp = document.getElementById('settleRefInput');
    const notesInp = document.getElementById('settleNotesInput');

    if (idInp) idInp.value = expenseId;
    if (descEl) descEl.textContent = itemDesc || 'Personal Drawing';
    if (amtEl) amtEl.textContent = SD_BANKING.formatINR(amount || 0);
    if (dtInp) dtInp.value = new Date().toISOString().split('T')[0];
    if (refInp) refInp.value = '';
    if (notesInp) notesInp.value = '';

    m.classList.remove('hidden');
    m.classList.add('flex');
    if (window.lucide) lucide.createIcons();
  };

  Folio.closeSettleExpenseModal = function () {
    const m = document.getElementById('settleExpenseModal');
    if (m) {
      m.classList.add('hidden');
      m.classList.remove('flex');
    }
  };

  Folio.submitSettleExpense = async function (e) {
    if (e) e.preventDefault();
    const idInp = document.getElementById('settleExpenseId');
    if (!idInp || !idInp.value) return;
    const expenseId = idInp.value;

    const mode = (document.getElementById('settlePaymentMode')?.value || 'CASH').toUpperCase();
    const settledAt = document.getElementById('settleDateInput')?.value || '';
    const ref = (document.getElementById('settleRefInput')?.value || '').trim();
    const notes = (document.getElementById('settleNotesInput')?.value || '').trim();

    const form = document.getElementById('settleExpenseForm');
    const submitBtn = form?.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="inline-block animate-spin mr-2">⏳</span> Settling...';
    }

    try {
      const res = await SD_BANKING.bankingFetch(`/banking/api/personal-expenses/${expenseId}/settle`, {
        method: 'POST',
        body: {
          settlement_mode: mode,
          settled_at: settledAt,
          settlement_ref: ref,
          settlement_notes: notes
        }
      });

      if (res && res.success !== false) {
        SD_BANKING.showToast(res.message || 'Personal expense marked as settled!', 'success');
        Folio.closeSettleExpenseModal();
        setTimeout(() => window.location.reload(), 700);
      } else {
        throw new Error((res && res.error) || 'Failed to settle drawing');
      }
    } catch (err) {
      SD_BANKING.showToast(err.message || 'Error settling drawing', 'error');
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Confirm Settlement';
      }
    }
  };

  /**
   * Re-open a settled personal drawing
   */
  Folio.unsettlePersonalExpense = async function (expenseId) {
    if (!confirm('Re-open this personal drawing back to active unsettled status?')) {
      return;
    }
    try {
      const res = await SD_BANKING.bankingFetch(`/banking/api/personal-expenses/${expenseId}/unsettle`, {
        method: 'POST'
      });
      if (res && res.success !== false) {
        SD_BANKING.showToast(res.message || 'Personal drawing re-opened to active status!', 'success');
        setTimeout(() => window.location.reload(), 700);
      } else {
        throw new Error((res && res.error) || 'Failed to re-open drawing');
      }
    } catch (err) {
      SD_BANKING.showToast(err.message || 'Error re-opening drawing', 'error');
    }
  };

  window.InvestorFolio = Folio;

  document.addEventListener('DOMContentLoaded', function () {
    Folio.initCalculations();
  });

})(window);
