import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { AuthProvider } from './auth/AuthProvider'

const operator = {
  id: '00000000-0000-0000-0000-000000000002',
  email: 'operator@demo.opsforge.dev',
  full_name: 'Olivia Operator',
  role: 'operator',
  is_active: true,
  last_login_at: null,
  created_at: '2026-08-05T10:00:00Z',
  updated_at: '2026-08-05T10:00:00Z',
} as const

const dashboard = {
  counts: { active_products: 6, active_warehouses: 2, active_partners: 4, pending_sales_orders: 1, pending_purchase_orders: 1, low_stock_balances: 2 },
  inventory_value: '1250.00',
  pending_sales_value: '480.00',
  recent_sales_orders: [],
  recent_purchase_orders: [],
  recent_movements: [],
  recent_audit_events: [],
}

describe('OpsForge application', () => {
  beforeEach(() => {
    localStorage.clear()
    window.history.replaceState({}, '', '/')
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input)
      if (path.endsWith('/auth/login')) return response({ access_token: 'test-token', token_type: 'bearer', expires_at: '2099-01-01T00:00:00Z', user: operator })
      if (path.endsWith('/dashboard/summary')) return response(dashboard)
      return response({ detail: 'Unexpected test request' }, 404)
    }))
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('presents secure demo access for all three roles', () => {
    render(<AuthProvider><App /></AuthProvider>)

    expect(screen.getByRole('heading', { name: /control the flow/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Admin' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Operator' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Support' })).toBeInTheDocument()
  })

  it('signs an operator in, loads live metrics, and hides admin navigation', async () => {
    render(<AuthProvider><App /></AuthProvider>)
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText('Inventory value')).toBeInTheDocument()
    expect(screen.getByText(/1,250\.00/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /sales orders/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /users & roles/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /audit log/i })).not.toBeInTheDocument()
  })
})

function response(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } })
}
