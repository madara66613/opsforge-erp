import { useEffect, useState } from 'react'

type ProbeState = 'checking' | 'healthy' | 'unavailable'

interface VersionInfo {
  name: string
  version: string
  environment: string
}

async function probe(path: string): Promise<Response> {
  const response = await fetch(path, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error(`${path} returned ${response.status}`)
  return response
}

function App() {
  const [liveness, setLiveness] = useState<ProbeState>('checking')
  const [readiness, setReadiness] = useState<ProbeState>('checking')
  const [version, setVersion] = useState<VersionInfo | null>(null)

  useEffect(() => {
    void probe('/health')
      .then(() => setLiveness('healthy'))
      .catch(() => setLiveness('unavailable'))
    void probe('/ready')
      .then(() => setReadiness('healthy'))
      .catch(() => setReadiness('unavailable'))
    void probe('/version')
      .then((response) => response.json() as Promise<VersionInfo>)
      .then(setVersion)
      .catch(() => setVersion(null))
  }, [])

  return (
    <main>
      <nav className="topbar" aria-label="Primary navigation">
        <a className="brand" href="/">
          <span className="brand-mark">OF</span>
          <span>OpsForge ERP</span>
        </a>
        <span className="portfolio-label">Portfolio system</span>
      </nav>

      <section className="hero">
        <div>
          <p className="eyebrow">Operations, made observable</p>
          <h1>One dependable workspace for distribution operations.</h1>
          <p className="lede">
            A compact ERP built to demonstrate inventory integrity, auditable workflows, support
            diagnostics, and production-minded delivery.
          </p>
        </div>
        <aside className="status-panel" aria-label="System status">
          <div className="status-heading">
            <span>System status</span>
            <span className="live-dot" aria-hidden="true" />
          </div>
          <StatusRow label="API liveness" state={liveness} />
          <StatusRow label="Database readiness" state={readiness} />
          <div className="version-row">
            <span>Release</span>
            <strong>{version ? `v${version.version} · ${version.environment}` : 'checking'}</strong>
          </div>
        </aside>
      </section>

      <section className="capability-grid" aria-label="Project capabilities">
        <Capability number="01" title="Inventory integrity" text="Transactional stock movements and explicit business rules." />
        <Capability number="02" title="Operational support" text="Health probes, request IDs, structured logs, and audit history." />
        <Capability number="03" title="Reviewable delivery" text="Typed code, migrations, automated tests, and focused milestones." />
      </section>

      <footer>
        Fictional, non-commercial portfolio project. Not intended for production business use.
      </footer>
    </main>
  )
}

function StatusRow({ label, state }: { label: string; state: ProbeState }) {
  return (
    <div className="status-row">
      <span>{label}</span>
      <strong data-state={state}>{state}</strong>
    </div>
  )
}

function Capability({ number, title, text }: { number: string; title: string; text: string }) {
  return (
    <article className="capability-card">
      <span>{number}</span>
      <h2>{title}</h2>
      <p>{text}</p>
    </article>
  )
}

export default App

