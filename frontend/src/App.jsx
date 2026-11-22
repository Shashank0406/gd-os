import { useEffect, useMemo, useState } from "react"

import { api } from "./api.js"
import { prepaidDue } from "./money.js"

const TOKEN_KEY = "gd-os-staff-token"
const NAME_KEY = "gd-os-staff-name"
const GROUPS = [
  ["PC", "PCs"],
  ["PS5", "PS5"],
  ["RACING_SIMULATOR", "Racing sims"],
  ["ADMIN_WORKSTATION", "Cashier"],
]
const DURATIONS = [
  [1800, "30 min"],
  [3600, "1 hour"],
  [7200, "2 hours"],
  [10800, "3 hours"],
]
const METHODS = [
  ["CASH", "Cash"],
  ["UPI", "UPI"],
  ["CARD", "Card"],
]

export function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) || "")
  const [staffName, setStaffName] = useState(() => sessionStorage.getItem(NAME_KEY) || "")

  function signIn(nextToken, username) {
    sessionStorage.setItem(TOKEN_KEY, nextToken)
    sessionStorage.setItem(NAME_KEY, username)
    setToken(nextToken)
    setStaffName(username)
  }

  function signOut() {
    sessionStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(NAME_KEY)
    setToken("")
    setStaffName("")
  }

  if (!token) {
    return <Login onSuccess={signIn} />
  }
  return <Desk token={token} staffName={staffName} onSignOut={signOut} onUnauthorized={signOut} />
}

function Login({ onSuccess }) {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError("")
    try {
      const body = await api("/auth/login", { method: "POST", body: { username, password } })
      onSuccess(body.access_token, body.username)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login">
      <form onSubmit={submit}>
        <p className="eyebrow">Gamers District</p>
        <h1>Cashier</h1>
        <label>
          Username
          <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
          />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <button type="submit" disabled={busy || !username || !password}>
          Sign in
        </button>
      </form>
    </main>
  )
}

function Desk({ token, staffName, onSignOut, onUnauthorized }) {
  const [stations, setStations] = useState([])
  const [sessions, setSessions] = useState([])
  const [pricing, setPricing] = useState({ plans: [], packages: [] })
  const [selectedCode, setSelectedCode] = useState("")
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [receipt, setReceipt] = useState(null)
  const [takings, setTakings] = useState(null)
  const [utilisation, setUtilisation] = useState(null)
  const [reservations, setReservations] = useState([])
  const [role, setRole] = useState("")

  async function reload() {
    try {
      const [nextStations, nextSessions, nextPricing, nextTakings, nextReservations, nextUse] = await Promise.all([
        api("/stations", { token }),
        api("/sessions/active", { token }),
        api("/pricing", { token }),
        api("/reports/takings", { token }),
        api("/reservations", { token }),
        api("/reports/utilisation", { token }),
      ])
      setStations(nextStations)
      setSessions(nextSessions)
      setPricing(nextPricing)
      setTakings(nextTakings)
      setReservations(nextReservations)
      setUtilisation(nextUse)
      setError("")
    } catch (err) {
      if (err.status === 401) {
        onUnauthorized()
        return
      }
      setError(err.message)
    }
  }

  useEffect(() => {
    let stopped = false
    api("/auth/me", { token })
      .then((me) => {
        if (!stopped) {
          setRole(me.role)
        }
      })
      .catch((err) => {
        if (err.status === 401) {
          onUnauthorized()
        }
      })
    reload()
    const timer = setInterval(reload, 10000)
    return () => {
      stopped = true
      clearInterval(timer)
    }
  }, [token])

  const canManage = role === "SUPER_ADMIN" || role === "MANAGER"
  const canPrice = role === "SUPER_ADMIN"

  const selected = stations.find((station) => station.code === selectedCode) || null
  const active = sessions.find((session) => session.station_code === selectedCode) || null

  return (
    <main className="desk">
      <section className="floor">
        <div className="top">
          <div>
            <p className="eyebrow">Gamers District</p>
            <h1>Floor</h1>
            {takings ? <p className="takings">{takingsLine(takings)}</p> : null}
            {utilisation ? <p className="takings">Used today {formatUse(utilisation.occupied_seconds)}</p> : null}
          </div>
          <div>
            <span>{staffName}</span>{" "}
            <button className="secondary" type="button" onClick={onSignOut}>
              Sign out
            </button>
          </div>
        </div>
        {error ? <p className="error">{error}</p> : null}
        {GROUPS.map(([deviceType, label]) => {
          const rows = stations.filter((station) => station.device_type === deviceType)
          if (rows.length === 0) {
            return null
          }
          return (
            <div className="group" key={deviceType}>
              <h2>{label}</h2>
              <div className="tiles">
                {rows.map((station) => (
                  <button
                    key={station.code}
                    type="button"
                    className={`tile ${station.status} ${station.code === selectedCode ? "selected" : ""}`}
                    disabled={!station.is_billable}
                    onClick={() => {
                      setSelectedCode(station.code)
                      setNotice("")
                      setReceipt(null)
                    }}
                  >
                    <strong>{station.code}</strong>
                    <small>{stationLabel(station)}</small>
                  </button>
                ))}
              </div>
            </div>
          )
        })}
      </section>
      <section className="panel">
        {!selected ? <p>Select a station.</p> : null}
        {selected && !selected.is_billable ? <p>{selected.code} is the cashier workstation. It is not billed.</p> : null}
        {selected && selected.is_billable && active ? (
          <SessionPanel
            token={token}
            session={active}
            onChanged={reload}
            onUnauthorized={onUnauthorized}
            onNotice={setNotice}
            onReceipt={setReceipt}
            utilisation={utilisation}
          />
        ) : null}
        {selected && selected.is_billable && !active && selected.status === "AVAILABLE" ? (
          <StartPanel
            token={token}
            station={selected}
            pricing={pricing}
            reservations={reservations.filter((item) => item.station_code === selected.code)}
            onStarted={reload}
            onUnauthorized={onUnauthorized}
            onNotice={setNotice}
            utilisation={utilisation}
          />
        ) : null}
        {selected && selected.is_billable && !active && canManage ? (
          <StatusControls
            token={token}
            station={selected}
            onChanged={reload}
            onUnauthorized={onUnauthorized}
          />
        ) : null}
        {selected && selected.is_billable && !active && selected.status !== "AVAILABLE" ? (
          <p>
            {selected.code} is {selected.status.replaceAll("_", " ").toLowerCase()}.
            {selected.maintenance_reason ? ` ${selected.maintenance_reason}` : ""}
          </p>
        ) : null}
        {selected && selected.is_billable && canPrice ? (
          <SchedulePanel
            token={token}
            station={selected}
            pricing={pricing}
            onChanged={reload}
            onUnauthorized={onUnauthorized}
          />
        ) : null}
        {receipt ? <Receipt slip={receipt} /> : null}
        {notice ? <div className="receipt">{notice}</div> : null}
      </section>
    </main>
  )
}

