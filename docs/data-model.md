# Data model

The diagram shows the persisted model through the transactional order milestone. UUID primary keys make demo data stable and avoid exposing sequential record volume.

```mermaid
erDiagram
    USER ||--o{ AUTH_SESSION : owns
    USER o|--o{ AUDIT_LOG : acts
    USER ||--o{ STOCK_MOVEMENT : creates
    USER ||--o{ SALES_ORDER : creates
    USER ||--o{ PURCHASE_ORDER : creates
    USER ||--o{ IDEMPOTENCY_RECORD : claims
    PRODUCT ||--o{ INVENTORY_BALANCE : has
    WAREHOUSE ||--o{ INVENTORY_BALANCE : stores
    PRODUCT ||--o{ STOCK_MOVEMENT : moves
    WAREHOUSE ||--o{ STOCK_MOVEMENT : sources
    WAREHOUSE o|--o{ STOCK_MOVEMENT : receives_transfer
    PARTNER ||--o{ SALES_ORDER : customer
    PARTNER ||--o{ PURCHASE_ORDER : supplier
    WAREHOUSE ||--o{ SALES_ORDER : fulfills
    WAREHOUSE ||--o{ PURCHASE_ORDER : receives
    SALES_ORDER ||--|{ SALES_ORDER_LINE : contains
    PURCHASE_ORDER ||--|{ PURCHASE_ORDER_LINE : contains
    PRODUCT ||--o{ SALES_ORDER_LINE : sold
    PRODUCT ||--o{ PURCHASE_ORDER_LINE : purchased

    USER {
        uuid id PK
        string email UK
        string role
        boolean is_active
    }
    AUTH_SESSION {
        uuid id PK
        uuid user_id FK
        string token_hash UK
        datetime expires_at
        datetime revoked_at
    }
    AUDIT_LOG {
        uuid id PK
        uuid actor_user_id FK
        string action
        string outcome
        json details
    }
    PRODUCT {
        uuid id PK
        string sku UK
        string name
        decimal sale_price
        decimal purchase_price
        decimal reorder_threshold
    }
    WAREHOUSE {
        uuid id PK
        string code UK
        string name
    }
    INVENTORY_BALANCE {
        uuid id PK
        uuid product_id FK
        uuid warehouse_id FK
        decimal quantity
    }
    STOCK_MOVEMENT {
        uuid id PK
        string movement_type
        uuid product_id FK
        uuid warehouse_id FK
        uuid destination_warehouse_id FK
        decimal quantity
        boolean allow_negative_override
    }
    PARTNER {
        uuid id PK
        string code UK
        string name
        string partner_type
        boolean is_active
    }
    SALES_ORDER {
        uuid id PK
        string order_number UK
        uuid partner_id FK
        uuid warehouse_id FK
        string status
    }
    SALES_ORDER_LINE {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        decimal quantity
        decimal unit_price
    }
    PURCHASE_ORDER {
        uuid id PK
        string order_number UK
        uuid partner_id FK
        uuid warehouse_id FK
        string status
        date expected_delivery_date
    }
    PURCHASE_ORDER_LINE {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        decimal quantity
        decimal unit_cost
    }
    IDEMPOTENCY_RECORD {
        uuid id PK
        string operation
        string idempotency_key
        uuid resource_id
        string request_hash
    }
```

`inventory_balances(product_id, warehouse_id)`, each order line's `(order_id, product_id)`, and `idempotency_records(operation, idempotency_key)` are unique. Inventory balances are a transactionally maintained current-state projection; stock movements and audit logs retain the operational history used for traceability.
