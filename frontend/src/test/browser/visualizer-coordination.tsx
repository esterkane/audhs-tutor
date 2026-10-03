import { MemoryRouter } from 'react-router-dom'
import { createRoot } from 'react-dom/client'
import { ReadAloud } from '../../features/voice/ReadAloud'

// Browser-only composition; never imported by the production app.
createRoot(document.getElementById('fixture')!).render(
  <MemoryRouter>
    <ReadAloud text="Synthetic reading" label="Listen to fixture" />
  </MemoryRouter>,
)
