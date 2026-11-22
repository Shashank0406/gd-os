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
  const [takings, setTakings] = useState(null)

  async function reload() {
    try {
      const [nextStations, nextSessions, nextPricing, nextTakings] = await Promise.all([
        api("/stations", { token }),
        api("/sessions/active", { token }),
        api("/pricing", { token }),
        api("/reports/takings", { token }),
      ])
      setStations(nextStations)
      setSessions(nextSessions)
      setPricing(nextPricing)
      setTakings(nextTakings)
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
    reload()
    const timer = setInterval(reload, 10000)
    return () => clearInterval(timer)
  }, [token])

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
          />
        ) : null}
        {selected && selected.is_billable && !active && selected.status === "AVAILABLE" ? (
          <StartPanel
            token={token}
            station={selected}
            pricing={pricing}
            onStarted={reload}
            onUnauthorized={onUnauthorized}
            onNotice={setNotice}
          />
        ) : null}
        {selected && selected.is_billable && !active && selected.status !== "AVAILABLE" ? (
          <p>{selected.code} is {selected.status.replaceAll("_", " ").toLowerCase()}.</p>
        ) : null}
        {notice ? <div className="receipt">{notice}</div> : null}
      </section>
    </main>
  )
}

function StartPanel({ token, station, pricing, onStarted, onUnauthorized, onNotice }) {
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

  const plan = useMemo(() => planFor(pricing.plans, station), [pricing.plans, station])
  const packages = pricing.packages.filter((item) => item.device_type === station.device_type && item.is_active)
  const usesPackage = mode === "PACKAGE_NOW" || mode === "PACKAGE_LATER"
  const dueNow =
    mode === "PREPAID" && plan
      ? prepaidDue(plan.hourly_rate_rupees, duration, plan.billing_increment_seconds, plan.minimum_duration_seconds)
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

  return (
    <form className="stack" onSubmit={start}>
      <div>
        <p className="eyebrow">{station.code}</p>
        <h2>Start session</h2>
        <p>{plan ? `₹${plan.hourly_rate_rupees} / hour` : "No hourly price"}</p>
      </div>
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

function SessionPanel({ token, session, onChanged, onUnauthorized, onNotice }) {
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
      const ended = await api(`/sessions/${session.id}/end`, {
        method: "POST",
        token,
        body: { payment_method: needsPayment ? method : null },
      })
      onNotice(`${session.station_code} closed. Bill ₹${ended.final_amount_rupees}. Paid ₹${ended.amount_paid_rupees}.`)
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
