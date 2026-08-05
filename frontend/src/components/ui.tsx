import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { Icon } from './Icon'

export function Button({ variant = 'primary', children, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger' }) {
  return <button className={`button button-${variant}`} {...props}>{children}</button>
}

export function StatusBadge({ value }: { value: string }) {
  return <span className={`badge badge-${value}`}>{value.replaceAll('_', ' ')}</span>
}

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow: string; title: string; description: string; actions?: ReactNode }) {
  return <header className="page-header"><div><p className="page-eyebrow">{eyebrow}</p><h1>{title}</h1><p>{description}</p></div>{actions && <div className="page-actions">{actions}</div>}</header>
}

export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{children}</section>
}

export function EmptyState({ title, text }: { title: string; text: string }) {
  return <div className="empty-state"><span className="empty-icon"><Icon name="package" size={24} /></span><strong>{title}</strong><p>{text}</p></div>
}

export function LoadingState({ label = 'Loading operational data…' }: { label?: string }) {
  return <div className="loading-state"><span className="spinner" />{label}</div>
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return <div className="error-state"><Icon name="alert"/><div><strong>Unable to load data</strong><p>{message}</p></div>{retry && <Button variant="secondary" onClick={retry}>Retry</Button>}</div>
}

export function Modal({ title, description, children, onClose }: { title: string; description?: string; children: ReactNode; onClose: () => void }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><header><div><h2 id="modal-title">{title}</h2>{description && <p>{description}</p>}</div><button className="icon-button" onClick={onClose} aria-label="Close"><Icon name="close" /></button></header>{children}</section></div>
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return <label className="field"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>
}

export function SearchBox({ value, onChange, placeholder = 'Search' }: { value: string; onChange: (value: string) => void; placeholder?: string }) {
  return <label className="search-box"><Icon name="search" size={16}/><input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} /></label>
}

export function TableMeta({ total, noun }: { total: number; noun: string }) {
  return <span className="table-meta">{total} {total === 1 ? noun : `${noun}s`}</span>
}
