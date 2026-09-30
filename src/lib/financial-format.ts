export function formatMoney(amountMinor: number, currency = "INR") {
  const formatter = new Intl.NumberFormat("en-IN", { style: "currency", currency })
  return formatter.format(amountMinor / 10 ** (formatter.resolvedOptions().maximumFractionDigits ?? 2))
}

export function readableLabel(value: string) {
  return value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase())
}
