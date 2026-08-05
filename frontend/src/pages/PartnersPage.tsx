import { type FormEvent, useMemo, useState } from 'react'

import { useAuth } from '../auth/useAuth'
import { Icon } from '../components/Icon'
import { Button, EmptyState, ErrorState, Field, LoadingState, Modal, PageHeader, Panel, SearchBox, StatusBadge, TableMeta } from '../components/ui'
import { useApiResource } from '../hooks/useApiResource'
import { api, errorMessage } from '../lib/api'
import { can } from '../lib/permissions'
import type { ListResponse, Partner, PartnerType } from '../types'

export function PartnersPage() {
  const { token, user } = useAuth()
  const { data, loading, error, refresh } = useApiResource<ListResponse<Partner>>('/partners?limit=100', token)
  const [search, setSearch] = useState('')
  const [type, setType] = useState<PartnerType | 'all'>('all')
  const [modal, setModal] = useState(false)
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')
  const writable = Boolean(user && can(user.role, 'partners.write'))
  const partners = useMemo(() => data?.items.filter((partner) => (type === 'all' || partner.partner_type === type || partner.partner_type === 'both') && `${partner.code} ${partner.name} ${partner.tax_id ?? ''}`.toLowerCase().includes(search.toLowerCase())) ?? [], [data, search, type])

  async function createPartner(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setFormError('')
    const form = new FormData(event.currentTarget)
    try {
      await api('/partners', { method: 'POST', token, body: {
        code: form.get('code'), name: form.get('name'), partner_type: form.get('partner_type'), email: form.get('email') || null,
        phone: form.get('phone') || null, tax_id: form.get('tax_id') || null, address: form.get('address') || null, is_active: true,
      } })
      setModal(false); refresh()
    } catch (reason) { setFormError(errorMessage(reason)) } finally { setBusy(false) }
  }

  async function toggle(partner: Partner) {
    try { await api(`/partners/${partner.id}`, { method: 'PATCH', token, body: { is_active: !partner.is_active } }); refresh() }
    catch (reason) { setFormError(errorMessage(reason)) }
  }

  return <>
    <PageHeader eyebrow="Business network" title="Partners" description="Keep customer and supplier information connected to every order." actions={writable && <Button onClick={() => { setFormError(''); setModal(true) }}><Icon name="plus"/> New partner</Button>}/>
    <Panel>
      <div className="filter-row"><SearchBox value={search} onChange={setSearch} placeholder="Search code, name, or tax ID"/><div className="segmented">{(['all','customer','supplier'] as const).map((value) => <button key={value} className={type === value ? 'active' : ''} onClick={() => setType(value)}>{value === 'all' ? 'All partners' : `${value}s`}</button>)}</div><TableMeta total={partners.length} noun="partner"/></div>
      {formError && !modal && <div className="inline-alert">{formError}</div>}
      {loading && !data ? <LoadingState/> : error && !data ? <ErrorState message={error} retry={refresh}/> : partners.length === 0 ? <EmptyState title="No partners found" text="Adjust the filters or add a customer or supplier."/> : <div className="table-scroll"><table><thead><tr><th>Partner</th><th>Type</th><th>Contact</th><th>Tax ID</th><th>Status</th>{writable && <th className="align-right">Action</th>}</tr></thead><tbody>{partners.map((partner) => <tr key={partner.id}><td><div className="primary-cell"><span className="entity-icon partner"><Icon name="partners"/></span><span><strong>{partner.name}</strong><small>{partner.code}</small></span></div></td><td><StatusBadge value={partner.partner_type}/></td><td><strong>{partner.email ?? '—'}</strong><small className="cell-note">{partner.phone ?? 'No phone'}</small></td><td className="mono">{partner.tax_id ?? '—'}</td><td><StatusBadge value={partner.is_active ? 'active' : 'inactive'}/></td>{writable && <td className="align-right"><button className="row-action" onClick={() => void toggle(partner)}>{partner.is_active ? 'Deactivate' : 'Activate'}</button></td>}</tr>)}</tbody></table></div>}
    </Panel>
    {modal && <Modal title="Add partner" description="Choose the relationship type to control which orders may use this partner." onClose={() => setModal(false)}><form className="modal-form" onSubmit={(event) => void createPartner(event)}><div className="form-grid"><Field label="Partner code"><input name="code" placeholder="e.g. CUST-104" required/></Field><Field label="Relationship"><select name="partner_type" defaultValue="customer"><option value="customer">Customer</option><option value="supplier">Supplier</option><option value="both">Customer & supplier</option></select></Field><Field label="Business name"><input name="name" placeholder="Legal or trading name" required/></Field><Field label="Tax ID"><input name="tax_id" placeholder="Optional"/></Field><Field label="Email"><input name="email" type="email" placeholder="operations@example.com"/></Field><Field label="Phone"><input name="phone" placeholder="Optional"/></Field><Field label="Address"><input name="address" placeholder="Optional registered address"/></Field></div>{formError && <div className="form-error"><Icon name="alert" size={16}/>{formError}</div>}<div className="modal-actions"><Button type="button" variant="secondary" onClick={() => setModal(false)}>Cancel</Button><Button type="submit" disabled={busy}>{busy ? 'Creating…' : 'Create partner'}</Button></div></form></Modal>}
  </>
}
