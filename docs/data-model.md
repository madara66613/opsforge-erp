# Data model

The diagram shows the persisted model through the inventory milestone. UUID primary keys make demo data stable and avoid exposing sequential record volume.

```mermaid
erDiagram
    USER ||--o{ AUTH_SESSION : owns
    USER o|--o{ AUDIT_LOG : acts
    USER ||--o{ STOCK_MOVEMENT : creates
    PRODUCT ||--o{ INVENTORY_BALANCE : has
    WAREHOUSE ||--o{ INVENTORY_BALANCE : stores
    PRODUCT ||--o{ STOCK_MOVEMENT : moves
    WAREHOUSE ||--o{ STOCK_MOVEMENT : sources
    WAREHOUSE o|--o{ STOCK_MOVEMENT : receives_transfer

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
```

`inventory_balances(product_id, warehouse_id)` is unique. It is a transactionally maintained current-state projection; `stock_movements` is the operational history used for traceability.

