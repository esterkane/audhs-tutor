import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { ParkingLotButton } from '../components/ParkingLotButton'
import { Corpus } from '../routes/Corpus'
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
import { MODE_LABELS, useMode } from '../stores/mode'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

export function Shell({ children }: { children: React.ReactNode }) {
  const { mode, energy, sessionId } = useMode()
  useSensory()
  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between px-4 py-3 border-b border-line bg-card">
        <Link to="/" className="font-semibold no-underline text-fg">
          AuDHS-Tutor
        </Link>
        <nav className="flex gap-3 text-sm">
          <Link to="/map">Skill map</Link>
          <Link to="/together">Together</Link>
          <Link to="/experiments">Experiments</Link>
          <Link to="/vocab">Vocab</Link>
          <Link to="/corpus">Corpus</Link>
          <Link to="/models">Models</Link>
          <Link to="/preferences">Preferences</Link>
        </nav>
        <div className="text-sm text-muted" aria-live="polite">
          {MODE_LABELS[mode].title} · energy {energy}
          {sessionId ? ' · session running' : ''}
        </div>
      </header>
      <main className="max-w-3xl mx-auto p-4 pb-24">{children}</main>
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
            <Route path="/session" element={<Session />} />
            <Route path="/review" element={<Review />} />
            <Route path="/recap" element={<Recap />} />
            <Route path="/map" element={<Map />} />
            <Route path="/preferences" element={<Preferences />} />
            <Route path="/corpus" element={<Corpus />} />
            <Route path="/models" element={<Models />} />
            <Route path="/experiments" element={<Experiments />} />
            <Route path="/vocab" element={<Vocab />} />
            <Route path="/together" element={<Together />} />
          </Routes>
        </Shell>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
