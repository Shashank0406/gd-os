/** Preview of a server charge. The API amount is the one that is stored. */

export function chargeRupees(hourlyRate, seconds) {
  if (seconds < 0) {
    throw new Error("Seconds cannot be negative")
  }
  const cents = rupeeCents(hourlyRate)
  const product = BigInt(cents) * BigInt(seconds)
  const divisor = 3600n
  const rounded = (product + divisor / 2n) / divisor
  return formatCents(rounded)
}

export function prepaidDue(hourlyRate, requestedSeconds, incrementSeconds, minimumSeconds) {
  const purchased = Math.max(roundUp(requestedSeconds, incrementSeconds), minimumSeconds)
  return chargeRupees(hourlyRate, purchased)
}

function roundUp(elapsedSeconds, incrementSeconds) {
  if (elapsedSeconds <= 0) {
    return 0
  }
  return Math.ceil(elapsedSeconds / incrementSeconds) * incrementSeconds
}

function rupeeCents(value) {
  const text = String(value)
  const negative = text.startsWith("-")
  const [whole, fraction = ""] = text.replace("-", "").split(".")
  const cents = BigInt(whole) * 100n + BigInt((fraction + "00").slice(0, 2))
  return negative ? -cents : cents
}

function formatCents(cents) {
  const negative = cents < 0n
  const absolute = negative ? -cents : cents
  const whole = absolute / 100n
  const fraction = (absolute % 100n).toString().padStart(2, "0")
  return `${negative ? "-" : ""}${whole}.${fraction}`
}
