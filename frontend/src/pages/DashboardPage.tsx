import { Link } from 'wouter'

import { useAuth } from '../auth/useAuth'
import { Icon } from '../components/Icon'
import { ErrorState, LoadingState, PageHeader, Panel, StatusBadge } from '../components/ui'
import { useApiResource } from '../hooks/useApiResource'
import { dateTime, money, quantity, titleCase } from '../lib/format'
import { can } from '../lib/permissions'
import type { DashboardSummary } from '../types'

export function DashboardPage() {
  const { token, user } = useAuth()
  const { data, loading, error, refresh } = useApiResource<DashboardSummary>('/dashboard/summary', token)

  return <>
    <PageHeader eyebrow="Command center" title={`Good ${greeting()}, ${user?.full_name.split(' ')[0]}.`} description="Here is what is happening across your operation right now." />
    {loading && !data ? <LoadingState/> : error && !data ? <ErrorState message={error} retry={refresh}/> : data && <>
      <section className="metric-grid">
        <Metric icon="package" label="Inventory value" value={money(data.inventory_value)} trend={`${data.counts.active_products} active products`} tone="mint" />
        <Metric icon="sales" label="Pending sales" value={money(data.pending_sales_value)} trend={`${data.counts.pending_sales_orders} orders in progress`} tone="blue" />
        <Metric icon="purchases" label="Open purchases" value={String(data.counts.pending_purchase_orders)} trend="Awaiting receipt" tone="violet" />
        <Metric icon="alert" label="Low stock" value={String(data.counts.low_stock_balances)} trend="Product-specific thresholds" tone={data.counts.low_stock_balances > 0 ? 'amber' : 'mint'} />
      </section>
      <section className="dashboard-grid">
        <Panel className="span-two">
          <div className="panel-heading"><div><p className="section-kicker">Live orders</p><h2>Recent sales</h2></div><Link href="/sales" className="text-link">View all <span>→</span></Link></div>
          <div className="compact-list">{data.recent_sales_orders.map((order) => <Link href="/sales" className="order-row" key={order.id}><span className="entity-icon sales"><Icon name="sales"/></span><span className="order-primary"><strong>{order.order_number}</strong><small>{order.partner_name}</small></span><StatusBadge value={order.status}/><span className="order-value"><strong>{money(order.total_amount)}</strong><small>{dateTime(order.created_at)}</small></span></Link>)}{data.recent_sales_orders.length === 0 && <p className="inline-empty">No sales orders yet.</p>}</div>
        </Panel>
        <Panel>
          <div className="panel-heading"><div><p className="section-kicker">At a glance</p><h2>Operations</h2></div></div>
          <div className="operation-summary"><SummaryItem label="Warehouses" value={data.counts.active_warehouses} icon="warehouse"/><SummaryItem label="Partners" value={data.counts.active_partners} icon="partners"/><SummaryItem label="Products" value={data.counts.active_products} icon="products"/></div>
        </Panel>
        <Panel className="span-two">
          <div className="panel-heading"><div><p className="section-kicker">Inventory ledger</p><h2>Latest movements</h2></div><Link href="/inventory" className="text-link">Open ledger <span>→</span></Link></div>
          <div className="movement-feed">{data.recent_movements.slice(0, 6).map((movement) => <div className="movement-row" key={movement.id}><span className={`movement-mark ${movement.movement_type}`}><Icon name="activity"/></span><span><strong>{titleCase(movement.movement_type)}</strong><small>{movement.product_sku} · {movement.warehouse_code}</small></span><span className="movement-quantity">{movement.movement_type === 'sale_issue' ? '−' : '+'}{quantity(movement.quantity)}</span><time>{dateTime(movement.created_at)}</time></div>)}</div>
        </Panel>
        <Panel>
          <div className="panel-heading"><div><p className="section-kicker">Inbound</p><h2>Recent purchases</h2></div></div>
          <div className="purchase-stack">{data.recent_purchase_orders.slice(0, 4).map((order) => <Link href="/purchases" key={order.id}><div><strong>{order.order_number}</strong><small>{order.partner_name}</small></div><div><StatusBadge value={order.status}/><strong>{money(order.total_amount)}</strong></div></Link>)}{data.recent_purchase_orders.length === 0 && <p className="inline-empty">No purchases yet.</p>}</div>
        </Panel>
        {user && can(user.role, 'audit.read') && <Panel className="span-full">
          <div className="panel-heading"><div><p className="section-kicker">Traceability</p><h2>Recent audit events</h2></div><Link href="/audit" className="text-link">Open audit log <span>→</span></Link></div>
          <div className="audit-summary">{data.recent_audit_events.map((event) => <Link href="/audit" className="audit-summary-row" key={event.id}><span className={`audit-summary-mark ${event.outcome}`}><Icon name="audit"/></span><span><strong>{event.action}</strong><small>{titleCase(event.entity_type)} · {dateTime(event.created_at)}</small></span><StatusBadge value={event.outcome}/></Link>)}{data.recent_audit_events.length === 0 && <p className="inline-empty">No audit events yet.</p>}</div>
        </Panel>}
      </section>
    </>}
  </>
}

function greeting(): string {
  const hour = new Date().getHours()
  return hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening'
}

type IconName = Parameters<typeof Icon>[0]['name']

function Metric({ icon, label, value, trend, tone }: { icon: IconName; label: string; value: string; trend: string; tone: string }) {
  return <article className="metric-card"><span className={`metric-icon ${tone}`}><Icon name={icon}/></span><div><p>{label}</p><strong>{value}</strong><small>{trend}</small></div></article>
}

function SummaryItem({ icon, label, value }: { icon: IconName; label: string; value: number }) {
  return <div><span><Icon name={icon}/></span><div><strong>{value}</strong><small>{label}</small></div></div>
}
