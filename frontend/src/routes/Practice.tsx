import { Link } from 'react-router-dom'
import { Card, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'

const activities = [
  {
    title: 'Practise a lesson',
    description: 'Open your current learning session, or choose a topic from Home. Questions and scheduled reviews stay within that session.',
    action: 'Open learning session', path: '/learn',
  },
  {
    title: 'Try a coding experiment',
    description: 'Edit starter code, predict the result and run it locally. Ask the tutor for help when you need it.',
    action: 'Open playground', path: '/playground',
  },
  {
    title: 'Practise listening and vocabulary',
    description: 'Open listening lessons and manage vocabulary cards. Vocabulary reviews appear in language blocks when enabled in Preferences.',
    action: 'Open language activities', path: '/vocab',
  },
  {
    title: 'Work on a project',
    description: 'Build a small system, record test evidence and explain what you learned.',
    action: 'Open knowledge projects', path: '/projects',
  },
] as const

export function Practice() {
  return <div className="grid gap-5">
    <div>
      <h1 className="text-page-title font-semibold">Practice</h1>
      <p className="mt-2 text-muted">Choose what you want to try. Opening an activity does not count as completed practice.</p>
    </div>
    <div className="grid gap-5 md:grid-cols-2">
      {activities.map(activity => <Card key={activity.path} className="flex flex-col items-start">
        <CardTitle>{activity.title}</CardTitle>
        <p className="mb-4">{activity.description}</p>
        <Button asChild className="mt-auto"><Link to={activity.path}>{activity.action}</Link></Button>
      </Card>)}
    </div>
  </div>
}
