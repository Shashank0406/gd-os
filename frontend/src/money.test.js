import assert from "node:assert/strict"
import test from "node:test"

import { chargeRupees, prepaidDue } from "./money.js"

test("a full hour stays the hourly rate", () => {
  assert.equal(chargeRupees("150.00", 3600), "150.00")
  assert.equal(chargeRupees("250.00", 3600), "250.00")
  assert.equal(chargeRupees("800.00", 3600), "800.00")
})

test("one minute rounds half up", () => {
  assert.equal(chargeRupees("150.00", 60), "2.50")
  assert.equal(chargeRupees("250.00", 60), "4.17")
  assert.equal(chargeRupees("800.00", 60), "13.33")
})

test("ninety minutes of simulator time is 1200 rupees", () => {
  assert.equal(chargeRupees("800.00", 5400), "1200.00")
})

test("prepaid preview uses the billing increment and minimum", () => {
  assert.equal(prepaidDue("150.00", 3600, 60, 60), "150.00")
  assert.equal(prepaidDue("150.00", 30, 60, 60), "2.50")
})