function StartPanel({ token, station, pricing, reservations, utilisation, onStarted, onUnauthorized, onNotice }) {
  const [who, setWho] = useState("guest")
  const [guestLabel, setGuestLabel] = useState("")
  const [mobile, setMobile] = useState("")
  const [customer, setCustomer] = useState(null)
  const [walkInName, setWalkInName] = useState("")
  const [mode, setMode] = useState("POSTPAID")
  const [packageCode, setPackageCode] = useState("")
  const [duration, setDuration] = useState(3600)
  const [method, setMethod] = useState("CASH")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [holdName, setHoldName] = useState("")

  const plan = useMemo(() => planFor(pricing.plans, station), [pricing.plans, station])
  const packages = pricing.packages.filter((item) => item.device_type === station.device_type && item.is_active)
  const usesPackage = mode === "PACKAGE_NOW" || mode === "PACKAGE_LATER"
  const dueNow =
    mode === "PREPAID" && plan
      ? prepaidDue(shownRate(plan), duration, plan.billing_increment_seconds, plan.minimum_duration_seconds)
      : mode === "PACKAGE_NOW"
        ? packages.find((item) => item.code === packageCode)?.price_rupees || ""
        : "0.00"

  useEffect(() => {
    setGuestLabel("")
    setMobile("")
    setCustomer(null)
    setWalkInName("")
    setMode("POSTPAID")
    setPackageCode(packages[0]?.code || "")
    setError("")
  }, [station.code])

  async function findCustomer() {
    setError("")
    setCustomer(null)
    try {
      const found = await api(`/customers/search?mobile=${encodeURIComponent(mobile)}`, { token })
      setCustomer(found)
    } catch (err) {
      if (err.status === 401) {
        onUnauthorized()
        return
      }
      setError(err.status === 404 ? "No account for that mobile. Add a walk-in below." : err.message)
    }
  }

  async function createWalkIn() {
    setBusy(true)
    setError("")
    try {
      const created = await api("/customers", {
        method: "POST",
        token,
        body: { display_name: walkInName, mobile },
      })
      setCustomer(created)
    } catch (err) {
      if (err.status === 401) {
        onUnauthorized()
      } else {
        setError(err.message)
      }
    } finally {
      setBusy(false)
    }
  }

  async function start(event) {
    event.preventDefault()
    setBusy(true)
    setError("")
    const billingMode = mode === "PACKAGE_LATER" ? "POSTPAID" : mode === "PACKAGE_NOW" ? "PREPAID" : mode
    const body = {
      station_code: station.code,
      billing_mode: billingMode,
      payment_method: Number(dueNow) > 0 ? method : null,
    }
    if (who === "guest") {
      body.guest_label = guestLabel
    } else if (customer) {
      body.customer_id = customer.id
    }
    if (usesPackage) {
      body.package_code = packageCode
    }
    if (mode === "PREPAID") {
      body.duration_seconds = duration
    }
    const held = coveringReservation(reservations)
    if (held) {
      body.reservation_id = held.id
    }
    try {
      const started = await api("/sessions", { method: "POST", token, body })
      onNotice(`${station.code} started. Paid ₹${started.amount_paid_rupees}. Rate ₹${started.hourly_rate_rupees}/hour.`)
      await onStarted()
    } catch (err) {
      if (err.status === 401) {
        onUnauthorized()
      } else {
        setError(err.message)
      }
    } finally {
      setBusy(false)
    }
  }

  async function reserveNow() {
    setBusy(true)
    setError("")
    try {
      const booked = await api("/reservations", {
        method: "POST",
        token,
        body: {
          station_code: station.code,
          guest_label: holdName,
          starts_at: new Date().toISOString(),
          duration_seconds: 1800,
        },
      })
      onNotice(`${station.code} reserved for ${booked.holder_name} until ${booked.ends_at_local}.`)
      setHoldName("")
      await onStarted()
    } catch (err) {
      if (err.status === 401) {
        onUnauthorized()
      } else {
        setError(err.message)
      }
    } finally {
      setBusy(false)
    }
  }

  async function cancelHold(reservation) {
    setBusy(true)
    setError("")
    try {
      await api(`/reservations/${reservation.id}/cancel`, { method: "POST", token })
      onNotice(`${station.code} reservation for ${reservation.holder_name} cancelled.`)
      await onStarted()
    } catch (err) {
      if (err.status === 401) {
        onUnauthorized()
      } else {
        setError(err.message)
      }
    } finally {
      setBusy(false)
    }
  }

  const held = coveringReservation(reservations)

  return (
    <form className="stack" onSubmit={start}>
      <div>
        <p className="eyebrow">{station.code}</p>
        <h2>Start session</h2>
        <p>
          {plan ? `₹${shownRate(plan)} / hour` : "No hourly price"}
          {plan?.effective_label ? ` · ${plan.effective_label}` : ""}
        </p>
        <p>Used today {formatUse(usedSeconds(utilisation, station.code))}</p>
        {held ? <p>Reserved now for {held.holder_name}.</p> : null}
      </div>
      <label>
        Hold for
        <input value={holdName} onChange={(event) => setHoldName(event.target.value)} />
      </label>
      <button className="secondary" type="button" onClick={reserveNow} disabled={busy || !holdName.trim()}>
        Reserve 30 min from now
      </button>
      {reservations.map((reservation) => (
        <p key={reservation.id}>
          {reservation.holder_name} · {reservation.starts_at_local.slice(11, 16)}–{reservation.ends_at_local.slice(11, 16)}{" "}
          <button className="secondary" type="button" onClick={() => cancelHold(reservation)} disabled={busy}>
            Cancel
          </button>
        </p>
      ))}
      <div className="choices">
        <button type="button" className={who === "guest" ? "selected" : ""} onClick={() => setWho("guest")}>
          Guest
        </button>
        <button type="button" className={who === "customer" ? "selected" : ""} onClick={() => setWho("customer")}>
          Customer
        </button>
      </div>
      {who === "guest" ? (
        <label>
          Guest name
          <input value={guestLabel} onChange={(event) => setGuestLabel(event.target.value)} />
        </label>
      ) : (
        <>
          <label>
            Mobile
            <input value={mobile} onChange={(event) => setMobile(event.target.value)} inputMode="numeric" />
          </label>
          <button className="secondary" type="button" onClick={findCustomer} disabled={mobile.length < 10}>
            Find customer
          </button>
          {customer ? <p>{customer.display_name}</p> : null}
          {!customer ? (
            <>
              <label>
                Walk-in name
                <input value={walkInName} onChange={(event) => setWalkInName(event.target.value)} />
              </label>
              <button className="secondary" type="button" onClick={createWalkIn} disabled={busy || !walkInName || mobile.length < 10}>
                Save walk-in
              </button>
            </>
          ) : null}
        </>
      )}
      <div className="choices">
        <button type="button" className={mode === "POSTPAID" ? "selected" : ""} onClick={() => setMode("POSTPAID")}>
          Postpaid
        </button>
        <button type="button" className={mode === "PREPAID" ? "selected" : ""} onClick={() => setMode("PREPAID")}>
          Prepaid
        </button>
        {packages.length > 0 ? (
          <>
            <button type="button" className={mode === "PACKAGE_NOW" ? "selected" : ""} onClick={() => setMode("PACKAGE_NOW")}>
              Package now
            </button>
            <button type="button" className={mode === "PACKAGE_LATER" ? "selected" : ""} onClick={() => setMode("PACKAGE_LATER")}>
              Package later
            </button>
          </>
        ) : null}
        <button type="button" className={mode === "FREE_PLAY" ? "selected" : ""} onClick={() => setMode("FREE_PLAY")}>
          Free
        </button>
      </div>
      {mode === "PREPAID" ? (
        <label>
          Time
          <select value={duration} onChange={(event) => setDuration(Number(event.target.value))}>
            {DURATIONS.map(([seconds, label]) => (
              <option key={seconds} value={seconds}>
                {label}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {usesPackage ? (
        <label>
          Package
          <select value={packageCode} onChange={(event) => setPackageCode(event.target.value)}>
            {packages.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name} · ₹{item.price_rupees}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {Number(dueNow) > 0 ? (
        <>
          <p className="money">Due now ₹{dueNow}</p>
          <MethodPicker method={method} onChange={setMethod} />
        </>
      ) : (
        <p>Collected at the end, from the price saved when this session starts.</p>
      )}
      {error ? <p className="error">{error}</p> : null}
      <button type="submit" disabled={busy || (who === "guest" ? !guestLabel.trim() : !customer) || (usesPackage && !packageCode)}>
        Start
      </button>
    </form>
  )
}

function StatusControls({ token, station, onChanged, onUnauthorized }) {
  const [reason, setReason] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const out = station.status === "MAINTENANCE" || station.status === "DISABLED"

  useEffect(() => {
    setReason("")
    setError("")
  }, [station.code, station.status])

  async function change(status) {
    setBusy(true)
    setError("")
    try {
      await api(`/stations/${station.code}/status`, {
        method: "POST",
        token,
        body: status === "AVAILABLE" ? { status } : { status, reason },
      })
      await onChanged()
    } catch (err) {
      if (err.status === 401) {
        onUnauthorized()
        return
      }
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (station.status === "IN_SESSION") {
    return null
  }
  if (out) {
    return (
      <div className="stack">
        <button type="button" disabled={busy} onClick={() => change("AVAILABLE")}>
          Return to floor
        </button>
        {error ? <p className="error">{error}</p> : null}
      </div>
    )
  }
  if (station.status !== "AVAILABLE") {
    return null
  }
  return (
    <div className="stack">
      <label>
        Reason
        <input value={reason} onChange={(event) => setReason(event.target.value)} />
      </label>
      <div className="choices">
        <button type="button" disabled={busy || !reason.trim()} onClick={() => change("MAINTENANCE")}>
          Maintenance
        </button>
        <button type="button" disabled={busy || !reason.trim()} onClick={() => change("DISABLED")}>
          Disable
        </button>
      </div>
      {error ? <p className="error">{error}</p> : null}
    </div>
  )
}

function SchedulePanel({ token, station, pricing, onChanged, onUnauthorized }) {
  const plan = planFor(pricing.plans, station)
  const schedules = (pricing.schedules || []).filter((item) => item.pricing_plan_id === plan?.id)
  const [label, setLabel] = useState("Weekday peak")
  const [days, setDays] = useState("1,2,3,4,5")
  const [start, setStart] = useState("18:00")
  const [end, setEnd] = useState("23:00")
  const [rate, setRate] = useState("200.00")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  async function addSchedule(event) {
    event.preventDefault()
    if (!plan) {
      return
    }
    setBusy(true)
    setError("")
    try {
      await api(`/pricing/plans/${plan.id}/schedules`, {
        method: "POST",
        token,
        body: {
          label,
          days_of_week: days.split(",").map((day) => Number(day)),
          start_local_time: start,
          end_local_time: end,
          hourly_rate_rupees: rate,
        },
      })
      await onChanged()
    } catch (err) {
      if (err.status === 401) {
        onUnauthorized()
        return
      }
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function deactivate(schedule) {
    setBusy(true)
    setError("")
    try {
      await api(`/pricing/schedules/${schedule.id}/deactivate`, { method: "POST", token })
      await onChanged()
    } catch (err) {
      if (err.status === 401) {
        onUnauthorized()
        return
      }
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (!plan) {
    return null
  }
  return (
    <form className="stack" onSubmit={addSchedule}>
      <p className="eyebrow">Peak rate</p>
      <label>
        Name
        <input value={label} onChange={(event) => setLabel(event.target.value)} />
      </label>
      <div className="choices">
        {[
          ["1,2,3,4,5", "Weekdays"],
          ["6,7", "Weekend"],
          ["1,2,3,4,5,6,7", "Every day"],
        ].map(([value, name]) => (
          <button key={value} type="button" className={days === value ? "selected" : ""} onClick={() => setDays(value)}>
            {name}
          </button>
        ))}
      </div>
      <label>
        From
        <input type="time" value={start} onChange={(event) => setStart(event.target.value)} />
      </label>
      <label>
        Until
        <input type="time" value={end} onChange={(event) => setEnd(event.target.value)} />
      </label>
      <label>
        Hourly rate
        <input value={rate} onChange={(event) => setRate(event.target.value)} />
      </label>
      <button type="submit" disabled={busy || !label.trim() || !rate.trim()}>
        Save rate window
      </button>
      {schedules.map((schedule) => (
        <p key={schedule.id}>
          {schedule.label} · {schedule.start_local_time}–{schedule.end_local_time} · ₹{schedule.hourly_rate_rupees}{" "}
          <button className="secondary" type="button" disabled={busy} onClick={() => deactivate(schedule)}>
            Remove
          </button>
        </p>
      ))}
      {error ? <p className="error">{error}</p> : null}
    </form>
  )
}

function Receipt({ slip }) {
  return (
    <div className="receipt">
      <p className="eyebrow">Receipt</p>
      <p>
        {slip.station_code} · {slip.holder_name}
      </p>
      <p>
        {slip.started_at_local.slice(11, 16)}–{slip.ended_at_local.slice(11, 16)} · ₹{slip.hourly_rate_rupees}/hour
      </p>
      {slip.payments.map((payment, index) => (
        <p key={`${payment.method}-${index}`}>
          {payment.method} ₹{payment.amount_rupees}
        </p>
      ))}
      <p className="money">₹{slip.final_amount_rupees}</p>
    </div>
  )
}

function SessionPanel({ token, session, onChanged, onUnauthorized, onNotice, onReceipt, utilisation }) {
  const [due, setDue] = useState(null)
  const [extendFor, setExtendFor] = useState(1800)
  const [method, setMethod] = useState("CASH")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [elapsed, setElapsed] = useState("")

  useEffect(() => {
    const tick = () => setElapsed(formatElapsed(session.started_at_utc))
    tick()
    const timer = setInterval(tick, 1000)
    return () => clearInterval(timer)
  }, [session.started_at_utc])

  async function loadDue() {
    try {
      const quote = await api(`/sessions/${session.id}/due`, { token })
      setDue(quote)
    } catch (err) {
      if (err.status === 401) {
        onUnauthorized()
      }
    }
  }

  useEffect(() => {
    loadDue()
    const timer = setInterval(loadDue, 5000)
    return () => clearInterval(timer)
  }, [session.id, token])

  const extensionDue =
    session.billing_mode === "PREPAID" ? prepaidDue(session.hourly_rate_rupees, extendFor, 60, 0) : "0.00"

  async function extendSession() {
    setBusy(true)
    setError("")
    try {
      const updated = await api(`/sessions/${session.id}/extend`, {
        method: "POST",
        token,
        body: {
          duration_seconds: extendFor,
          payment_method: Number(extensionDue) > 0 ? method : null,
        },
      })
      onNotice(`Added time on ${session.station_code}. Paid ₹${updated.amount_paid_rupees}.`)
      await onChanged()
    } catch (err) {
      if (err.status === 401) {
        onUnauthorized()
      } else {
        setError(err.message)
      }
    } finally {
      setBusy(false)
    }
  }

  async function endSession() {
    setBusy(true)
    setError("")
    try {
      const needsPayment = due && Number(due.balance_rupees) > 0
      await api(`/sessions/${session.id}/end`, {
        method: "POST",
        token,
        body: { payment_method: needsPayment ? method : null },
      })
      const slip = await api(`/sessions/${session.id}/receipt`, { token })
      onReceipt(slip)
      await onChanged()
    } catch (err) {
      if (err.status === 401) {
        onUnauthorized()
      } else {
        setError(err.message)
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="stack">
      <div>
        <p className="eyebrow">{session.station_code}</p>
        <h2>{session.billing_mode.replaceAll("_", " ")}</h2>
        <p>
          {elapsed} · ₹{session.hourly_rate_rupees}/hour
          {session.package_code ? ` · ${session.package_code}` : ""}
        </p>
        <p>Used today {formatUse(usedSeconds(utilisation, session.station_code))}</p>
      </div>
      {due ? (
        <p className="money">
          Due ₹{due.balance_rupees}
          <small> of ₹{due.final_amount_rupees}</small>
        </p>
      ) : null}
      <label>
        Add time
        <select value={extendFor} onChange={(event) => setExtendFor(Number(event.target.value))}>
          <option value={1800}>30 min{session.billing_mode === "PREPAID" ? ` · ₹${prepaidDue(session.hourly_rate_rupees, 1800, 60, 0)}` : ""}</option>
          <option value={3600}>1 hour{session.billing_mode === "PREPAID" ? ` · ₹${prepaidDue(session.hourly_rate_rupees, 3600, 60, 0)}` : ""}</option>
        </select>
      </label>
      {Number(extensionDue) > 0 || (due && Number(due.balance_rupees) > 0) ? (
        <MethodPicker method={method} onChange={setMethod} />
      ) : null}
      {error ? <p className="error">{error}</p> : null}
      <button className="secondary" type="button" onClick={extendSession} disabled={busy}>
        {Number(extensionDue) > 0 ? `Add time · ₹${extensionDue}` : "Add time"}
      </button>
      <button type="button" onClick={endSession} disabled={busy || !due}>
        {due && Number(due.balance_rupees) > 0 ? `End and take ₹${due.balance_rupees}` : "End session"}
      </button>
    </div>
  )
}

function MethodPicker({ method, onChange }) {
  return (
    <div className="choices">
      {METHODS.map(([value, label]) => (
        <button key={value} type="button" className={method === value ? "selected" : ""} onClick={() => onChange(value)}>
          {label}
        </button>
      ))}
    </div>
  )
}

function coveringReservation(reservations) {
  const now = Date.now()
  return reservations.find((item) => Date.parse(item.starts_at_utc) <= now && now < Date.parse(item.ends_at_utc))
}

function usedSeconds(utilisation, stationCode) {
  const row = utilisation?.stations?.find((item) => item.station_code === stationCode)
  return row ? row.occupied_seconds : 0
}

function formatUse(seconds) {
  const total = Math.max(0, seconds || 0)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const rest = total % 60
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  return `${minutes}m ${String(rest).padStart(2, "0")}s`
}

function takingsLine(takings) {
  const amounts = Object.fromEntries(takings.by_method.map((item) => [item.method, item.amount_rupees]))
  return `Today ₹${takings.total_rupees} · Cash ₹${amounts.CASH} · UPI ₹${amounts.UPI} · Card ₹${amounts.CARD}`
}

function stationLabel(station) {
  const status = station.is_billable ? station.status.replaceAll("_", " ") : "Not billed"
  if (station.agent_desired === "UNPAIRED") {
    return `${status} · No agent`
  }
  if (station.agent_desired === "LOCK") {
    return `${status} · Lock`
  }
  if (station.agent_desired === "UNLOCK") {
    return `${status} · Unlock`
  }
  return status
}

function shownRate(plan) {
  return plan.effective_hourly_rate_rupees || plan.hourly_rate_rupees
}

function planFor(plans, station) {
  const override = plans.find((plan) => plan.station_id === station.id && plan.is_active)
  if (override) {
    return override
  }
  return plans.find((plan) => plan.device_type === station.device_type && !plan.station_id && plan.is_active) || null
}

function formatElapsed(startedAtUtc) {
  const seconds = Math.max(0, Math.floor((Date.now() - Date.parse(startedAtUtc)) / 1000))
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const rest = seconds % 60
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  return `${minutes}m ${String(rest).padStart(2, "0")}s`
}
