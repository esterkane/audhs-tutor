import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { ListeningPanel } from '../../features/listening/ListeningPanel'
import { ReadAloud } from '../../features/voice/ReadAloud'
import { AudioControls } from '../../features/audio/AudioControls'

// Browser-only test composition. Never imported by the production app.
const element = document.getElementById('fixture')!
createRoot(element).render(
  <QueryClientProvider client={new QueryClient()}>
    <MemoryRouter>
      <header>
        <AudioControls />
      </header>
      <ListeningPanel sessionId="fixture" documentId="clip" onDone={() => {}} />
      <ReadAloud text="Synthetic reading" label="Listen to fixture" />
    </MemoryRouter>
  </QueryClientProvider>,
)
