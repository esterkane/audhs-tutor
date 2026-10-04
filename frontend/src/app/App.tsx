import { BrowseArea } from '../features/areas/BrowseArea'
import { AudioControls } from '../features/audio/AudioControls'
import { LearningCompanion } from '../features/programs/LearningCompanion'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useLayoutEffect, useRef, useState } from 'react'
import { BrowserRouter, Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { ParkingLotButton } from '../components/ParkingLotButton'
import { Corpus } from '../routes/Corpus'
import { Answers } from '../routes/Answers'
import { Areas } from '../routes/Areas'
import { Curriculum } from '../routes/Curriculum'
import { Experiments } from '../routes/Experiments'
import { Home } from '../routes/Home'
import { Map } from '../routes/Map'
import { Models } from '../routes/Models'
import { Together } from '../routes/Together'
import { Vocab } from '../routes/Vocab'
import { useSensory } from '../features/sensory/useSensory'
import { Preferences } from '../routes/Preferences'
import { Recap } from '../routes/Recap'
import { Review } from '../routes/Review'
import { Session } from '../routes/Session'
import { Visualizer } from '../routes/Visualizer'
import { Programs } from '../routes/Programs'
import { Playground } from '../routes/Playground'
import { MODE_LABELS, useMode } from '../stores/mode'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

const primaryPages = [
  ['/', 'Home'],
  ['/programs', 'Project study'],
] as const
const navigationGroups: ReadonlyArray<{ label: string; pages: ReadonlyArray<readonly [string, string]> }> = [
  { label: 'Learn', pages: [['/', 'Start or resume'], ['/review', 'Review'], ['/vocab', 'Vocabulary'], ['/together', 'Work alongside']] },
  { label: 'Explore', pages: [['/areas', 'Learning areas'], ['/map', 'Skill map']] },
  { label: 'Library', pages: [['/answers', 'Saved answers']] },
  { label: 'Tools', pages: [['/playground', 'Playground'], ['/playground/visualizer', 'Audio visualizer']] },
  { label: 'Manage', pages: [['/corpus', 'Materials'], ['/curriculum', 'Lesson drafts'], ['/models', 'Models'], ['/experiments', 'Experiments'], ['/preferences', 'Preferences']] },
] as const
const toolPages = navigationGroups.flatMap(group => group.pages).filter(([path]) => path !== '/')
const pageTitles: Record<string, string> = {
  ...Object.fromEntries([...primaryPages, ...toolPages]),
  '/programs': 'Project study',
  '/session': 'Learning session',
  '/review': 'Review',
  '/recap': 'Session recap',
}

export function Shell({ children }: { children: React.ReactNode }) {
  const { mode, energy, sessionId } = useMode()
  useSensory()
  const pathname = useLocation().pathname
  const routePath = pathname.replace(/\/+$/, '').toLowerCase() || '/'
  const main = useRef<HTMLElement>(null)
  const lastPath = useRef(pathname)
  const title = routePath.startsWith('/answers/') ? 'Saved answer' : (pageTitles[routePath] ?? 'Page not found')
  useLayoutEffect(() => {
    document.title = `${title} · AuDHS Tutor`
    if (lastPath.current !== pathname) {
      lastPath.current = pathname
      main.current?.focus()
    }
  }, [pathname, title])
  const wide = ['/playground', '/programs'].some((path) => pathname.startsWith(path))
  const navClass = ({ isActive }: { isActive: boolean }) =>
    `rounded px-2 py-1 ${isActive ? 'bg-accent text-accent-fg font-semibold' : 'underline-offset-4 hover:underline'}`
  return (
    <div className="min-h-screen">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:block focus:p-3 focus:bg-card">
        Skip to learning content
      </a>
      <header className="grid gap-3 px-4 py-3 border-b border-line bg-card">
        <div className="flex flex-wrap gap-3 items-center justify-between">
          <Link to="/" className="font-semibold no-underline text-fg">
            AuDHS-Tutor
          </Link>
          <div className="flex flex-wrap items-start gap-2 min-w-0 max-w-full">
            <AudioControls />
            <ParkingLotButton />
          </div>
        </div>
        <BrowseArea />
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
          <span>
            {MODE_LABELS[mode].title} · energy {energy}
          </span>
          {sessionId && (
            <Link to="/" className="underline">
              Resume or manage session
            </Link>
          )}
        </div>
      </header>
      <div className="shell-workspace">
        <ResponsiveNavigation key={pathname} title={title}>
          <NavLink to="/" end className={navClass}>Home</NavLink>
          {navigationGroups.map((group, index) => {
            const selected = group.pages.find(([path]) => path !== '/' &&
              (routePath === path || (path === '/answers' && routePath.startsWith('/answers/'))))
            const currentLabel = selected?.[1] ?? (group.label === 'Learn' && ['/session', '/recap'].includes(routePath) ? title : null)
            return (
              <div key={group.label} className="contents">
                {index === 2 && <NavLink to="/programs" end className={navClass}>Projects</NavLink>}
                <details key={`${pathname}:${group.label}`} className="min-w-0 max-w-full">
                  <summary className={`cursor-pointer rounded px-2 py-1 ${currentLabel ? 'bg-accent text-accent-fg font-semibold' : ''}`}>
                    {group.label}{currentLabel ? ` · ${currentLabel}` : ''}
                  </summary>
                  <div className="grid gap-2 p-3 mt-2 rounded-lg border border-line bg-card">
                    {group.pages.map(([path, label]) => (
                      <NavLink key={path} to={path} end={path !== '/answers'} className={navClass}>
                        {label}
                      </NavLink>
                    ))}
                  </div>
                </details>
              </div>
            )
          })}
        </ResponsiveNavigation>
      <div className="min-w-0">
      <main
        id="main-content"
        ref={main}
        tabIndex={-1}
        className={`${wide ? 'max-w-7xl' : 'max-w-4xl'} w-full mx-auto p-4 pb-24`}
      >
        {children}
      </main>
      <LearningCompanion key={pathname} />
      </div>
      </div>
    </div>
  )
}

function ResponsiveNavigation({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const trigger = useRef<HTMLButtonElement>(null)
  const nav = useRef<HTMLElement>(null)
  const lastNavigationFocus = useRef<Element | null>(null)
  useLayoutEffect(() => {
    const desktop = window.matchMedia('(min-width: 64rem)')
    const trackFocus = () => {
      const active = document.activeElement
      lastNavigationFocus.current = active === trigger.current || nav.current?.contains(active) ? active : null
    }
    const restoreVisibleFocus = () => {
      // CSS can blur a newly hidden control before the media-query event arrives.
      const active = document.activeElement === document.body ? lastNavigationFocus.current : document.activeElement
      if (!desktop.matches && !open && nav.current?.contains(active)) trigger.current?.focus()
      if (desktop.matches && active === trigger.current) nav.current?.querySelector<HTMLAnchorElement>('a')?.focus()
    }
    document.addEventListener('focusin', trackFocus)
    desktop.addEventListener('change', restoreVisibleFocus)
    return () => {
      desktop.removeEventListener('change', restoreVisibleFocus)
      document.removeEventListener('focusin', trackFocus)
    }
  }, [open])
  return <div className="shell-navigation-container">
    <button ref={trigger} type="button" className="shell-menu-toggle" aria-expanded={open}
      aria-controls="main-navigation" onClick={() => setOpen(!open)}>
      {open ? 'Close menu' : 'Menu'} · {title}
    </button>
    <nav ref={nav} id="main-navigation" aria-label="Main navigation" data-open={open}
      className="shell-navigation flex flex-wrap gap-2 text-sm items-start"
      onKeyDown={event => {
        if (event.key === 'Escape' && open) { setOpen(false); trigger.current?.focus() }
      }}
      onClick={event => {
        const link = (event.target as HTMLElement).closest('a')
        if (link && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
          setOpen(false)
          document.getElementById('main-content')?.focus()
        }
      }}>
      {children}
    </nav>
  </div>
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Shell>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/answers" element={<Answers />} />
            <Route path="/answers/:answerId" element={<Answers />} />
            <Route path="/session" element={<Session />} />
            <Route path="/playground" element={<Playground />} />
            <Route path="/playground/visualizer" element={<Visualizer />} />
            <Route path="/review" element={<Review />} />
            <Route path="/recap" element={<Recap />} />
            <Route path="/map" element={<Map />} />
            <Route path="/preferences" element={<Preferences />} />
            <Route path="/corpus" element={<Corpus />} />
            <Route path="/areas" element={<Areas />} />
            <Route path="/programs" element={<Programs />} />
            <Route path="/curriculum" element={<Curriculum />} />
            <Route path="/models" element={<Models />} />
            <Route path="/experiments" element={<Experiments />} />
            <Route path="/vocab" element={<Vocab />} />
            <Route path="/together" element={<Together />} />
            <Route
              path="*"
              element={
                <div>
                  <h1 className="text-2xl font-semibold">Page not found</h1>
                  <p>This address does not match a learning page.</p>
                  <Link to="/" className="underline">
                    Return Home
                  </Link>
                </div>
              }
            />
          </Routes>
        </Shell>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
