/* ============================================
   CHIT FUND — THEME TOGGLE SYSTEM
   Dark/Light mode with localStorage persistence
   ============================================ */

(function () {
  'use strict';

  const STORAGE_KEY = 'sd-theme';

  /** Read saved preference, fallback to system, fallback to light */
  function getSavedTheme() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'dark' || saved === 'light') return saved;
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
    return 'light';
  }

  /** Apply the theme class to <html> and update toggle icons */
  function applyTheme(theme) {
    const html = document.documentElement;
    if (theme === 'dark') {
      html.classList.add('dark');
    } else {
      html.classList.remove('dark');
    }
    localStorage.setItem(STORAGE_KEY, theme);
    updateToggleIcons(theme);
  }

  /** Show sun in dark mode, moon in light mode */
  function updateToggleIcons(theme) {
    const sunIcon = document.getElementById('themeIconSun');
    const moonIcon = document.getElementById('themeIconMoon');
    if (!sunIcon || !moonIcon) return;

    if (theme === 'dark') {
      sunIcon.style.opacity = '1';
      sunIcon.style.transform = 'rotate(0deg) scale(1)';
      moonIcon.style.opacity = '0';
      moonIcon.style.transform = 'rotate(-90deg) scale(0.5)';
    } else {
      sunIcon.style.opacity = '0';
      sunIcon.style.transform = 'rotate(90deg) scale(0.5)';
      moonIcon.style.opacity = '1';
      moonIcon.style.transform = 'rotate(0deg) scale(1)';
    }
  }

  /** Toggle between dark and light */
  function toggleTheme() {
    const current = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
  }

  /* ── INIT: apply theme ASAP (also done inline in <head> to prevent FOUC) ── */
  applyTheme(getSavedTheme());

  /* ── Bind toggle button after DOM ready ── */
  document.addEventListener('DOMContentLoaded', function () {
    const btn = document.getElementById('themeToggleBtn');
    if (btn) btn.addEventListener('click', toggleTheme);
    // Re-apply to ensure icons are correct after DOM paints
    updateToggleIcons(getSavedTheme());
  });

  /* ── Listen for system preference changes ── */
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
      if (!localStorage.getItem(STORAGE_KEY)) {
        applyTheme(e.matches ? 'dark' : 'light');
      }
    });
  }

  // Expose for inline usage
  window.chitToggleTheme = toggleTheme;
})();
