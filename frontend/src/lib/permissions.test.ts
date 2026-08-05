import { describe, expect, it } from 'vitest'

import { can } from './permissions'

describe('role permissions', () => {
  it('keeps operator workflows writable without exposing user administration', () => {
    expect(can('operator', 'sales.write')).toBe(true)
    expect(can('operator', 'inventory.write')).toBe(true)
    expect(can('operator', 'users.manage')).toBe(false)
    expect(can('operator', 'audit.read')).toBe(false)
  })

  it('keeps support read-only while retaining diagnostics', () => {
    expect(can('support', 'products.read')).toBe(true)
    expect(can('support', 'products.write')).toBe(false)
    expect(can('support', 'audit.read')).toBe(true)
    expect(can('support', 'system.read')).toBe(true)
  })
})
