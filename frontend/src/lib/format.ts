const moneyFormatter = new Intl.NumberFormat('en-GB', {
  style: 'currency',
  currency: 'PLN',
  maximumFractionDigits: 2,
})

const numberFormatter = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 3 })

export function money(value: string | number): string {
  return moneyFormatter.format(Number(value))
}

export function quantity(value: string | number): string {
  return numberFormatter.format(Number(value))
}

export function dateTime(value: string | null): string {
  if (!value) return 'Never'
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export function titleCase(value: string): string {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}
