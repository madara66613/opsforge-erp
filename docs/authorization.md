# Authentication and authorization

OpsForge ERP uses revocable opaque bearer sessions. Raw tokens are returned once at login; only SHA-256 token digests are persisted. Passwords are hashed with Argon2 through `pwdlib`, and authentication returns the same public error for unknown, inactive, and incorrectly authenticated accounts.

## Role matrix

| Capability | Admin | Operator | Support |
| --- | --- | --- | --- |
| Manage users and roles | Yes | No | No |
| View users | Yes | No | Yes |
| View audit history | Yes | No | Yes |
| Manage products and partners | Yes | Yes | Read only |
| Execute inventory and order workflows | Yes | Yes | Read only |
| Override negative-inventory protection | Yes | No | No |
| Import CSV | Yes | Yes | No |
| Export operational CSV | Yes | Yes | Yes |

The backend is authoritative. The frontend hides actions a user cannot perform, but every protected endpoint independently checks the required permission and returns `403` when it is missing.

## Session behavior

- Default lifetime: 480 minutes, configurable through `OPSFORGE_SESSION_TTL_MINUTES`.
- Logout immediately marks the current session revoked.
- Disabled users cannot create new sessions and existing tokens are rejected.
- Session tokens and passwords must never be included in structured logs or audit details.
- Demo credentials are limited to seeded local environments and are not production defaults.

