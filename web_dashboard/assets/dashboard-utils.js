/**
 * dashboard-utils.js
 * Shared utility functions: formatting, DOM helpers, error banner, theme.
 */

// ── HTML Escaping ──
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function getSafeDOMId(str) {
  return (str || '').replace(/[^a-zA-Z0-9_-]/g, '_');
}

// ── Date / Time Formatting ──
function formatTime(isoStr) {
  if (!isoStr) return '—';
  return new Date(isoStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatRelative(isoStr) {
  if (!isoStr) return '';
  const diff = Math.floor((Date.now() - new Date(isoStr)) / 1000);
  if (diff < 60) return diff + ' seconds ago';
  if (diff < 3600) return Math.floor(diff / 60) + ' minutes ago';
  if (diff < 86400) return Math.floor(diff / 3600) + ' hours ago';
  return Math.floor(diff / 86400) + ' days ago';
}

function formatDateTime(isoStr) {
  if (!isoStr) return '—';
  return new Date(isoStr).toLocaleString();
}

// ── Badge Renderers ──
function scoreBadge(score) {
  if (score === null || score === undefined) return '—';
  const cls = score >= 0.75 ? 'high' : score >= 0.60 ? 'mid' : 'low';
  return `<span class="score-badge score-badge--${cls}">${parseFloat(score).toFixed(2)}</span>`;
}

function statusBadge(status) {
  const s = status || 'none';
  return `<span class="status-badge status-badge--${escapeHtml(s)}">${escapeHtml(s)}</span>`;
}

// ── Live Status Banner ──
function setError(msg) {
  document.getElementById('live-dot').className = 'live-dot offline';
  document.getElementById('live-label').textContent = 'Offline';
  document.getElementById('error-msg').textContent = msg;
  document.getElementById('error-banner').classList.add('visible');
}

function clearError() {
  document.getElementById('live-dot').className = 'live-dot online';
  document.getElementById('live-label').textContent = 'Live · refreshes every 5s';
  document.getElementById('error-banner').classList.remove('visible');
}

// ── Admin Key (localStorage) ──
function saveAdminKey(val) {
  localStorage.setItem('admin_key', val);
}

function getAdminKey() {
  return localStorage.getItem('admin_key') || '';
}

// ── Theme Toggle ──
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const isDark = theme === 'dark';
  document.getElementById('theme-icon').textContent = isDark ? '🌙' : '☀️';
  document.getElementById('theme-label').textContent = isDark ? 'Dark' : 'Light';
  localStorage.setItem('theme', theme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  applyTheme(current === 'dark' ? 'light' : 'dark');
}
