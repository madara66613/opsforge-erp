import { type FormEvent, useState } from 'react'

import { useAuth } from '../auth/useAuth'
import { Icon } from '../components/Icon'
import { Button, Field } from '../components/ui'
import { errorMessage } from '../lib/api'

const demos = [
  { role: 'Admin', email: 'admin@demo.opsforge.dev', password: 'AdminDemo!2026' },
  { role: 'Operator', email: 'operator@demo.opsforge.dev', password: 'OperatorDemo!2026' },
  { role: 'Support', email: 'support@demo.opsforge.dev', password: 'SupportDemo!2026' },
]

export function LoginPage() {
  const { signIn } = useAuth()
  const [email, setEmail] = useState(demos[1].email)
  const [password, setPassword] = useState(demos[1].password)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await signIn(email, password)
    } catch (reason) {
      setError(errorMessage(reason))
    } finally {
      setBusy(false)
    }
  }

  return <main className="login-layout">
    <section className="login-story">
      <div className="login-brand"><span className="brand-symbol large"><span>O</span></span><span><strong>OpsForge</strong><small>Enterprise resource planning</small></span></div>
      <div className="story-copy"><p className="page-eyebrow">Operations, made observable</p><h1>Control the flow.<br/><span>Trust the numbers.</span></h1><p>A focused distribution ERP where inventory, orders, and every operational decision stay connected and auditable.</p></div>
      <div className="story-metrics"><div><Icon name="inventory"/><span><strong>Atomic inventory</strong><small>Every stock change is transactional</small></span></div><div><Icon name="audit"/><span><strong>Complete traceability</strong><small>Every action carries its context</small></span></div><div><Icon name="system"/><span><strong>Built for support</strong><small>Health, logs, and diagnostics included</small></span></div></div>
      <p className="portfolio-note">Fictional, non-commercial portfolio project</p>
    </section>
    <section className="login-panel">
      <div className="login-card">
        <header><p className="page-eyebrow">Secure workspace</p><h2>Welcome back</h2><p>Sign in to continue to operations.</p></header>
        <form onSubmit={(event) => void submit(event)}>
          <Field label="Work email"><input type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required /></Field>
          <Field label="Password"><input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></Field>
          {error && <div className="form-error" role="alert"><Icon name="alert" size={16}/>{error}</div>}
          <Button type="submit" disabled={busy}>{busy ? <><span className="spinner small"/>Signing in…</> : <>Sign in <span>→</span></>}</Button>
        </form>
        <div className="demo-access"><div><span>Demo access</span><small>Choose a role to prefill credentials</small></div><div className="demo-buttons">{demos.map((demo) => <button key={demo.role} type="button" className={email === demo.email ? 'selected' : ''} onClick={() => { setEmail(demo.email); setPassword(demo.password) }}>{demo.role}</button>)}</div></div>
        <p className="security-note"><span className="live-dot"/> Session tokens are revocable and passwords use Argon2</p>
      </div>
    </section>
  </main>
}
