import { LessonFocusContext } from '../features/session/focusContext'
import { MainNavigation } from '../components/MainNavigation'
import { primaryPages, toolPages } from './navigation'
import { CorrectionEditor } from '../features/questions/CorrectionEditor'
import { Brand } from '../components/Brand'
import { QuickNavigation } from '../components/QuickNavigation'
import { BrowseArea } from '../features/areas/BrowseArea'
import { AudioControls } from '../features/audio/AudioControls'
import { LearningCompanion } from '../features/programs/LearningCompanion'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom'
import { ParkingLotButton } from '../components/ParkingLotButton'
import { Corpus } from '../routes/Corpus'
import { Search } from '../routes/Search'
import { Sources } from '../routes/Sources'
import { Answers } from '../routes/Answers'
import { Areas } from '../routes/Areas'
import { Curriculum } from '../routes/Curriculum'
import { Experiments } from '../routes/Experiments'
import { Home } from '../routes/Home'
import { Learn } from '../routes/Learn'
import { Practice } from '../routes/Practice'
import { Progress } from '../routes/Progress'
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

const pageTitles: Record<string, string> = {
  ...Object.fromEntries([...primaryPages, ...toolPages]),
  '/programs': 'Project study',
  '/areas': 'Learning areas',
  '/corrections': 'Correction drafts',
  '/learn': 'Learn',
  '/practice': 'Practice',
  '/progress': 'Progress',
  '/session': 'Learning session',
  '/review': 'Review',
  '/recap': 'Session recap',
}

export function Shell({ children }: { children: React.ReactNode }) {
  const { mode, energy } = useMode()
  useSensory()
  const { pathname, key: routeKey } = useLocation()
  const [focusState, setFocusState] = useState({ key: routeKey, active: false })
  if (focusState.key !== routeKey) setFocusState({ key: routeKey, active: false })
  const focused = pathname === '/session' && focusState.key === routeKey && focusState.active
  const setFocused = (active: boolean) => setFocusState({ key: routeKey, active })
  useEffect(() => {
    if (!focused) return
    const escape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || event.isComposing) return
      const nested = document.querySelector('dialog[open], [role="dialog"]')
      const editor = event.target instanceof Element && event.target.closest('.cm-editor')
      queueMicrotask(() => {
        if (!nested && !editor && !event.defaultPrevented) {
          if (document.activeElement?.closest('[data-focus-only]')) document.querySelector<HTMLButtonElement>('[data-focus-toggle]')?.focus()
          setFocusState({ key: routeKey, active: false })
        }
      })
    }
    window.addEventListener('keydown', escape, true)
    return () => window.removeEventListener('keydown', escape, true)
  }, [focused, routeKey])
  const routePath = pathname.replace(/\/+$/, '').toLowerCase() || '/'
  const [tutorEntry, setTutorEntry] = useState<HTMLDivElement | null>(null)
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
  const wide = ['/playground', '/programs', '/session'].some((path) => pathname.startsWith(path))
  return (
    <LessonFocusContext.Provider value={pathname === '/session' ? { active: focused, setActive: setFocused } : null}>
    <div className={`min-h-screen ${focused ? 'shell-focus' : ''}`}>
      <a href="#main-content" className="sr-only focus:not-sr-only focus:block focus:p-3 focus:bg-card">
        Skip to learning content
      </a>
      <header className="shell-header border-b border-line bg-card">
        <Link to="/" className="shell-brand font-semibold no-underline text-fg">
          <Brand />
        </Link>
        <QuickNavigation enabled={!focused} pages={[...primaryPages, ...toolPages]} />
        <ParkingLotButton statusRoot={tutorEntry} />
        <AudioControls compact header />
      </header>
      <div className="shell-workspace">
        <MainNavigation />
      <div className="tutor-workspace min-w-0">
      <div className="min-w-0">
      <div role="region" aria-label="Learning context and tools" className={`${wide ? 'max-w-7xl' : 'max-w-4xl'} w-full mx-auto px-4 pt-4 flex flex-wrap items-center justify-between gap-2 min-w-0`}>
        <div className="shell-browse-context min-w-0">
          <BrowseArea />
          <p className="text-xs text-muted">{MODE_LABELS[mode].title} · energy {energy}</p>
        </div>
        <div ref={setTutorEntry} className="flex flex-wrap gap-2 min-w-0" />
      </div>
      <main
        id="main-content"
        ref={main}
        tabIndex={-1}
        className={`${wide ? 'max-w-7xl' : 'max-w-4xl'} w-full mx-auto p-4 pb-24`}
      >
        {children}
      </main>
      </div>
      <LearningCompanion entryRoot={tutorEntry} />
      </div>
      </div>
    </div>
    </LessonFocusContext.Provider>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Shell>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/search" element={<Search />} />
            <Route path="/sources" element={<Sources />} />
            <Route path="/answers" element={<Answers />} />
            <Route path="/answers/:answerId" element={<Answers />} />
            <Route path="/learn" element={<Learn />} />
            <Route path="/practice" element={<Practice />} />
            <Route path="/progress" element={<Progress />} />
            <Route path="/session" element={<Session />} />
            <Route path="/playground" element={<Playground />} />
            <Route path="/playground/visualizer" element={<Visualizer />} />
            <Route path="/review" element={<Review />} />
            <Route path="/recap" element={<Recap />} />
            <Route path="/map" element={<Map />} />
            <Route path="/preferences" element={<Preferences />} />
            <Route path="/corrections" element={<CorrectionEditor />} />
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
                  <h1 className="text-page-title font-semibold">Page not found</h1>
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
