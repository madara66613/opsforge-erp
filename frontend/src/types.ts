export type Role = 'admin' | 'operator' | 'support'
export type PartnerType = 'customer' | 'supplier' | 'both'
export type SalesStatus = 'draft' | 'confirmed' | 'processing' | 'completed' | 'cancelled'
export type PurchaseStatus = 'draft' | 'ordered' | 'received' | 'cancelled'
export type MovementType = 'receipt' | 'sale_issue' | 'transfer' | 'return' | 'adjustment'

export interface User {
  id: string
  email: string
  full_name: string
  role: Role
  is_active: boolean
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface Session {
  access_token: string
  token_type: string
  expires_at: string
  user: User
}

export interface ListResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface Product {
  id: string
  sku: string
  name: string
  description: string | null
  unit: string
  sale_price: string
  purchase_price: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Warehouse {
  id: string
  code: string
  name: string
  location: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ProductReference {
  id: string
  sku: string
  name: string
  unit: string
}

export interface WarehouseReference {
  id: string
  code: string
  name: string
}

export interface InventoryBalance {
  id: string
  product: ProductReference
  warehouse: WarehouseReference
  quantity: string
  updated_at: string
}

export interface StockMovement {
  id: string
  movement_type: MovementType
  product_id: string
  warehouse_id: string
  destination_warehouse_id: string | null
  quantity: string
  unit_cost: string | null
  reference: string | null
  notes: string | null
  created_by_user_id: string
  allow_negative_override: boolean
  created_at: string
}

export interface Partner {
  id: string
  code: string
  name: string
  partner_type: PartnerType
  email: string | null
  phone: string | null
  address: string | null
  tax_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface OrderLine {
  id: string
  product: ProductReference
  quantity: string
  unit_price?: string
  unit_cost?: string
  line_total: string
}

export interface SalesOrder {
  id: string
  order_number: string
  partner: Pick<Partner, 'id' | 'code' | 'name' | 'partner_type'>
  warehouse: WarehouseReference
  status: SalesStatus
  currency: string
  notes: string | null
  created_by_user_id: string
  confirmed_at: string | null
  processing_at: string | null
  completed_at: string | null
  cancelled_at: string | null
  created_at: string
  updated_at: string
  total_amount: string
  lines: OrderLine[]
}

export interface PurchaseOrder {
  id: string
  order_number: string
  partner: Pick<Partner, 'id' | 'code' | 'name' | 'partner_type'>
  warehouse: WarehouseReference
  status: PurchaseStatus
  currency: string
  notes: string | null
  created_by_user_id: string
  ordered_at: string | null
  received_at: string | null
  cancelled_at: string | null
  created_at: string
  updated_at: string
  total_amount: string
  lines: OrderLine[]
}

export interface RecentOrder {
  id: string
  order_number: string
  partner_name: string
  status: SalesStatus | PurchaseStatus
  total_amount: string
  created_at: string
}

export interface DashboardSummary {
  counts: {
    active_products: number
    active_warehouses: number
    active_partners: number
    pending_sales_orders: number
    pending_purchase_orders: number
    low_stock_balances: number
  }
  inventory_value: string
  pending_sales_value: string
  recent_sales_orders: RecentOrder[]
  recent_purchase_orders: RecentOrder[]
  recent_movements: Array<{
    id: string
    movement_type: MovementType
    product_sku: string
    warehouse_code: string
    quantity: string
    created_at: string
  }>
}

export interface AuditEvent {
  id: string
  actor_user_id: string | null
  action: string
  entity_type: string
  entity_id: string | null
  outcome: 'success' | 'failure'
  request_id: string | null
  details: Record<string, unknown>
  created_at: string
}

export interface VersionInfo {
  name: string
  version: string
  environment: string
}
