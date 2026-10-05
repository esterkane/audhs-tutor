import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { useSkills } from './api'

export function SkillSearch({ phrase }: { phrase: string }) {
  const skills = useSkills()
  const term = phrase.toLocaleLowerCase()
  const matches = (skills.data?.skills ?? []).filter(skill => [skill.title, skill.description].some(text => text.toLocaleLowerCase().includes(term)))
  return <section aria-labelledby="search-skills" className="rounded-md border border-line p-3 min-w-0 break-words">
    <h2 id="search-skills" className="text-panel-heading font-semibold">Skills</h2>
    <p className="text-sm text-muted">Skill names and descriptions matching your phrase. Open a lesson choice before deciding whether to start or switch.</p>
    {skills.isPending ? <p role="status">Searching skills…</p> : skills.isError ? <div role="alert">Skills could not be refreshed. <Button disabled={skills.isFetching} onClick={() => void skills.refetch()}>Retry skill search</Button></div> : <>
      <p role="status">{matches.length ? `${Math.min(8, matches.length)} of ${matches.length} matching skills shown.` : 'No skills matched.'}</p>
      <ul className="grid gap-3 my-2">{matches.slice(0, 8).map(skill => <li key={skill.id}>
        <Link className="underline" to={`/?${new URLSearchParams({ lesson: skill.id })}`}>{skill.title}</Link>
        <p className="text-sm">{skill.description}</p>
        {!skill.unlocked && <p className="text-sm text-muted">Prerequisites are not yet met.</p>}
      </li>)}</ul>
      {matches.length > 8 && <Link className="underline" to="/map">Browse the full skill map</Link>}
    </>}
  </section>
}
