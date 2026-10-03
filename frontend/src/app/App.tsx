import { AudioControls } from '../features/audio/AudioControls'
import { LearningCompanion } from '../features/programs/LearningCompanion'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useLayoutEffect, useRef } from 'react'
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
  ['/areas', 'Learning areas'],
  ['/programs', 'Project study'],
  ['/playground', 'Playground'],
  ['/playground/visualizer', 'Audio visualizer'],
] as const
const toolPages = [
  ['/answers', 'Saved answers'],
  ['/map', 'Skill map'],
  ['/together', 'Together'],
  ['/experiments', 'Experiments'],
  ['/vocab', 'Vocabulary'],
  ['/corpus', 'Materials'],
  ['/curriculum', 'Lesson drafts'],
  ['/models', 'Models'],
  ['/preferences', 'Preferences'],
] as const
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
  const selectedTool = toolPages.find(
    ([path]) => routePath === path || (path === '/answers' && routePath.startsWith('/answers/')),
  )
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
          <AudioControls />
        </div>
        <nav aria-label="Main navigation" className="flex flex-wrap gap-2 text-sm items-start">
          {primaryPages.map(([path, label]) => (
            <NavLink key={path} to={path} end className={navClass}>
              {label}
            </NavLink>
          ))}
          <details key={pathname} className="min-w-0">
            <summary className="cursor-pointer px-2 py-1">
              More tools{selectedTool ? ` · ${selectedTool[1]}` : ''}
            </summary>
            <div className="grid gap-2 p-3 mt-2 rounded-lg border border-line bg-card">
              {toolPages.map(([path, label]) => (
                <NavLink key={path} to={path} end={path !== '/answers'} className={navClass}>
                  {label}
                </NavLink>
              ))}
            </div>
          </details>
        </nav>
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
      <main
        id="main-content"
        ref={main}
        tabIndex={-1}
        className={`${wide ? 'max-w-7xl' : 'max-w-3xl'} mx-auto p-4 pb-24`}
      >
        {children}
      </main>
      <LearningCompanion key={pathname} />
      <ParkingLotButton />
    </div>
  )
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
