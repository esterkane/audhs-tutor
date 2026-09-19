import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { ParkingLotButton } from '../components/ParkingLotButton'
import { Home } from '../routes/Home'
import { Recap } from '../routes/Recap'
import { Review } from '../routes/Review'
import { Session } from '../routes/Session'
import { MODE_LABELS, useMode } from '../stores/mode'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

export function Shell({ children }: { children: React.ReactNode }) {
  const { mode, energy, sessionId } = useMode()
  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between px-4 py-3 border-b border-line bg-card">
        <Link to="/" className="font-semibold no-underline text-fg">
          AuDHS-Tutor
        </Link>
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
          </Routes>
        </Shell>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
