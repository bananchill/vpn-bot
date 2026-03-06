export function calcProgressPercent(current, max) {
  if (!max) return 0
  return Math.min(100, Math.round((current / max) * 100))
}

export function formatExpiryDate(validUntil) {
  if (!validUntil) return ''
  return new Date(validUntil).toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export function checkIsExpired(promo) {
  if (promo.is_expired) return true
  if (!promo.valid_until) return false
  return new Date(promo.valid_until) < new Date()
}

export function getStatusInfo(promo) {
  const expired = checkIsExpired(promo)
  if (expired) return { label: 'Истёк', bg: '#fff3e0', color: '#e65100' }
  if (!promo.is_active) return { label: 'Неактивен', bg: '#fce4ec', color: '#c62828' }
  return { label: 'Активен', bg: '#e8f5e9', color: '#2e7d32' }
}
