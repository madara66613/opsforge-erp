type IconName =
  | 'dashboard' | 'products' | 'inventory' | 'partners' | 'sales' | 'purchases'
  | 'audit' | 'users' | 'system' | 'search' | 'plus' | 'logout' | 'menu'
  | 'arrow' | 'activity' | 'warehouse' | 'package' | 'alert' | 'close'

const paths: Record<IconName, React.ReactNode> = {
  dashboard: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
  products: <><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="m4.3 7.7 7.7 4.4 7.7-4.4M12 12.1V21"/></>,
  inventory: <><path d="M4 7h16v14H4zM2 3h20v4H2z"/><path d="M9 11h6"/></>,
  partners: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></>,
  sales: <><path d="M3 3h2l2.5 12h10l2-8H7"/><circle cx="9" cy="20" r="1"/><circle cx="17" cy="20" r="1"/><path d="M10 10h5M12.5 7.5v5"/></>,
  purchases: <><path d="M6 2h12l2 5-8 4-8-4 2-5Z"/><path d="M4 7v11l8 4 8-4V7M12 11v11"/></>,
  audit: <><path d="M9 11h6M9 15h6M10 3h4l1 2h4v16H5V5h4l1-2Z"/><path d="m7.5 11 .5.5 1-1M7.5 15l.5.5 1-1"/></>,
  users: <><circle cx="9" cy="8" r="4"/><path d="M3 21v-2a6 6 0 0 1 12 0v2M16 11a4 4 0 0 1 5 4v3"/></>,
  system: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9A1.7 1.7 0 0 0 21 10h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/></>,
  search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
  plus: <path d="M12 5v14M5 12h14"/>,
  logout: <><path d="M10 17l5-5-5-5M15 12H3M21 3v18h-8"/></>,
  menu: <path d="M4 7h16M4 12h16M4 17h16"/>,
  arrow: <path d="m9 18 6-6-6-6"/>,
  activity: <path d="M3 12h4l2-7 4 14 2-7h6"/>,
  warehouse: <><path d="M3 10 12 3l9 7v11H3V10Z"/><path d="M7 21v-7h10v7M9 10h6"/></>,
  package: <><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="m4.3 7.7 7.7 4.4 7.7-4.4"/></>,
  alert: <><path d="M12 3 2.5 20h19L12 3Z"/><path d="M12 9v5M12 17h.01"/></>,
  close: <path d="m6 6 12 12M18 6 6 18"/>,
}

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}
