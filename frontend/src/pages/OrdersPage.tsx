import { type FormEvent, useMemo, useState } from 'react'

import { useAuth } from '../auth/useAuth'
import { Icon } from '../components/Icon'
import { Button, EmptyState, ErrorState, Field, LoadingState, Modal, PageHeader, Panel, SearchBox, StatusBadge, TableMeta } from '../components/ui'
import { useApiResource } from '../hooks/useApiResource'
import { api, errorMessage } from '../lib/api'
import { dateTime, money, quantity, titleCase } from '../lib/format'
import { can } from '../lib/permissions'
import type { ListResponse, Partner, Product, PurchaseOrder, SalesOrder, Warehouse } from '../types'

type Kind = 'sales' | 'purchases'
type Order = SalesOrder | PurchaseOrder
interface DraftLine { product_id: string; quantity: string }

export function OrdersPage({ kind }: { kind: Kind }) {
  const { token, user } = useAuth()
  const config = kind === 'sales' ? salesConfig : purchaseConfig
  const orders = useApiResource<ListResponse<Order>>(config.listPath, token)
  const partners = useApiResource<ListResponse<Partner>>('/partners?limit=100&active=true', token)
  const products = useApiResource<ListResponse<Product>>('/products?limit=100&active=true', token)
  const warehouses = useApiResource<ListResponse<Warehouse>>('/warehouses?limit=100&active=true', token)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [modal, setModal] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [lines, setLines] = useState<DraftLine[]>([{ product_id: '', quantity: '1' }])
  const [busy, setBusy] = useState('')
  const [formError, setFormError] = useState('')
  const writable = Boolean(user && can(user.role, kind === 'sales' ? 'sales.write' : 'purchases.write'))
  const filtered = useMemo(() => orders.data?.items.filter((order) => (status === 'all' || order.status === status) && `${order.order_number} ${order.partner.name}`.toLowerCase().includes(search.toLowerCase())) ?? [], [orders.data, search, status])

  async function createOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy('create'); setFormError('')
    const form = new FormData(event.currentTarget)
    try {
      await api(config.listPath, { method: 'POST', token, body: {
        partner_id: form.get('partner_id'), warehouse_id: form.get('warehouse_id'), notes: form.get('notes') || null,
        lines: lines.map((line) => ({ product_id: line.product_id, quantity: line.quantity })),
      } })
      setModal(false); setLines([{ product_id: '', quantity: '1' }]); orders.refresh()
    } catch (reason) { setFormError(errorMessage(reason)) } finally { setBusy('') }
  }

  async function transition(order: Order, action: string, idempotent = false) {
    setBusy(`${order.id}:${action}`); setFormError('')
    try {
      await api(`${config.listPath}/${order.id}/${action}`, { method: 'POST', token, headers: idempotent ? { 'Idempotency-Key': crypto.randomUUID() } : undefined })
      orders.refresh()
    } catch (reason) { setFormError(errorMessage(reason)) } finally { setBusy('') }
  }

  const eligiblePartners = partners.data?.items.filter((partner) => partner.is_active && (partner.partner_type === config.partnerType || partner.partner_type === 'both')) ?? []
  return <>
    <PageHeader eyebrow={config.eyebrow} title={config.title} description={config.description} actions={writable && <Button onClick={() => { setFormError(''); setLines([{ product_id: '', quantity: '1' }]); setModal(true) }}><Icon name="plus"/> {config.newLabel}</Button>}/>
    <Panel>
      <div className="filter-row"><SearchBox value={search} onChange={setSearch} placeholder={`Search ${config.title.toLowerCase()}`}/><select className="filter-select" value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">All statuses</option>{config.statuses.map((value) => <option key={value} value={value}>{titleCase(value)}</option>)}</select><TableMeta total={filtered.length} noun="order"/></div>
      {formError && !modal && <div className="inline-alert">{formError}</div>}
      {orders.loading && !orders.data ? <LoadingState/> : orders.error && !orders.data ? <ErrorState message={orders.error} retry={orders.refresh}/> : filtered.length === 0 ? <EmptyState title={`No ${config.title.toLowerCase()} found`} text={`Create the first ${kind === 'sales' ? 'customer order' : 'supplier purchase'} or adjust the filters.`}/> : <div className="table-scroll"><table><thead><tr><th>Order</th><th>Partner</th><th>Warehouse</th><th>Status</th><th>Total</th><th>Created</th><th className="align-right">Workflow</th></tr></thead><tbody>{filtered.map((order) => <OrderRows key={order.id} order={order} kind={kind} expanded={expanded === order.id} toggle={() => setExpanded(expanded === order.id ? null : order.id)} writable={writable} busy={busy} transition={transition}/>)}</tbody></table></div>}
    </Panel>
    {modal && <Modal title={config.newLabel} description="Prices use the current product catalog. Inventory changes only at completion or receipt." onClose={() => setModal(false)}><form className="modal-form order-form" onSubmit={(event) => void createOrder(event)}><div className="form-grid"><Field label={kind === 'sales' ? 'Customer' : 'Supplier'}><select name="partner_id" required defaultValue=""><option value="" disabled>Select {config.partnerType}</option>{eligiblePartners.map((partner) => <option value={partner.id} key={partner.id}>{partner.code} — {partner.name}</option>)}</select></Field><Field label="Warehouse"><select name="warehouse_id" required defaultValue=""><option value="" disabled>Select warehouse</option>{warehouses.data?.items.filter((item) => item.is_active).map((warehouse) => <option value={warehouse.id} key={warehouse.id}>{warehouse.code} — {warehouse.name}</option>)}</select></Field><Field label="Notes"><input name="notes" placeholder="Optional operational context"/></Field></div><div className="line-editor"><div className="line-editor-heading"><div><strong>Order lines</strong><small>Each product can appear once.</small></div><Button type="button" variant="secondary" onClick={() => setLines((value) => [...value, { product_id: '', quantity: '1' }])}><Icon name="plus" size={15}/> Add line</Button></div>{lines.map((line, index) => <div className="line-input" key={index}><span>{String(index + 1).padStart(2, '0')}</span><select value={line.product_id} required onChange={(event) => setLines((items) => items.map((item, lineIndex) => lineIndex === index ? { ...item, product_id: event.target.value } : item))}><option value="" disabled>Select product</option>{products.data?.items.map((product) => <option value={product.id} key={product.id} disabled={lines.some((item, lineIndex) => lineIndex !== index && item.product_id === product.id)}>{product.sku} — {product.name} · {money(kind === 'sales' ? product.sale_price : product.purchase_price)}</option>)}</select><input type="number" min="0.001" step="0.001" value={line.quantity} required aria-label={`Line ${index + 1} quantity`} onChange={(event) => setLines((items) => items.map((item, lineIndex) => lineIndex === index ? { ...item, quantity: event.target.value } : item))}/><button type="button" className="icon-button" aria-label={`Remove line ${index + 1}`} disabled={lines.length === 1} onClick={() => setLines((items) => items.filter((_, lineIndex) => lineIndex !== index))}><Icon name="close" size={16}/></button></div>)}</div>{formError && <div className="form-error"><Icon name="alert" size={16}/>{formError}</div>}<div className="modal-actions"><Button type="button" variant="secondary" onClick={() => setModal(false)}>Cancel</Button><Button type="submit" disabled={busy === 'create'}>{busy === 'create' ? 'Creating…' : config.newLabel}</Button></div></form></Modal>}
  </>
}

