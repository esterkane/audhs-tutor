import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
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
  const queryClient = useQueryClient()
  const studyChoice = useMutation({
    mutationFn: (provider: 'local' | 'openai') =>
      apiFetch<Schemas['SupabaseProjectStatus']>('/api/learning-focus/supabase/study', {
        method: 'PUT',
        body: JSON.stringify({ provider }),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(['supabase-project-status'], data)
      void queryClient.invalidateQueries({ queryKey: ['preferences'] })
    },
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
      {status.data?.ready && (
        <details className="rounded border border-line p-3">
          <summary>
            Tutor provider: {status.data.study_provider === 'local' ? 'local' : status.data.study_provider}
          </summary>
          <p>
            OpenAI can answer fresh project questions using the retrieved documentation and session history.
            It shares your daily hosted budget with authoring. Reviewed reuse stays local.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={studyChoice.isPending || status.data.study_provider === 'local'}
              onClick={() => studyChoice.mutate('local')}
            >
              Use local tutor
            </Button>
            <Button
              disabled={studyChoice.isPending || status.data.study_provider === 'openai'}
              onClick={() => studyChoice.mutate('openai')}
            >
              Use OpenAI tutor
            </Button>
          </div>
          {studyChoice.isPending && <p role="status">Saving tutor provider…</p>}
          {studyChoice.isError && <p role="alert">{studyChoice.error.message} Your session is kept.</p>}
        </details>
      )}
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
        .{' '}
        {status.data?.hosted_study_enabled
          ? `Fresh project explanations use ${status.data.study_provider === 'anthropic' ? 'Anthropic' : 'OpenAI'} with the shared daily hosted budget. Reviewed answers and embeddings stay local.`
          : 'Study uses the local model. Adding an API key does not enable hosted tutoring.'}
      </p>
    </div>
  )
}
