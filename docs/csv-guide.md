# CSV import and export

CSV supports deliberate, small-scope data transfer: product import, product export, and inventory export. Admins and operators may import; admin, operator, and support roles may export.

## Product import

Use UTF-8 text, a maximum file size of 2 MB, and this exact header order:

```csv
sku,name,description,unit,purchase_price,sale_price,reorder_threshold,is_active
```

| Column | Rule |
| --- | --- |
| `sku` | Required, unique, normalized to uppercase, maximum 64 characters |
| `name` | Required, 2–160 characters |
| `description` | Optional |
| `unit` | Required, such as `pcs` or `box` |
| `purchase_price` | Decimal greater than or equal to zero |
| `sale_price` | Decimal greater than or equal to zero |
| `reorder_threshold` | Quantity greater than or equal to zero |
| `is_active` | `true`, `false`, `1`, `0`, `yes`, or `no` |

The importer validates headers and every row before creating anything. One invalid row rejects the whole file and reports its row, field, and reason. Existing and within-file duplicate SKUs are rejected. Successfully imported products receive a zero balance in every existing warehouse.

Start with [the sample file](../samples/products.csv). Do not import spreadsheet formulas or locale-formatted currency symbols; use plain decimal values such as `129.00`.

## Exports

Product export uses the same columns as import, so it can be reviewed and re-imported into an empty environment. Inventory export adds warehouse, on-hand quantity, configured threshold, computed low-stock status, and update timestamp.

Exports are point-in-time operational extracts, not accounting reports. Successful import/export operations create metadata-only audit entries; raw CSV content is never stored in the audit log.