const salesConfig = { listPath: '/sales-orders', eyebrow: 'Order to cash', title: 'Sales orders', description: 'Move customer demand through a controlled, inventory-safe workflow.', newLabel: 'New sales order', partnerType: 'customer' as const, statuses: ['draft','confirmed','processing','completed','cancelled'] }
const purchaseConfig = { listPath: '/purchase-orders', eyebrow: 'Procure to stock', title: 'Purchase orders', description: 'Coordinate inbound supply and receive every line into stock atomically.', newLabel: 'New purchase order', partnerType: 'supplier' as const, statuses: ['draft','ordered','received','cancelled'] }

function OrderRows({ order, kind, expanded, toggle, writable, busy, transition }: { order: Order; kind: Kind; expanded: boolean; toggle: () => void; writable: boolean; busy: string; transition: (order: Order, action: string, idempotent?: boolean) => Promise<void> }) {
  return <><tr className="clickable-row" onClick={toggle}><td><div className="primary-cell"><span className={`entity-icon ${kind}`}><Icon name={kind === 'sales' ? 'sales' : 'purchases'}/></span><span><strong>{order.order_number}</strong><small>{order.lines.length} line{order.lines.length === 1 ? '' : 's'}</small></span></div></td><td><strong>{order.partner.name}</strong><small className="cell-note">{order.partner.code}</small></td><td>{order.warehouse.code}</td><td><StatusBadge value={order.status}/></td><td className="mono emphasis">{money(order.total_amount)}</td><td className="muted">{dateTime(order.created_at)}</td><td className="align-right" onClick={(event) => event.stopPropagation()}><WorkflowActions order={order} kind={kind} writable={writable} busy={busy} transition={transition}/></td></tr>{expanded && <tr className="detail-row"><td colSpan={7}><div className="order-detail"><div><p className="section-kicker">Line details</p>{order.lines.map((line) => <div className="order-line" key={line.id}><span><strong>{line.product.name}</strong><small>{line.product.sku}</small></span><span>{quantity(line.quantity)} {line.product.unit} × {money(line.unit_price ?? line.unit_cost ?? '0')}</span><strong>{money(line.line_total)}</strong></div>)}</div><aside><span>Order total</span><strong>{money(order.total_amount)}</strong><small>{order.notes || 'No notes attached'}</small></aside></div></td></tr>}</>
}

