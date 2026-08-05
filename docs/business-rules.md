# Business rules

This document defines the operational behavior enforced by OpsForge ERP. The API and UI may make these rules easier to understand, but the service layer and database remain authoritative.

## Product catalog

- SKUs are trimmed, normalized to uppercase, and unique.
- Sale and purchase prices use fixed-precision decimal values and cannot be negative.
- Inactive products remain visible for historical records but cannot participate in new stock movements.
- Product deactivation does not delete inventory or movement history.
- Each product has a non-negative reorder threshold. A warehouse balance at or below that product-specific threshold is low stock.

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

## Partners

- Partner codes are trimmed, normalized to uppercase, and unique.
- Customers may be used on sales orders, suppliers on purchase orders, and `both` partners on either workflow.
- Inactive partners remain available to historical records but cannot be selected for new orders.
- Deactivation preserves orders, movements, and audit history.

## Sales orders

The supported lifecycle is `draft → confirmed → processing → completed`. A draft, confirmed, or processing order may be cancelled; completed and cancelled orders are terminal.

- A sales order requires an active customer-compatible partner, an active warehouse, at least one active product, positive quantities, and non-negative unit prices.
- A product may appear only once per order.
- Completing an order issues every line from its warehouse and marks the order complete in one transaction.
- If any line lacks stock, the entire completion rolls back: no balance, movement, or order status is partially changed.
- Sales completion honors the normal negative-inventory policy; it does not expose the admin override used by manual stock adjustments.

## Purchase orders

The supported lifecycle is `draft → ordered → received`. A draft or ordered purchase may be cancelled; received and cancelled purchases are terminal.

- A purchase order requires an active supplier-compatible partner, an active warehouse, at least one active product, positive quantities, and non-negative unit costs.
- Receiving creates one stock receipt per line and marks the purchase received in one transaction.
- A product may appear only once per order.

## Idempotency and auditability

- Stock-changing order endpoints require an `Idempotency-Key` between 8 and 128 characters.
- Repeating the same operation, resource, actor, and key returns the completed result without creating duplicate movements.
- Reusing a key for a different resource or request is rejected with a conflict.
- The order row is locked before an idempotency claim and any balance mutations, making concurrent retries safe.
- Every successful transition and every failed business attempt records its actor, request ID, outcome, and relevant reason in the audit log.

## CSV transfer

- Product import validates the exact header contract and every row before opening the write phase.
- An invalid header, value, duplicate SKU, or database conflict rejects the full import; partial product creation is not allowed.
- Imported products receive a zero balance for each existing warehouse in the same transaction.
- Product and inventory exports are available to read-only support users; import remains an admin/operator write capability.
- Audit metadata records row counts and outcomes but never stores uploaded file contents.
