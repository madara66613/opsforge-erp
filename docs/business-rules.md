# Business rules

This document defines the operational behavior enforced by OpsForge ERP. The API and UI may make these rules easier to understand, but the service layer and database remain authoritative.

## Product catalog

- SKUs are trimmed, normalized to uppercase, and unique.
- Sale and purchase prices use fixed-precision decimal values and cannot be negative.
- Inactive products remain visible for historical records but cannot participate in new stock movements.
- Product deactivation does not delete inventory or movement history.

## Warehouses and balances

- Warehouse codes are trimmed, normalized to uppercase, and unique.
- Every product/warehouse pair has one balance row protected by a database uniqueness constraint.
- Balance rows are locked before stock-changing operations. Transfers lock both warehouse balances in deterministic warehouse-ID order to reduce deadlock risk.
- The movement ledger is immutable. Corrections use a new explicit adjustment rather than editing prior history.

## Stock movements

| Type | Source effect | Destination effect | Notes |
| --- | ---: | ---: | --- |
| `receipt` | Increase | — | Supplier or opening receipt |
| `sale_issue` | Decrease | — | Shipment/customer issue |
| `transfer` | Decrease | Increase | Requires a different destination warehouse |
| `return` | Increase | — | Customer return into stock |
| `adjustment` | Signed change | — | Non-zero correction with an explanation |

- Receipt, sale issue, transfer, and return quantities must be positive. Adjustment quantity may be positive or negative but never zero.
- A movement, every affected balance, and its audit event commit in one database transaction.
- Failed movements roll back all balance changes and create a separate failure audit event.
- Negative inventory is rejected by default. Only an admin may set `allow_negative_override=true`; that choice is preserved on the movement and highlighted in audit details.
- Operators can execute normal movements. Support users have read-only visibility.

Order-specific reservation, completion, receiving, and idempotency rules are documented when those workflows are introduced.

