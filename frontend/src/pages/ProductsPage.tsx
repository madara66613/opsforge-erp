import { type FormEvent, useMemo, useState } from 'react'

import { useAuth } from '../auth/useAuth'
import { Icon } from '../components/Icon'
import { Button, EmptyState, ErrorState, Field, LoadingState, Modal, PageHeader, Panel, SearchBox, StatusBadge, TableMeta } from '../components/ui'
import { useApiResource } from '../hooks/useApiResource'
import { api, downloadCsv, errorMessage, uploadCsv } from '../lib/api'
import { money, quantity } from '../lib/format'
import { can } from '../lib/permissions'
import type { ListResponse, Product, ProductImportSummary } from '../types'

export function ProductsPage() {
  const { token, user } = useAuth()
  const { data, loading, error, refresh } = useApiResource<ListResponse<Product>>('/products?limit=100&sort_by=sku', token)
  const [search, setSearch] = useState('')
  const [modal, setModal] = useState(false)
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')
  const [success, setSuccess] = useState('')
  const writable = Boolean(user && can(user.role, 'products.write'))
  const importable = Boolean(user && can(user.role, 'csv.import'))
  const exportable = Boolean(user && can(user.role, 'csv.export'))
  const products = useMemo(() => data?.items.filter((product) => `${product.sku} ${product.name}`.toLowerCase().includes(search.toLowerCase())) ?? [], [data, search])

  async function createProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true); setFormError('')
    const form = new FormData(event.currentTarget)
    try {
      await api('/products', { method: 'POST', token, body: {
        sku: form.get('sku'), name: form.get('name'), description: form.get('description') || null,
        unit: form.get('unit'), sale_price: form.get('sale_price'), purchase_price: form.get('purchase_price'),
        reorder_threshold: form.get('reorder_threshold'), is_active: true,
      } })
      setModal(false); setSuccess('Product created successfully.'); refresh()
    } catch (reason) { setFormError(errorMessage(reason)) } finally { setBusy(false) }
  }

  async function importCsv(file: File | undefined) {
    if (!file) return
    setFormError(''); setSuccess('')
    try {
      const result = await uploadCsv<ProductImportSummary>('/csv/products/import', token, file)
      setSuccess(`${result.products_created} product${result.products_created === 1 ? '' : 's'} imported. No partial rows were applied.`)
      refresh()
    } catch (reason) { setFormError(errorMessage(reason)) }
  }

  async function exportCsv() {
    setFormError('')
    try { await downloadCsv('/csv/products/export', token, 'opsforge-products.csv') }
    catch (reason) { setFormError(errorMessage(reason)) }
  }

  async function toggle(product: Product) {
    try {
      await api(`/products/${product.id}`, { method: 'PATCH', token, body: { is_active: !product.is_active } })
      refresh()
    } catch (reason) { setFormError(errorMessage(reason)) }
  }

  return <>
    <PageHeader eyebrow="Catalog" title="Products" description="Manage the items your teams buy, store, and sell." actions={<>{exportable && <Button variant="secondary" onClick={() => void exportCsv()}>Export CSV</Button>}{importable && <label className="button button-secondary file-button">Import CSV<input type="file" accept=".csv,text/csv" onChange={(event) => { void importCsv(event.target.files?.[0]); event.target.value = '' }}/></label>}{writable && <Button onClick={() => { setFormError(''); setSuccess(''); setModal(true) }}><Icon name="plus"/> New product</Button>}</>} />
    <Panel>
      <div className="table-toolbar"><SearchBox value={search} onChange={setSearch} placeholder="Search by SKU or product name"/><TableMeta total={products.length} noun="product"/></div>
      {success && <div className="inline-success">{success}</div>}{formError && !modal && <div className="inline-alert">{formError}</div>}
      {loading && !data ? <LoadingState/> : error && !data ? <ErrorState message={error} retry={refresh}/> : products.length === 0 ? <EmptyState title="No products found" text="Try another search or add the first catalog item."/> : <div className="table-scroll"><table><thead><tr><th>Product</th><th>Unit</th><th>Purchase</th><th>Sale</th><th>Reorder at</th><th>Status</th>{writable && <th className="align-right">Action</th>}</tr></thead><tbody>{products.map((product) => <tr key={product.id}><td><div className="primary-cell"><span className="entity-icon product"><Icon name="products"/></span><span><strong>{product.name}</strong><small>{product.sku}</small></span></div></td><td>{product.unit}</td><td className="mono">{money(product.purchase_price)}</td><td className="mono emphasis">{money(product.sale_price)}</td><td className="mono">{quantity(product.reorder_threshold)}</td><td><StatusBadge value={product.is_active ? 'active' : 'inactive'}/></td>{writable && <td className="align-right"><button className="row-action" onClick={() => void toggle(product)}>{product.is_active ? 'Deactivate' : 'Activate'}</button></td>}</tr>)}</tbody></table></div>}
    </Panel>
    {modal && <Modal title="Add product" description="New products receive a zero balance in every warehouse." onClose={() => setModal(false)}><form className="modal-form" onSubmit={(event) => void createProduct(event)}><div className="form-grid"><Field label="SKU"><input name="sku" placeholder="e.g. OF-1007" required maxLength={64}/></Field><Field label="Unit"><input name="unit" defaultValue="pcs" required maxLength={24}/></Field><Field label="Product name"><input name="name" placeholder="Product display name" required maxLength={160}/></Field><Field label="Purchase price"><input name="purchase_price" type="number" min="0" step="0.01" defaultValue="0.00" required/></Field><Field label="Sale price"><input name="sale_price" type="number" min="0" step="0.01" defaultValue="0.00" required/></Field><Field label="Reorder threshold" hint="Balance at or below this level is low stock."><input name="reorder_threshold" type="number" min="0" step="0.001" defaultValue="5" required/></Field><Field label="Description"><input name="description" placeholder="Optional short description"/></Field></div>{formError && <div className="form-error"><Icon name="alert" size={16}/>{formError}</div>}<div className="modal-actions"><Button type="button" variant="secondary" onClick={() => setModal(false)}>Cancel</Button><Button type="submit" disabled={busy}>{busy ? 'Creating…' : 'Create product'}</Button></div></form></Modal>}
  </>
}
