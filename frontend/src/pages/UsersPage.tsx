import { type FormEvent, useState } from 'react'

import { useAuth } from '../auth/useAuth'
import { Icon } from '../components/Icon'
import { Button, EmptyState, ErrorState, Field, LoadingState, Modal, PageHeader, Panel, StatusBadge, TableMeta } from '../components/ui'
import { useApiResource } from '../hooks/useApiResource'
import { api, errorMessage } from '../lib/api'
import { dateTime, initials, titleCase } from '../lib/format'
import { can } from '../lib/permissions'
import type { ListResponse, User } from '../types'

export function UsersPage() {
  const { token, user } = useAuth()
  const { data, loading, error, refresh } = useApiResource<ListResponse<User>>('/users?limit=100', token)
  const [modal, setModal] = useState(false)
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')
  const manageable = Boolean(user && can(user.role, 'users.manage'))

  async function createUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setFormError('')
    const form = new FormData(event.currentTarget)
    try {
      await api('/users', { method: 'POST', token, body: { email: form.get('email'), full_name: form.get('full_name'), password: form.get('password'), role: form.get('role') } })
      setModal(false); refresh()
    } catch (reason) { setFormError(errorMessage(reason)) } finally { setBusy(false) }
  }

  async function toggle(target: User) {
    try { await api(`/users/${target.id}`, { method: 'PATCH', token, body: { is_active: !target.is_active } }); refresh() }
    catch (reason) { setFormError(errorMessage(reason)) }
  }

  return <>
    <PageHeader eyebrow="Access control" title="Users & roles" description="Review who can access the workspace and which operational role they hold." actions={manageable && <Button onClick={() => { setFormError(''); setModal(true) }}><Icon name="plus"/> New user</Button>}/>
    <Panel><div className="table-toolbar"><div className="role-legend"><span><i className="role-dot admin"/>Admin</span><span><i className="role-dot operator"/>Operator</span><span><i className="role-dot support"/>Support</span></div><TableMeta total={data?.total ?? 0} noun="user"/></div>{formError && !modal && <div className="inline-alert">{formError}</div>}{loading && !data ? <LoadingState/> : error && !data ? <ErrorState message={error} retry={refresh}/> : !data?.items.length ? <EmptyState title="No users found" text="Create the first workspace account."/> : <div className="table-scroll"><table><thead><tr><th>User</th><th>Role</th><th>Status</th><th>Last sign-in</th><th>Created</th>{manageable && <th className="align-right">Action</th>}</tr></thead><tbody>{data.items.map((target) => <tr key={target.id}><td><div className="primary-cell"><span className={`user-avatar table-avatar role-${target.role}`}>{initials(target.full_name)}</span><span><strong>{target.full_name}{target.id === user?.id && <em className="you-label">You</em>}</strong><small>{target.email}</small></span></div></td><td><StatusBadge value={target.role}/></td><td><StatusBadge value={target.is_active ? 'active' : 'inactive'}/></td><td className="muted">{dateTime(target.last_login_at)}</td><td className="muted">{dateTime(target.created_at)}</td>{manageable && <td className="align-right"><button className="row-action" disabled={target.id === user?.id} onClick={() => void toggle(target)}>{target.is_active ? 'Deactivate' : 'Activate'}</button></td>}</tr>)}</tbody></table></div>}</Panel>
    <section className="permission-cards"><PermissionCard role="Admin" text="Full system control, user management, audit access, and negative stock override."/><PermissionCard role="Operator" text="Runs catalog, partner, inventory, sales, purchase, and CSV workflows."/><PermissionCard role="Support" text="Read-only operational visibility plus user, audit, system, and export access."/></section>
    {modal && <Modal title="Create workspace user" description="Assign the least-privileged role that fits this person's responsibilities." onClose={() => setModal(false)}><form className="modal-form" onSubmit={(event) => void createUser(event)}><div className="form-grid"><Field label="Full name"><input name="full_name" placeholder="First and last name" minLength={2} required/></Field><Field label="Email"><input name="email" type="email" placeholder="name@company.com" required/></Field><Field label="Role"><select name="role" defaultValue="support"><option value="admin">Admin</option><option value="operator">Operator</option><option value="support">Support</option></select></Field><Field label="Temporary password" hint="At least 12 characters."><input name="password" type="password" minLength={12} required/></Field></div>{formError && <div className="form-error"><Icon name="alert" size={16}/>{formError}</div>}<div className="modal-actions"><Button type="button" variant="secondary" onClick={() => setModal(false)}>Cancel</Button><Button type="submit" disabled={busy}>{busy ? 'Creating…' : 'Create user'}</Button></div></form></Modal>}
  </>
}

function PermissionCard({ role, text }: { role: string; text: string }) { return <article><span className={`role-dot ${role.toLowerCase()}`}/><div><strong>{titleCase(role)}</strong><p>{text}</p></div></article> }
