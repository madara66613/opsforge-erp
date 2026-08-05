import { type FormEvent, useMemo, useState } from 'react'

import { useAuth } from '../auth/useAuth'
import { Icon } from '../components/Icon'
import { Button, EmptyState, ErrorState, Field, LoadingState, Modal, PageHeader, Panel, SearchBox, StatusBadge, TableMeta } from '../components/ui'
import { useApiResource } from '../hooks/useApiResource'
import { api, downloadCsv, errorMessage } from '../lib/api'
import { dateTime, quantity, titleCase } from '../lib/format'
import { can } from '../lib/permissions'
import type { InventoryBalance, ListResponse, MovementType, Product, StockMovement, Warehouse } from '../types'

type Tab = 'balances' | 'movements' | 'warehouses'

export function InventoryPage() {
  const { token, user } = useAuth()
  const balances = useApiResource<ListResponse<InventoryBalance>>('/inventory?limit=100', token)
  const movements = useApiResource<ListResponse<StockMovement>>('/inventory/movements?limit=100', token)
  const products = useApiResource<ListResponse<Product>>('/products?limit=100&active=true', token)
  const warehouses = useApiResource<ListResponse<Warehouse>>('/warehouses?limit=100', token)
  const [tab, setTab] = useState<Tab>('balances')
  const [search, setSearch] = useState('')
  const [movementModal, setMovementModal] = useState(false)
  const [warehouseModal, setWarehouseModal] = useState(false)
  const [movementType, setMovementType] = useState<MovementType>('receipt')
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')
  const writable = Boolean(user && can(user.role, 'inventory.write'))
  const exportable = Boolean(user && can(user.role, 'csv.export'))
  const canManageWarehouses = writable

  const filteredBalances = useMemo(() => balances.data?.items.filter((item) => `${item.product.sku} ${item.product.name} ${item.warehouse.code}`.toLowerCase().includes(search.toLowerCase())) ?? [], [balances.data, search])
  const filteredMovements = useMemo(() => movements.data?.items.filter((item) => `${item.movement_type} ${item.reference ?? ''} ${productName(item.product_id, products.data?.items)} ${warehouseName(item.warehouse_id, warehouses.data?.items)}`.toLowerCase().includes(search.toLowerCase())) ?? [], [movements.data, products.data, search, warehouses.data])
  const filteredWarehouses = useMemo(() => warehouses.data?.items.filter((item) => `${item.code} ${item.name} ${item.location ?? ''}`.toLowerCase().includes(search.toLowerCase())) ?? [], [search, warehouses.data])

  async function createMovement(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setFormError('')
    const form = new FormData(event.currentTarget)
    const destination = form.get('destination_warehouse_id')
    try {
      await api('/inventory/movements', { method: 'POST', token, body: {
        movement_type: movementType, product_id: form.get('product_id'), warehouse_id: form.get('warehouse_id'),
        destination_warehouse_id: movementType === 'transfer' ? destination : null, quantity: form.get('quantity'),
        unit_cost: movementType === 'receipt' ? form.get('unit_cost') || null : null, reference: form.get('reference') || null,
        notes: form.get('notes') || null, allow_negative_override: user?.role === 'admin' && form.get('allow_negative_override') === 'on',
      } })
      setMovementModal(false); balances.refresh(); movements.refresh()
    } catch (reason) { setFormError(errorMessage(reason)) } finally { setBusy(false) }
  }

  async function createWarehouse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setFormError('')
    const form = new FormData(event.currentTarget)
    try {
      await api('/warehouses', { method: 'POST', token, body: { code: form.get('code'), name: form.get('name'), location: form.get('location') || null, is_active: true } })
      setWarehouseModal(false); warehouses.refresh(); balances.refresh()
    } catch (reason) { setFormError(errorMessage(reason)) } finally { setBusy(false) }
  }

  async function exportCsv() {
    setFormError('')
    try { await downloadCsv('/csv/inventory/export', token, 'opsforge-inventory.csv') }
    catch (reason) { setFormError(errorMessage(reason)) }
  }

  const activeResource = tab === 'balances' ? balances : tab === 'movements' ? movements : warehouses
  return <>
    <PageHeader eyebrow="Stock control" title="Inventory" description="See every balance and movement across your warehouse network." actions={<>{exportable && <Button variant="secondary" onClick={() => void exportCsv()}>Export CSV</Button>}{tab === 'warehouses' && canManageWarehouses && <Button variant="secondary" onClick={() => { setFormError(''); setWarehouseModal(true) }}><Icon name="plus"/> Warehouse</Button>}{writable && <Button onClick={() => { setFormError(''); setMovementModal(true) }}><Icon name="plus"/> Stock movement</Button>}</>} />
    <Panel>
      <div className="tab-bar"><div><button className={tab === 'balances' ? 'active' : ''} onClick={() => { setTab('balances'); setSearch('') }}>Balances</button><button className={tab === 'movements' ? 'active' : ''} onClick={() => { setTab('movements'); setSearch('') }}>Movement ledger</button><button className={tab === 'warehouses' ? 'active' : ''} onClick={() => { setTab('warehouses'); setSearch('') }}>Warehouses</button></div></div>
      <div className="table-toolbar"><SearchBox value={search} onChange={setSearch} placeholder={`Search ${tab}`}/><TableMeta total={tab === 'balances' ? filteredBalances.length : tab === 'movements' ? filteredMovements.length : filteredWarehouses.length} noun={tab === 'balances' ? 'balance' : tab === 'movements' ? 'movement' : 'warehouse'}/></div>
      {formError && !movementModal && !warehouseModal && <div className="inline-alert">{formError}</div>}
      {activeResource.loading && !activeResource.data ? <LoadingState/> : activeResource.error && !activeResource.data ? <ErrorState message={activeResource.error} retry={activeResource.refresh}/> : tab === 'balances' ? <BalanceTable items={filteredBalances}/> : tab === 'movements' ? <MovementTable items={filteredMovements} products={products.data?.items ?? []} warehouses={warehouses.data?.items ?? []}/> : <WarehouseTable items={filteredWarehouses}/>} 
    </Panel>
    {movementModal && <Modal title="Record stock movement" description="The balance, immutable ledger entry, and audit event commit together." onClose={() => setMovementModal(false)}><form className="modal-form" onSubmit={(event) => void createMovement(event)}><div className="form-grid"><Field label="Movement type"><select value={movementType} onChange={(event) => setMovementType(event.target.value as MovementType)}>{['receipt','sale_issue','transfer','return','adjustment'].map((value) => <option value={value} key={value}>{titleCase(value)}</option>)}</select></Field><Field label="Product"><select name="product_id" required defaultValue=""><option value="" disabled>Select product</option>{products.data?.items.map((item) => <option value={item.id} key={item.id}>{item.sku} — {item.name}</option>)}</select></Field><Field label={movementType === 'transfer' ? 'Source warehouse' : 'Warehouse'}><select name="warehouse_id" required defaultValue=""><option value="" disabled>Select warehouse</option>{warehouses.data?.items.filter((item) => item.is_active).map((item) => <option value={item.id} key={item.id}>{item.code} — {item.name}</option>)}</select></Field>{movementType === 'transfer' && <Field label="Destination warehouse"><select name="destination_warehouse_id" required defaultValue=""><option value="" disabled>Select destination</option>{warehouses.data?.items.filter((item) => item.is_active).map((item) => <option value={item.id} key={item.id}>{item.code} — {item.name}</option>)}</select></Field>}<Field label="Quantity" hint={movementType === 'adjustment' ? 'Use a negative number to reduce stock.' : undefined}><input name="quantity" type="number" step="0.001" defaultValue={movementType === 'adjustment' ? '0' : '1'} required/></Field>{movementType === 'receipt' && <Field label="Unit cost"><input name="unit_cost" type="number" min="0" step="0.01" placeholder="Optional"/></Field>}<Field label="Reference"><input name="reference" placeholder="Delivery, ticket, or document ID"/></Field><Field label="Notes"><input name="notes" placeholder="Operational context"/></Field></div>{user?.role === 'admin' && ['sale_issue','transfer','adjustment'].includes(movementType) && <label className="check-field"><input name="allow_negative_override" type="checkbox"/><span><strong>Allow negative inventory</strong><small>Admin exception; highlighted in the audit trail.</small></span></label>}{formError && <div className="form-error"><Icon name="alert" size={16}/>{formError}</div>}<div className="modal-actions"><Button type="button" variant="secondary" onClick={() => setMovementModal(false)}>Cancel</Button><Button type="submit" disabled={busy}>{busy ? 'Applying…' : 'Apply movement'}</Button></div></form></Modal>}
    {warehouseModal && <Modal title="Add warehouse" description="Existing products receive an initial zero balance here." onClose={() => setWarehouseModal(false)}><form className="modal-form" onSubmit={(event) => void createWarehouse(event)}><div className="form-grid"><Field label="Code"><input name="code" placeholder="e.g. WRO-01" required/></Field><Field label="Name"><input name="name" placeholder="Warehouse name" required/></Field><Field label="Location"><input name="location" placeholder="City or address"/></Field></div>{formError && <div className="form-error">{formError}</div>}<div className="modal-actions"><Button type="button" variant="secondary" onClick={() => setWarehouseModal(false)}>Cancel</Button><Button type="submit" disabled={busy}>{busy ? 'Creating…' : 'Create warehouse'}</Button></div></form></Modal>}
  </>
}

