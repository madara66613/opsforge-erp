import type { Role } from '../types'

export type Permission =
  | 'users.read'
  | 'users.manage'
  | 'audit.read'
  | 'system.read'
  | 'dashboard.read'
  | 'products.read'
  | 'products.write'
  | 'inventory.read'
  | 'inventory.write'
  | 'inventory.override'
  | 'partners.read'
  | 'partners.write'
  | 'sales.read'
  | 'sales.write'
  | 'purchases.read'
  | 'purchases.write'
  | 'csv.import'
  | 'csv.export'

const all: Permission[] = [
  'users.read', 'users.manage', 'audit.read', 'system.read', 'dashboard.read',
  'products.read', 'products.write', 'inventory.read', 'inventory.write',
  'inventory.override', 'partners.read', 'partners.write', 'sales.read',
  'sales.write', 'purchases.read', 'purchases.write', 'csv.import', 'csv.export',
]

const rolePermissions: Record<Role, ReadonlySet<Permission>> = {
  admin: new Set(all),
  operator: new Set([
    'system.read', 'dashboard.read', 'products.read', 'products.write', 'inventory.read',
    'inventory.write', 'partners.read', 'partners.write', 'sales.read', 'sales.write',
    'purchases.read', 'purchases.write', 'csv.import', 'csv.export',
  ]),
  support: new Set([
    'users.read', 'audit.read', 'system.read', 'dashboard.read', 'products.read',
    'inventory.read', 'partners.read', 'sales.read', 'purchases.read', 'csv.export',
  ]),
}

export function can(role: Role, permission: Permission): boolean {
  return rolePermissions[role].has(permission)
}
