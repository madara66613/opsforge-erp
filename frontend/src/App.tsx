import { Redirect, Route, Switch } from 'wouter'

import { useAuth } from './auth/useAuth'
import { AppShell } from './components/AppShell'
import { EmptyState, Panel } from './components/ui'
import type { Permission } from './lib/permissions'
import { can } from './lib/permissions'
import { AuditPage } from './pages/AuditPage'
import { DashboardPage } from './pages/DashboardPage'
import { InventoryPage } from './pages/InventoryPage'
import { LoginPage } from './pages/LoginPage'
import { OrdersPage } from './pages/OrdersPage'
import { PartnersPage } from './pages/PartnersPage'
import { ProductsPage } from './pages/ProductsPage'
import { SystemPage } from './pages/SystemPage'
import { UsersPage } from './pages/UsersPage'

function App() {
  const { user, checking } = useAuth()
  if (checking) return <div className="app-loading"><span className="brand-symbol large"><span>O</span></span><span className="spinner"/><p>Restoring secure workspace…</p></div>
  if (!user) return <LoginPage />

  return <AppShell><Switch>
    <Route path="/"><Guard permission="dashboard.read"><DashboardPage/></Guard></Route>
    <Route path="/products"><Guard permission="products.read"><ProductsPage/></Guard></Route>
    <Route path="/inventory"><Guard permission="inventory.read"><InventoryPage/></Guard></Route>
    <Route path="/partners"><Guard permission="partners.read"><PartnersPage/></Guard></Route>
    <Route path="/sales"><Guard permission="sales.read"><OrdersPage kind="sales"/></Guard></Route>
    <Route path="/purchases"><Guard permission="purchases.read"><OrdersPage kind="purchases"/></Guard></Route>
    <Route path="/audit"><Guard permission="audit.read"><AuditPage/></Guard></Route>
    <Route path="/users"><Guard permission="users.read"><UsersPage/></Guard></Route>
    <Route path="/system"><Guard permission="system.read"><SystemPage/></Guard></Route>
    <Route><Redirect to="/" /></Route>
  </Switch></AppShell>
}

function Guard({ permission, children }: { permission: Permission; children: React.ReactNode }) {
  const { user } = useAuth()
  if (!user || !can(user.role, permission)) return <Panel><EmptyState title="Access restricted" text="Your role does not include permission for this workspace."/></Panel>
  return children
}

export default App
