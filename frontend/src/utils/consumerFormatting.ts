// @ts-nocheck
export function formatPercent(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return '0%'
  }
  return `${Math.round(numeric * 100)}%`
}

export function translate(t, key, fallback, params = {}) {
  if (typeof t !== 'function') {
    return fallback
  }
  return t(key, params)
}