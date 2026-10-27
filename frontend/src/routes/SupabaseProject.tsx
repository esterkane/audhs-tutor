import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { apiFetch, type Schemas } from '../lib/api'
import { Button } from '../components/ui/button'
import { TutorApp } from '../features/supabaseTutor'
import { usePreferences } from '../features/preferences/api'

export function SupabaseProject() {
  const status = useQuery({
    queryKey: ['supabase-project-status'],
    retry: false,
    queryFn: () => apiFetch<Schemas['SupabaseProjectStatus']>('/api/learning-focus/supabase'),
  })
  const prefs = usePreferences()
  const values = prefs.data?.values ?? {}
  return (
    <div className="grid gap-4 min-w-0">
      <header>
        <Link to="/projects">Back to knowledge projects</Link>
        <h1 className="text-page-title font-semibold">Supabase and PostgreSQL project</h1>
        <p>
          Work through a disposable local SQL lab. Explain your observations, check the result, and develop
          your own knowledge material. Project progress does not certify mastery.
        </p>
      </header>
      {!status.data?.ready && (
        <section className="rounded border border-line p-4">
          <p role="status">
            {status.data?.detail ??
              (status.isError ? 'Project status could not load.' : 'Checking the local project…')}
          </p>
          <Button onClick={() => void status.refetch()}>Check project readiness</Button>
        </section>
      )}
      {status.data?.ready && !prefs.data && (
        <section>
          <p role="status">
            {prefs.isError
              ? 'Tutor preferences could not load. Your saved preferences are kept.'
              : 'Loading your language and tutor preferences…'}
          </p>
          {prefs.isError && <Button onClick={() => void prefs.refetch()}>Retry tutor preferences</Button>}
        </section>
      )}
      {status.data?.ready && status.data.user_id && prefs.data && (
        <section
          className="bg-zinc-950 text-zinc-100 rounded p-3 min-w-0"
          aria-label="Local Supabase project tutor"
        >
          <TutorApp
            host={{ userId: status.data.user_id }}
            apiBase="/api/supabase-project"
            deliveryChoice
            language={values['tutor.response_language'] === 'de' ? 'de' : 'en'}
            personaOn={values['tutor.persona'] === 'kangaroo'}
          />
        </section>
      )}
      <p className="text-sm text-muted">
        Imported project:{' '}
        <a href="https://github.com/esterkane/kanguroo-supabase-tutor" target="_blank" rel="noreferrer">
          kanguroo-supabase-tutor
        </a>
        . Study uses the local model. Authoring remains a separate, capped workflow.
      </p>
    </div>
  )
}