function BalanceTable({ items }: { items: InventoryBalance[] }) {
  if (!items.length) return <EmptyState title="No balances found" text="Try another search or create a product and warehouse."/>
  return <div className="table-scroll"><table><thead><tr><th>Product</th><th>Warehouse</th><th>On hand</th><th>Stock health</th><th>Last update</th></tr></thead><tbody>{items.map((item) => { const low = Number(item.quantity) <= 5; return <tr key={item.id}><td><div className="primary-cell"><span className="entity-icon product"><Icon name="products"/></span><span><strong>{item.product.name}</strong><small>{item.product.sku}</small></span></div></td><td><strong>{item.warehouse.code}</strong><small className="cell-note">{item.warehouse.name}</small></td><td className="mono quantity-cell">{quantity(item.quantity)} <small>{item.product.unit}</small></td><td><StatusBadge value={low ? 'low_stock' : 'healthy'}/></td><td className="muted">{dateTime(item.updated_at)}</td></tr> })}</tbody></table></div>
}

function MovementTable({ items, products, warehouses }: { items: StockMovement[]; products: Product[]; warehouses: Warehouse[] }) {
  if (!items.length) return <EmptyState title="No movements found" text="Movement history will appear here once stock changes."/>
  return <div className="table-scroll"><table><thead><tr><th>Movement</th><th>Product</th><th>Warehouse</th><th>Quantity</th><th>Reference</th><th>Recorded</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><StatusBadge value={item.movement_type}/></td><td><strong>{productName(item.product_id, products)}</strong></td><td>{warehouseName(item.warehouse_id, warehouses)}{item.destination_warehouse_id && <> → {warehouseName(item.destination_warehouse_id, warehouses)}</>}</td><td className="mono emphasis">{item.movement_type === 'sale_issue' ? '−' : ''}{quantity(item.quantity)}</td><td>{item.reference ?? '—'}</td><td className="muted">{dateTime(item.created_at)}</td></tr>)}</tbody></table></div>
}

function WarehouseTable({ items }: { items: Warehouse[] }) {
  if (!items.length) return <EmptyState title="No warehouses found" text="Add the first location to begin tracking inventory."/>
  return <div className="table-scroll"><table><thead><tr><th>Warehouse</th><th>Location</th><th>Status</th><th>Created</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><div className="primary-cell"><span className="entity-icon warehouse"><Icon name="warehouse"/></span><span><strong>{item.name}</strong><small>{item.code}</small></span></div></td><td>{item.location ?? '—'}</td><td><StatusBadge value={item.is_active ? 'active' : 'inactive'}/></td><td className="muted">{dateTime(item.created_at)}</td></tr>)}</tbody></table></div>
}

function productName(id: string, products: Product[] = []): string { return products.find((item) => item.id === id)?.sku ?? id.slice(0, 8) }
function warehouseName(id: string, warehouses: Warehouse[] = []): string { return warehouses.find((item) => item.id === id)?.code ?? id.slice(0, 8) }
