# Security

Staff passwords are hashed with Argon2id. Login returns a bearer token. `GET /stations`, `GET /pricing`, price changes, staff creation, and the audit list require that token and a permission.

Customer passwords use the same Argon2id hash. Customers and staff receive different tokens, so one cannot call the other's routes. OTP is not part of this system. Existing customers sign in with the password stored on the café server, including when the public internet is down.

The super admin account is created only when `GD_OS_ADMIN_PASSWORD` is at least 8 characters and is not `change-me`. `JWT_SECRET` must also be replaced. Login is limited to 5 failures per address in 5 minutes, in this server process.

The notes below are the rules for the work that follows.

- Passwords will be hashed with Argon2id. Plaintext passwords are never stored.
- Secrets live in `.env`, which is gitignored. `.env.example` contains placeholders only.
- The API computes prices. A browser or agent cannot submit the amount to charge.
- Staff actions will be written to an audit log.
- Login is rate-limited.
- The café API is for the local network. It is not a public internet service.
- PostgreSQL must not be exposed beyond the café LAN.
- Agent unlock commands will be rejected unless they match a server-side session. That protocol is not built yet.

The sample database password in `.env.example` is `change-me`. Replace it on any machine that stores real café data.