function WorkflowActions({ order, kind, writable, busy, transition }: { order: Order; kind: Kind; writable: boolean; busy: string; transition: (order: Order, action: string, idempotent?: boolean) => Promise<void> }) {
  if (!writable) return <span className="read-only-label">Read only</span>
  const working = busy.startsWith(order.id)
  if (kind === 'sales') {
    if (order.status === 'draft') return <div className="workflow-actions"><button disabled={working} onClick={() => void transition(order, 'confirm')}>Confirm</button><button disabled={working} className="danger-link" onClick={() => void transition(order, 'cancel')}>Cancel</button></div>
    if (order.status === 'confirmed') return <div className="workflow-actions"><button disabled={working} onClick={() => void transition(order, 'process')}>Start processing</button><button disabled={working} className="danger-link" onClick={() => void transition(order, 'cancel')}>Cancel</button></div>
    if (order.status === 'processing') return <div className="workflow-actions"><button disabled={working} onClick={() => void transition(order, 'complete', true)}>{working ? 'Completing…' : 'Complete'}</button><button disabled={working} className="danger-link" onClick={() => void transition(order, 'cancel')}>Cancel</button></div>
  } else {
    if (order.status === 'draft') return <div className="workflow-actions"><button disabled={working} onClick={() => void transition(order, 'order')}>Submit order</button><button disabled={working} className="danger-link" onClick={() => void transition(order, 'cancel')}>Cancel</button></div>
    if (order.status === 'ordered') return <div className="workflow-actions"><button disabled={working} onClick={() => void transition(order, 'receive', true)}>{working ? 'Receiving…' : 'Receive'}</button><button disabled={working} className="danger-link" onClick={() => void transition(order, 'cancel')}>Cancel</button></div>
  }
  return <span className="read-only-label">Final state</span>
}
