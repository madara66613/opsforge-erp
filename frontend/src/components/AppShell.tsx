import { type ReactNode, useState } from 'react'
import { Link, useLocation } from 'wouter'

import { useAuth } from '../auth/useAuth'
import { can, type Permission } from '../lib/permissions'
import { initials, titleCase } from '../lib/format'
import { Icon } from './Icon'

type IconName = Parameters<typeof Icon>[0]['name']

interface NavItem {
  path: string
  label: string
  icon: IconName
  permission: Permission
}

const operations: NavItem[] = [
  { path: '/', label: 'Overview', icon: 'dashboard', permission: 'dashboard.read' },
  { path: '/products', label: 'Products', icon: 'products', permission: 'products.read' },
  { path: '/inventory', label: 'Inventory', icon: 'inventory', permission: 'inventory.read' },
  { path: '/partners', label: 'Partners', icon: 'partners', permission: 'partners.read' },
  { path: '/sales', label: 'Sales orders', icon: 'sales', permission: 'sales.read' },
  { path: '/purchases', label: 'Purchases', icon: 'purchases', permission: 'purchases.read' },
]

const control: NavItem[] = [
  { path: '/audit', label: 'Audit log', icon: 'audit', permission: 'audit.read' },
  { path: '/users', label: 'Users & roles', icon: 'users', permission: 'users.read' },
  { path: '/system', label: 'System status', icon: 'system', permission: 'system.read' },
]

export function AppShell({ children }: { children: ReactNode }) {
  const { user, signOut } = useAuth()
  const [location] = useLocation()
  const [open, setOpen] = useState(false)
  if (!user) return null

  const renderItems = (items: NavItem[]) => items.filter((item) => can(user.role, item.permission)).map((item) => {
    const active = item.path === '/' ? location === '/' : location.startsWith(item.path)
    return <Link key={item.path} href={item.path} className={`nav-link${active ? ' active' : ''}`} onClick={() => setOpen(false)}><Icon name={item.icon}/><span>{item.label}</span>{active && <span className="nav-active-dot"/>}</Link>
  })

  const current = [...operations, ...control].find((item) => item.path === '/' ? location === '/' : location.startsWith(item.path))

  return <div className="app-shell">
    <aside className={`sidebar${open ? ' sidebar-open' : ''}`}>
      <Link href="/" className="app-brand" onClick={() => setOpen(false)}><span className="brand-symbol"><span>O</span></span><span><strong>OpsForge</strong><small>ERP workspace</small></span></Link>
      <nav aria-label="Main navigation">
        <p className="nav-label">Operations</p>{renderItems(operations)}
        <p className="nav-label nav-label-spaced">Control center</p>{renderItems(control)}
      </nav>
      <div className="sidebar-footer"><div className="environment"><span className="live-dot"/><div><strong>Systems operational</strong><small>Local environment</small></div></div></div>
    </aside>
    {open && <button className="sidebar-overlay" aria-label="Close navigation" onClick={() => setOpen(false)} />}
    <div className="workspace">
      <header className="workspace-bar">
        <div className="workspace-context"><button className="menu-button" onClick={() => setOpen(true)} aria-label="Open navigation"><Icon name="menu"/></button><span>Operations</span><Icon name="arrow" size={13}/><strong>{current?.label ?? 'Workspace'}</strong></div>
        <div className="user-menu"><span className="user-avatar">{initials(user.full_name)}</span><div><strong>{user.full_name}</strong><small>{titleCase(user.role)}</small></div><button className="icon-button" onClick={() => void signOut()} aria-label="Sign out" title="Sign out"><Icon name="logout"/></button></div>
      </header>
      <main className="page-content">{children}</main>
      <footer className="app-footer"><span>OpsForge ERP · Fictional portfolio system</span><span>Operational data is local to this demo</span></footer>
    </div>
  </div>
}
