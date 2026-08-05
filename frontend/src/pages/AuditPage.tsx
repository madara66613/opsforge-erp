import { useMemo, useState } from 'react'

import { useAuth } from '../auth/useAuth'
import { Icon } from '../components/Icon'
import { EmptyState, ErrorState, LoadingState, PageHeader, Panel, SearchBox, StatusBadge, TableMeta } from '../components/ui'
import { useApiResource } from '../hooks/useApiResource'
import { dateTime } from '../lib/format'
import type { AuditEvent, ListResponse } from '../types'

export function AuditPage() {
  const { token } = useAuth()
  const { data, loading, error, refresh } = useApiResource<ListResponse<AuditEvent>>('/audit-logs?limit=100', token)
  const [search, setSearch] = useState('')
  const [outcome, setOutcome] = useState('all')
  const events = useMemo(() => data?.items.filter((event) => (outcome === 'all' || event.outcome === outcome) && `${event.action} ${event.entity_type} ${event.entity_id ?? ''} ${event.request_id ?? ''}`.toLowerCase().includes(search.toLowerCase())) ?? [], [data, outcome, search])

  return <>
    <PageHeader eyebrow="Traceability" title="Audit log" description="A searchable record of successful actions, denied operations, and failed business attempts."/>
    <Panel><div className="filter-row"><SearchBox value={search} onChange={setSearch} placeholder="Search action, entity, or request ID"/><select className="filter-select" value={outcome} onChange={(event) => setOutcome(event.target.value)}><option value="all">All outcomes</option><option value="success">Success</option><option value="failure">Failure</option></select><TableMeta total={events.length} noun="event"/></div>{loading && !data ? <LoadingState/> : error && !data ? <ErrorState message={error} retry={refresh}/> : events.length === 0 ? <EmptyState title="No audit events found" text="Adjust the filters to see operational history."/> : <div className="table-scroll"><table><thead><tr><th>Event</th><th>Entity</th><th>Outcome</th><th>Context</th><th>Request ID</th><th>Recorded</th></tr></thead><tbody>{events.map((event) => <tr key={event.id}><td><div className="primary-cell"><span className={`entity-icon audit ${event.outcome}`}><Icon name="audit"/></span><span><strong>{event.action}</strong><small>Actor {event.actor_user_id?.slice(0, 8) ?? 'system'}</small></span></div></td><td><strong>{event.entity_type}</strong><small className="cell-note mono">{event.entity_id?.slice(0, 12) ?? '—'}</small></td><td><StatusBadge value={event.outcome}/></td><td><code className="detail-code">{compactDetails(event.details)}</code></td><td className="mono muted">{event.request_id?.slice(0, 12) ?? '—'}</td><td className="muted">{dateTime(event.created_at)}</td></tr>)}</tbody></table></div>}</Panel>
  </>
}

function compactDetails(details: Record<string, unknown>): string {
  const text = Object.entries(details).slice(0, 2).map(([key, value]) => `${key}: ${String(value)}`).join(' · ')
  return text || 'No additional details'
}
