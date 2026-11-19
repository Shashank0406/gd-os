# Security

Day 1 has no accounts, no sessions, and no agent commands. The notes below are the rules for the work that follows.

- Passwords will be hashed with Argon2id. Plaintext passwords are never stored.
- Secrets live in `.env`, which is gitignored. `.env.example` contains placeholders only.
- The API computes prices. A browser or agent cannot submit the amount to charge.
- Staff actions will be written to an audit log.
- Login and OTP endpoints will be rate-limited.
- The café API is for the local network. It is not a public internet service.
- PostgreSQL must not be exposed beyond the café LAN.
- Agent unlock commands will be rejected unless they match a server-side session. That protocol is not built yet.

The sample database password in `.env.example` is `change-me`. Replace it on any machine that stores real café data.
