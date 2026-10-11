import { useEffect, useRef, useState } from 'react'
import { BookOpen, ChartColumn, Compass, House, Pencil, PanelLeftClose, PanelLeftOpen, Settings } from 'lucide-react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { Button } from './ui/button'

import { primaryPages, toolPages } from '../app/navigation'

const icons = [House, BookOpen, Pencil, ChartColumn, Compass]

export function MainNavigation() {
  const location = useLocation()
  const path = location.pathname.replace(/\/+$/, '').toLowerCase() || '/'
  const [collapsed, setCollapsed] = useState(false)
  const dialog = useRef<HTMLDialogElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const railToggle = useRef<HTMLButtonElement>(null)
  const primaryNav = useRef<HTMLElement>(null)
  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 48rem)')
    let toggleHadFocus = false
    const trackFocus = () => { toggleHadFocus = document.activeElement === railToggle.current }
    const restoreVisibleFocus = () => {
      if (!desktop.matches && (document.activeElement === railToggle.current ||
          (document.activeElement === document.body && toggleHadFocus))) {
        primaryNav.current?.querySelector<HTMLAnchorElement>('a[aria-current="page"], a')?.focus()
      }
    }
    document.addEventListener('focusin', trackFocus)
    desktop.addEventListener('change', restoreVisibleFocus)
    return () => {
      document.removeEventListener('focusin', trackFocus)
      desktop.removeEventListener('change', restoreVisibleFocus)
    }
  }, [])
  useEffect(() => { dialog.current?.close() }, [location.key])
  const primary = ['/session', '/recap', '/review'].includes(path) ? '/learn'
    : path === '/map' ? '/progress'
      : ['/search', '/sources', '/areas'].includes(path) ? '/explore' : path
  function close() { dialog.current?.close(); trigger.current?.focus() }
  return <aside className="shell-navigation-container" data-collapsed={collapsed}>
    <button ref={railToggle} className="shell-rail-toggle" aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
      aria-expanded={!collapsed} onClick={() => setCollapsed(!collapsed)}>
      {collapsed ? <PanelLeftOpen aria-hidden="true" size={20} /> : <PanelLeftClose aria-hidden="true" size={20} />}
    </button>
    <nav ref={primaryNav} className="shell-primary-navigation" aria-label="Main navigation">
      {primaryPages.map(([href, label], index) => {
        const Icon = icons[index]
        return <Link key={href} to={href} aria-label={label} title={collapsed ? label : undefined}
          aria-current={primary === href ? 'page' : undefined} className="shell-primary-link">
          <Icon aria-hidden="true" size={20} /><span className="shell-primary-label">{label}</span>
        </Link>
      })}
    </nav>
    <div className="shell-navigation-footer">
      <Button aria-haspopup="dialog" onClick={event => {
        trigger.current = event.currentTarget
        if (document.querySelector('dialog[open]')) return
        dialog.current?.showModal(); dialog.current?.querySelector<HTMLButtonElement>('button')?.focus()
      }}>Tools</Button>
      <Link to="/preferences" className="shell-preferences-link" aria-label="Preferences" aria-current={path === '/preferences' ? 'page' : undefined}><Settings aria-hidden="true" size={20} /><span className="shell-primary-label">Preferences</span></Link>
    </div>
    <dialog ref={dialog} className="shell-tools-dialog" aria-labelledby="shell-tools-title"
      onCancel={event => { event.preventDefault(); close() }}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line p-4">
        <h2 id="shell-tools-title" className="text-panel-heading font-semibold">Tools and pages</h2>
        <Button onClick={close}>Close tools</Button>
      </div>
      <nav aria-label="Tools and pages" className="grid gap-2 p-4">
        {toolPages.map(([href, label]) => <NavLink key={href} to={href} end={href !== '/answers'}
          className={({ isActive }) => `min-h-11 flex items-center rounded px-3 py-2 ${isActive ? 'bg-accent-tint font-semibold' : 'hover:bg-sunken'}`}
          onClick={event => {
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return
            dialog.current?.close()
            document.getElementById('main-content')?.focus()
          }}>{label}</NavLink>)}
      </nav>
    </dialog>
  </aside>
}
