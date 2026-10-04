/**
 * Global Button Guard & Concurrency Protection
 * Prevents multiple/repeated clicks on buttons across the entire website
 * while asynchronous requests (fetch / AJAX) or form submissions are in progress.
 */
(function() {
  'use strict';

  // Track active trigger button clicked by user
  let activeTriggerButton = null;
  let activeTriggerTime = 0;

  // Track buttons currently in locked/loading state: Button Element -> metadata object
  const lockedButtons = new Map();

  /**
   * Determine if an element should be exempt from locking
   */
  function isIgnoredButton(btn) {
    if (!btn || !(btn instanceof Element)) return true;
    if (btn.hasAttribute('data-no-block')) return true;
    // Exclude tabs, navigation pills, close modals, accordions
    if (btn.classList.contains('tab-btn') || btn.classList.contains('nav-link')) return true;
    if (btn.classList.contains('close') || btn.classList.contains('modal-close')) return true;
    if (btn.hasAttribute('data-bs-dismiss') || btn.hasAttribute('data-dismiss')) return true;
    if (btn.getAttribute('role') === 'tab') return true;
    return false;
  }

  /**
   * Lock a button into loading/disabled state
   */
  function lockButton(btn) {
    if (!btn || isIgnoredButton(btn) || lockedButtons.has(btn)) return;

    const originalHtml = btn.innerHTML;
    const originalDisabled = btn.disabled;
    const siblingButtons = [];

    // Find nearby sibling buttons in the same action group or form to prevent conflicting concurrent clicks
    const container = btn.closest('.cust-topbar-actions, .feed-card-actions, .pay-row-actions, .modal-footer, .posting-actions, .form-actions, td, form');
    if (container) {
      container.querySelectorAll('button:not([disabled]), input[type="submit"]:not([disabled])').forEach(b => {
        if (b !== btn && !isIgnoredButton(b)) {
          siblingButtons.push({ el: b, origDisabled: b.disabled });
          b.disabled = true;
          b.style.pointerEvents = 'none';
        }
      });
    }

    btn.disabled = true;
    btn.style.pointerEvents = 'none';
    btn.classList.add('btn-loading');

    // Add loading spinner without breaking layout
    if (!btn.querySelector('.fa-spinner, .lucide-loader, svg.animate-spin')) {
      const icon = btn.querySelector('i.fas, i.fa, i.far');
      if (icon) {
        icon.dataset.origClass = icon.className;
        icon.className = 'fas fa-spinner fa-spin me-1';
      } else {
        const span = document.createElement('span');
        span.className = 'btn-spinner-icon me-1';
        span.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ';
        btn.insertAdjacentElement('afterbegin', span);
      }
    }

    // Safety timeout: unlock automatically after 30 seconds if network hangs
    const timer = setTimeout(() => {
      unlockButton(btn);
    }, 30000);

    lockedButtons.set(btn, {
      originalHtml,
      originalDisabled,
      siblingButtons,
      timer,
      requestsCount: 1
    });
  }

  /**
   * Unlock a button and restore its previous state
   */
  function unlockButton(btn) {
    if (!btn) return;
    const record = lockedButtons.get(btn);
    if (!record) return;

    clearTimeout(record.timer);

    btn.disabled = record.originalDisabled;
    btn.style.pointerEvents = '';
    btn.classList.remove('btn-loading');
    btn.innerHTML = record.originalHtml;

    if (record.siblingButtons && Array.isArray(record.siblingButtons)) {
      record.siblingButtons.forEach(s => {
        if (s.el && document.body.contains(s.el)) {
          s.el.disabled = s.origDisabled;
          s.el.style.pointerEvents = '';
        }
      });
    }

    lockedButtons.delete(btn);
  }

  // 1. Capture-phase click interceptor to block duplicate/rapid spam clicks
  document.addEventListener('click', function(e) {
    const btn = e.target.closest('button, input[type="submit"], .btn, .neumorphic-btn, .posting-tool-btn, .posting-action-circle');
    if (!btn || isIgnoredButton(btn)) return;

    // Hard block if already locked or loading
    if (lockedButtons.has(btn) || btn.classList.contains('btn-loading') || btn.disabled) {
      e.preventDefault();
      e.stopImmediatePropagation();
      return false;
    }

    // Debounce rapid multi-clicks on the exact same button (< 450ms)
    const now = Date.now();
    if (btn === activeTriggerButton && (now - activeTriggerTime) < 450) {
      e.preventDefault();
      e.stopImmediatePropagation();
      return false;
    }

    activeTriggerButton = btn;
    activeTriggerTime = now;
  }, true);

  // 2. Intercept window.fetch globally to lock the active button during requests
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    let triggeringBtn = null;
    const now = Date.now();

    if (activeTriggerButton && (now - activeTriggerTime) < 600) {
      triggeringBtn = activeTriggerButton;
    } else if (document.activeElement && (document.activeElement.tagName === 'BUTTON' || (document.activeElement.tagName === 'INPUT' && document.activeElement.type === 'submit'))) {
      if (!isIgnoredButton(document.activeElement)) {
        triggeringBtn = document.activeElement;
      }
    }

    if (triggeringBtn) {
      if (lockedButtons.has(triggeringBtn)) {
        lockedButtons.get(triggeringBtn).requestsCount++;
      } else {
        lockButton(triggeringBtn);
      }
    }

    try {
      const response = await originalFetch.apply(this, args);
      // Preserve session expiry handler if 401
      if (response && response.status === 401 && !window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
      return response;
    } finally {
      if (triggeringBtn && lockedButtons.has(triggeringBtn)) {
        const record = lockedButtons.get(triggeringBtn);
        record.requestsCount--;
        if (record.requestsCount <= 0) {
          unlockButton(triggeringBtn);
        }
      }
    }
  };

  // 3. Intercept jQuery AJAX if present
  function setupJQueryAjaxInterceptor() {
    if (typeof jQuery !== 'undefined' && jQuery.fn && jQuery(document).ajaxSend) {
      jQuery(document).ajaxSend(function(event, jqXHR, settings) {
        let triggeringBtn = null;
        const now = Date.now();
        if (activeTriggerButton && (now - activeTriggerTime) < 600) {
          triggeringBtn = activeTriggerButton;
        } else if (document.activeElement && document.activeElement.tagName === 'BUTTON') {
          if (!isIgnoredButton(document.activeElement)) triggeringBtn = document.activeElement;
        }

        if (triggeringBtn) {
          jqXHR._triggeringBtn = triggeringBtn;
          if (lockedButtons.has(triggeringBtn)) {
            lockedButtons.get(triggeringBtn).requestsCount++;
          } else {
            lockButton(triggeringBtn);
          }
        }
      });

      jQuery(document).ajaxComplete(function(event, jqXHR, settings) {
        const triggeringBtn = jqXHR._triggeringBtn;
        if (triggeringBtn && lockedButtons.has(triggeringBtn)) {
          const record = lockedButtons.get(triggeringBtn);
          record.requestsCount--;
          if (record.requestsCount <= 0) {
            unlockButton(triggeringBtn);
          }
        }
      });
      return true;
    }
    return false;
  }

  // Set up jQuery AJAX when DOM is loaded (or immediately if available)
  if (!setupJQueryAjaxInterceptor()) {
    document.addEventListener('DOMContentLoaded', setupJQueryAjaxInterceptor);
  }

  // 4. Intercept standard form submissions
  document.addEventListener('submit', function(e) {
    const form = e.target;
    if (!form || form.tagName !== 'FORM') return;

    if (form.dataset.submitting === 'true') {
      e.preventDefault();
      e.stopImmediatePropagation();
      return false;
    }

    form.dataset.submitting = 'true';
    const submitBtns = form.querySelectorAll('button[type="submit"], input[type="submit"], button:not([type])');
    submitBtns.forEach(btn => lockButton(btn));

    // If JavaScript form handler cancelled submit via e.preventDefault() (e.g. form validation error), unlock
    setTimeout(() => {
      if (e.defaultPrevented) {
        delete form.dataset.submitting;
        submitBtns.forEach(btn => unlockButton(btn));
      }
    }, 150);
  }, true);

  // Expose global helpers
  window.lockButton = lockButton;
  window.unlockButton = unlockButton;
})();
