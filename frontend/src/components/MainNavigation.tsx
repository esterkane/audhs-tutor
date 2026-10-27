import { useEffect, useRef, useState } from 'react'
import { BookOpen, ChartColumn, Compass, House, MessageCircle, PanelLeftClose, PanelLeftOpen, Settings } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

import { primaryPages } from '../app/navigation'

const icons = [House, BookOpen, ChartColumn, Compass, MessageCircle, Settings]

export function MainNavigation() {
  const location = useLocation()
  const path = location.pathname.replace(/\/+$/, '').toLowerCase() || '/'
  const [collapsed, setCollapsed] = useState(false)
  const railToggle = useRef<HTMLButtonElement>(null)
  const primaryNav = useRef<HTMLElement>(null)
  useEffect(() => {
    const nav = primaryNav.current
    if (!nav || typeof ResizeObserver === 'undefined') return
    const root = document.documentElement
    const measure = () => {
      const height = getComputedStyle(nav).position === 'fixed' ? nav.getBoundingClientRect().height : 0
      root.style.setProperty('--shell-bottom-nav-height', `${height}px`)
    }
    const observer = new ResizeObserver(measure)
    observer.observe(nav)
    window.addEventListener('resize', measure)
    measure()
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', measure)
      root.style.removeProperty('--shell-bottom-nav-height')
    }
  }, [])
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
  const primary = ['/session', '/recap', '/review', '/learn', '/practice'].includes(path) ? '/'
    : ['/map', '/explore'].includes(path) ? '/progress'
    : ['/search', '/sources', '/areas', '/corpus', '/answers', '/curriculum'].some(p => path === p || path.startsWith(p + '/')) ? '/library'
    : path.startsWith('/projects/') || path === '/programs' ? '/projects'
    : ['/models', '/experiments', '/corrections', '/vocab', '/together', '/playground', '/task-review'].some(p => path === p || path.startsWith(p + '/')) ? '/preferences' : path
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
  </aside>
}
