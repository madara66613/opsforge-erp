import { useEffect, useState } from 'react'

import { Icon } from '../components/Icon'
import { PageHeader, Panel, StatusBadge } from '../components/ui'
import type { VersionInfo } from '../types'

interface Probe { health: boolean; ready: boolean; version: VersionInfo | null }

export function SystemPage() {
  const [probe, setProbe] = useState<Probe | null>(null)
  useEffect(() => {
    let active = true
    Promise.all([
      fetch('/health').then((response) => response.ok),
      fetch('/ready').then((response) => response.ok),
      fetch('/version').then(async (response) => response.ok ? response.json() as Promise<VersionInfo> : null),
    ]).then(([health, ready, version]) => { if (active) setProbe({ health, ready, version }) }).catch(() => { if (active) setProbe({ health: false, ready: false, version: null }) })
    return () => { active = false }
  }, [])

  return <>
    <PageHeader eyebrow="Operational support" title="System status" description="Fast diagnostics for application availability, database readiness, and release identity." actions={<a className="button button-secondary" href="/docs" target="_blank" rel="noreferrer">Open API docs <span>↗</span></a>}/>
    <section className="system-grid"><Panel className="system-overview"><div className="system-hero"><span className="system-orbit"><Icon name="system" size={28}/></span><div><p className="section-kicker">Overall status</p><h2>{probe?.health && probe.ready ? 'All systems operational' : probe ? 'Attention required' : 'Running diagnostics…'}</h2><p>Independent liveness and database readiness probes keep failures easy to isolate.</p></div><StatusBadge value={probe?.health && probe.ready ? 'operational' : probe ? 'degraded' : 'checking'}/></div></Panel><Panel><div className="panel-heading"><div><p className="section-kicker">Release</p><h2>Build identity</h2></div></div><dl className="system-details"><div><dt>Application</dt><dd>{probe?.version?.name ?? '—'}</dd></div><div><dt>Version</dt><dd className="mono">{probe?.version ? `v${probe.version.version}` : '—'}</dd></div><div><dt>Environment</dt><dd><StatusBadge value={probe?.version?.environment ?? 'unknown'}/></dd></div></dl></Panel></section>
    <section className="probe-grid"><ProbeCard icon="activity" title="API liveness" endpoint="GET /health" ok={probe?.health}/><ProbeCard icon="warehouse" title="Database readiness" endpoint="GET /ready" ok={probe?.ready}/><ProbeCard icon="package" title="Release metadata" endpoint="GET /version" ok={Boolean(probe?.version)}/></section>
    <Panel className="support-panel"><div><p className="section-kicker">Support workflow</p><h2>Diagnose with context</h2><p>Every API response carries a request ID mirrored in structured logs and audit events. Start with the probes, capture the request ID, then correlate the action without exposing sensitive data.</p></div><ol><li><span>01</span>Check liveness and readiness</li><li><span>02</span>Capture the request ID</li><li><span>03</span>Review logs and audit history</li></ol></Panel>
  </>
}

type IconName = Parameters<typeof Icon>[0]['name']
function ProbeCard({ icon, title, endpoint, ok }: { icon: IconName; title: string; endpoint: string; ok: boolean | undefined }) { return <article><span className="probe-icon"><Icon name={icon}/></span><div><strong>{title}</strong><code>{endpoint}</code></div><StatusBadge value={ok === undefined ? 'checking' : ok ? 'healthy' : 'unavailable'}/></article> }
