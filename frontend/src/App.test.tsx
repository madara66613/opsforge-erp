import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const path = String(input)
        const payload = path.endsWith('/version')
          ? { name: 'OpsForge ERP', version: '0.1.0', environment: 'test' }
          : { status: 'ok' }
        return Promise.resolve(
          new Response(JSON.stringify(payload), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        )
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders project positioning and live system probes', async () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: /one dependable workspace/i }),
    ).toBeInTheDocument()
    expect(await screen.findAllByText('healthy')).toHaveLength(2)
    expect(await screen.findByText('v0.1.0 · test')).toBeInTheDocument()
    expect(screen.getByText(/fictional, non-commercial portfolio project/i)).toBeInTheDocument()
  })
})

