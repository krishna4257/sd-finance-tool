/**
 * SD Finance: Dynamic Unread Chat Badge Controller
 * File: SD_Accounting_Tool/static/js/chat_badge.js
 * 
 * Automatically synchronizes unread inbox badges across sidebar and header.
 */

(function () {
  'use strict';

  let pollInterval = null;

  async function updateChatBadge() {
    try {
      const resp = await fetch('/api/v1/chat/unread_count', {
        headers: { 'Accept': 'application/json' },
        cache: 'no-store'
      });
      if (!resp.ok) return;

      const data = await resp.json();
      if (!data || !data.success) return;

      const count = parseInt(data.unread_count || 0, 10);
      const navBadge = document.getElementById('nav-chat-badge');
      const headerBadge = document.getElementById('headerChatBadge');

      const badgeText = count > 99 ? '99+' : count.toString();
      const isVisible = count > 0;

      if (navBadge) {
        navBadge.textContent = badgeText;
        navBadge.style.display = isVisible ? 'inline-block' : 'none';
      }

      if (headerBadge) {
        headerBadge.textContent = badgeText;
        headerBadge.style.display = isVisible ? 'flex' : 'none';
      }
    } catch (e) {
      // Non-blocking silent catch
    }
  }

  // Expose globally
  window.updateChatBadge = updateChatBadge;

  document.addEventListener('DOMContentLoaded', function () {
    // Immediate initial sync
    updateChatBadge();

    // Periodic 4-second synchronization
    if (!pollInterval) {
      pollInterval = setInterval(updateChatBadge, 4000);
    }
  });

  // Re-sync when tab becomes visible
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) {
      updateChatBadge();
    }
  });
})();
