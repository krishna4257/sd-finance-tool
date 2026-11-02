/**
 * SIVA DURGA FINANCE — VILLAGE GROUP BANK MODULE
 * Dynamic Waterfall Preview Calculator, Capital Allocations & Shareholding Engine
 */

(function (window) {
  'use strict';

  const GroupBank = {};

  /**
   * Live Waterfall Preview Calculator
   * Updates tier breakdown and partner distribution table in real time as admin types amount.
   */
  GroupBank.updateWaterfallPreview = function () {
    const inputEl = document.getElementById('waterfallWithdrawAmount');
    if (!inputEl) return;

    const amount = parseFloat(inputEl.value) || 0;
    const principalOwed = parseFloat(inputEl.dataset.principalOwed || 0);
    const interestOwed = parseFloat(inputEl.dataset.interestOwed || 0);

    // Collect current shareholders from data attribute or table
    let shareholders = [];
    const shareDataEl = document.getElementById('waterfallShareholdersData');
    if (shareDataEl && shareDataEl.value) {
      try {
        shareholders = JSON.parse(shareDataEl.value);
      } catch (e) {
        shareholders = [];
      }
    }

    const waterfall = SD_BANKING.calcWaterfall(amount, principalOwed, interestOwed, shareholders);

    // Update Tier Figures
    const tier1El = document.getElementById('wfTier1Amount');
    const tier2El = document.getElementById('wfTier2Amount');
    const tier3El = document.getElementById('wfTier3Amount');
    const remPrincipalEl = document.getElementById('wfRemainingPrincipal');
    const remInterestEl = document.getElementById('wfRemainingInterest');

    if (tier1El) tier1El.textContent = SD_BANKING.formatINR(waterfall.tier1Principal);
    if (tier2El) tier2El.textContent = SD_BANKING.formatINR(waterfall.tier2Interest);
    if (tier3El) tier3El.textContent = SD_BANKING.formatINR(waterfall.tier3Profit);
    if (remPrincipalEl) remPrincipalEl.textContent = SD_BANKING.formatINR(waterfall.remainingPrincipal);
    if (remInterestEl) remInterestEl.textContent = SD_BANKING.formatINR(waterfall.remainingInterest);

    // Render Shareholder Itemized Table
    const tableBody = document.getElementById('wfPartnerTableBody');
    if (tableBody) {
      if (!waterfall.distributions || waterfall.distributions.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="5" class="py-3 text-center text-xs text-slate-400">No shareholding partners configured</td></tr>`;
      } else {
        tableBody.innerHTML = waterfall.distributions.map(d => `
          <tr class="border-b border-slate-100 dark:border-slate-800 text-xs">
            <td class="py-2.5 font-semibold text-slate-900 dark:text-slate-100">${d.name} <span class="text-[10px] text-slate-400 font-mono">(${d.share_pct}%)</span></td>
            <td class="py-2.5 font-mono text-right text-slate-600 dark:text-slate-400">${SD_BANKING.formatINR(d.principal_share)}</td>
            <td class="py-2.5 font-mono text-right text-amber-600 dark:text-amber-400 font-medium">${SD_BANKING.formatINR(d.interest_share)}</td>
            <td class="py-2.5 font-mono text-right text-emerald-600 dark:text-emerald-400 font-medium">${SD_BANKING.formatINR(d.profit_share)}</td>
            <td class="py-2.5 font-mono text-right font-bold text-slate-900 dark:text-white">${SD_BANKING.formatINR(d.total_share)}</td>
          </tr>
        `).join('');
      }
    }
  };

  /**
   * Handle Waterfall Withdrawal Submission (PIN Protected)
   */
  GroupBank.handleWaterfallWithdrawal = async function (formEvent, groupId) {
    if (formEvent) formEvent.preventDefault();
    const form = formEvent ? formEvent.target : document.getElementById('waterfallWithdrawForm');
    if (!form) return;

    const amount = parseFloat(form.querySelector('[name="amount"]').value || 0);
    const paymentMode = form.querySelector('[name="payment_mode"]').value;
    const withdrawalDate = form.querySelector('[name="withdrawal_date"]').value;
    const notes = form.querySelector('[name="notes"]').value;

    if (amount <= 0) {
      SD_BANKING.showToast('Please enter an amount to withdraw', 'error');
      return;
    }

    try {
      const auth = await SD_BANKING.promptAdminPin({
        title: 'Authorize Group Waterfall Withdrawal',
        message: `Authorize distribution of ${SD_BANKING.formatINR(amount)} via ${paymentMode} across partners?`,
        actionLabel: 'Authorize Waterfall Payout'
      });

      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="inline-block animate-spin mr-2">⏳</span> Processing Waterfall...';
      }

      const res = await SD_BANKING.bankingFetch(`/banking/api/groups/${groupId}/withdraw-waterfall`, {
        method: 'POST',
        body: {
          amount: amount,
          payment_mode: paymentMode,
          withdrawal_date: withdrawalDate,
          notes: notes,
          pin: auth.pin
        }
      });

      if (res && res.success !== false) {
        SD_BANKING.showToast(`Waterfall withdrawal of ${SD_BANKING.formatINR(amount)} processed and credited to investors!`, 'success');
        setTimeout(() => window.location.reload(), 900);
      } else {
        throw new Error((res && res.error) || 'Waterfall withdrawal failed');
      }
    } catch (err) {
      if (err.message !== 'Verification cancelled') {
        SD_BANKING.showToast(err.message || 'Error processing withdrawal', 'error');
      }
    }
  };

  /**
   * Handle Deploy Capital into Village Group (Auto Injects into Group's Cashbag)
   */
  GroupBank.handleDeployCapital = async function (formEvent, groupId) {
    if (formEvent) formEvent.preventDefault();
    const form = formEvent ? formEvent.target : document.getElementById('deployCapitalForm');
    if (!form) return;

    const investorId = form.querySelector('[name="investor_id"]').value;
    const amount = parseFloat(form.querySelector('[name="amount"]').value || 0);
    const paymentMode = form.querySelector('[name="payment_mode"]').value;
    const allocationDate = form.querySelector('[name="allocation_date"]').value;
    const interestRate = parseFloat(form.querySelector('[name="interest_rate"]').value || 24.0);

    if (!investorId) {
      SD_BANKING.showToast('Please select a funding investor', 'error');
      return;
    }

    if (amount <= 0) {
      SD_BANKING.showToast('Please enter a valid deployment capital amount', 'error');
      return;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="inline-block animate-spin mr-2">⏳</span> Deploying Capital...';
    }

    try {
      const res = await SD_BANKING.bankingFetch(`/banking/api/groups/${groupId}/deploy-capital`, {
        method: 'POST',
        body: {
          investor_id: investorId,
          amount: amount,
          payment_mode: paymentMode,
          allocation_date: allocationDate,
          interest_rate: interestRate
        }
      });

      if (res && res.success !== false) {
        SD_BANKING.showToast(`Successfully deployed ${SD_BANKING.formatINR(amount)} into Group Bank!`, 'success');
        setTimeout(() => window.location.reload(), 800);
      } else {
        throw new Error((res && res.error) || 'Deployment failed');
      }
    } catch (err) {
      SD_BANKING.showToast(err.message || 'Error deploying capital', 'error');
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Confirm Capital Injection';
      }
    }
  };

  /**
   * Shareholding Breakdown Validator
   * Ensures that sum of share_pct entries equals exactly 100.000%
   */
  GroupBank.checkSharePercentages = function (containerSelector = '#shareholdingRows') {
    const container = document.querySelector(containerSelector);
    if (!container) return { total: 0, isValid: false };

    const inputs = container.querySelectorAll('.share-pct-input');
    let total = 0.0;
    inputs.forEach(inp => {
      const v = parseFloat(inp.value) || 0;
      total += v;
    });

    total = Math.round(total * 1000) / 1000;
    const isValid = total >= 99.99;

    const totalDisplay = document.getElementById('totalSharePctDisplay');
    const badge = document.getElementById('sharePctStatusBadge');

    if (totalDisplay) {
      totalDisplay.textContent = `${Math.round(total)}%`;
    }

    if (badge) {
      if (isValid) {
        badge.className = 'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700';
        badge.innerHTML = `<i data-lucide="check" class="w-3.5 h-3.5"></i> Valid (${Math.round(total)}%)`;
      } else {
        const diff = Math.round(100.0 - total);
        badge.className = 'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-300 dark:border-rose-700';
        badge.innerHTML = `<i data-lucide="alert-triangle" class="w-3.5 h-3.5"></i> Needs at least 100% (Short by ${diff}%)`;
      }
      if (window.lucide) lucide.createIcons();
    }

    return { total, isValid };
  };

  /**
   * Adds a new shareholder row to the table
   */
  GroupBank.addShareholderRow = function (containerId = 'shareholdingRows') {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Clone first row or build fresh row
    const template = document.getElementById('shareholderRowTemplate');
    if (template) {
      const clone = template.content.cloneNode(true);
      container.appendChild(clone);
    } else {
      const div = document.createElement('tr');
      div.className = 'border-b border-slate-100 dark:border-slate-800 group-share-row';
      div.innerHTML = `
        <td class="py-2.5">
          <select name="investor_id[]" class="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-amber-500">
            ${window.INVESTORS_OPTIONS_HTML || '<option value="">Select Investor</option>'}
          </select>
        </td>
        <td class="py-2.5 pl-3">
          <div class="relative">
            <input type="number" step="0.001" min="0" max="100" name="share_pct[]" placeholder="0.000"
              class="share-pct-input w-full text-xs text-right font-mono rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 pr-7 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-amber-500"
              oninput="GroupBank.checkSharePercentages('#${containerId}')">
            <span class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 text-xs font-mono">%</span>
          </div>
        </td>
        <td class="py-2.5 pl-2 text-right">
          <button type="button" onclick="this.closest('tr').remove(); GroupBank.checkSharePercentages('#${containerId}');" class="p-1.5 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors">
            <i data-lucide="trash-2" class="w-4 h-4"></i>
          </button>
        </td>
      `;
      container.appendChild(div);
    }

    if (window.lucide) lucide.createIcons();
    GroupBank.checkSharePercentages('#' + containerId);
  };

  /**
   * Save Edited Shares
   */
  GroupBank.handleSaveShares = async function (formEvent, groupId) {
    if (formEvent) formEvent.preventDefault();
    const form = formEvent ? formEvent.target : document.getElementById('editSharesForm');
    if (!form) return;

    const check = GroupBank.checkSharePercentages('#editSharesRows');
    if (!check.isValid) {
      SD_BANKING.showToast(`Total shareholdings must be at least 100% (currently ${check.total}%)`, 'error');
      return;
    }

    const rows = form.querySelectorAll('.group-share-row');
    const shares = [];
    rows.forEach(r => {
      const invSelect = r.querySelector('[name="investor_id[]"]');
      const pctInput = r.querySelector('[name="share_pct[]"]');
      if (invSelect && pctInput && invSelect.value) {
        shares.push({
          investor_id: invSelect.value,
          share_pct: parseFloat(pctInput.value) || 0
        });
      }
    });

    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="inline-block animate-spin mr-2">⏳</span> Updating Shares...';
    }

    try {
      const res = await SD_BANKING.bankingFetch(`/banking/api/groups/${groupId}/shares`, {
        method: 'POST',
        body: { shares: shares }
      });

      if (res && res.success !== false) {
        SD_BANKING.showToast('Investor ownership shares updated successfully!', 'success');
        setTimeout(() => window.location.reload(), 700);
      } else {
        throw new Error((res && res.error) || 'Failed to update shares');
      }
    } catch (err) {
      SD_BANKING.showToast(err.message || 'Error updating shares', 'error');
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Save Shares Breakdown';
      }
    }
  };

  window.GroupBank = GroupBank;

})(window);
