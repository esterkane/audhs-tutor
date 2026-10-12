import { VisualFallback } from '../features/visual-learning/VisualFallback'
import { lazy, Suspense, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { centering, feedback, objective, source, type FitScope } from '../features/visual-learning/leakage'
const LeakageGraph = lazy(() => import('../features/visual-learning/LeakageGraph'))
export default function VisualLearning() {
  const [scope, setScope] = useState<FitScope>('train')
  const [heldOut, setHeldOut] = useState(10)
  const [answer, setAnswer] = useState('')
  const [checked, setChecked] = useState('')
  const data = centering(scope, heldOut)
  return <div className="grid gap-5">
    <Link to="/playground">← Return to coding playground</Link>
    <h1 className="text-page-title font-semibold">Keep test data out of training</h1>
    <p><strong>Learning objective:</strong> {objective}</p>
    <p>Fitting learns a value from data. Transforming applies that saved value to new data. Here, mean-centering subtracts a learned average. It is only one preprocessing step, not a complete model.</p>
    <p className="text-sm text-muted">Synthetic visual experiment · changes and answers are temporary · no mastery score is recorded.</p>
    <section className="grid gap-3" aria-labelledby="experiment-title">
      <h2 id="experiment-title" className="text-section-title font-semibold">Try changing the held-out data</h2>
      <p>Training values stay at 2 and 4. Before moving the slider, predict whether the fitted mean should change.</p>
      <label>Fit the mean using
        <select className="block w-full p-3 bg-card border border-control rounded-md" value={scope} onChange={e => setScope(e.target.value as FitScope)}>
          <option value="train">Training data only</option><option value="all">Training and held-out data</option>
        </select>
      </label>
      <label>First held-out value: {heldOut}
        <input className="block w-full min-h-11" type="range" min="6" max="20" step="1" value={heldOut} onChange={e => setHeldOut(Number(e.target.value))} />
      </label>
      <VisualFallback><Suspense fallback={<p>Loading optional diagram. The complete text explanation is below.</p>}><LeakageGraph scope={scope} mean={data.mean} /></Suspense></VisualFallback>
      <p role="status">Fitted mean: {data.mean}. {scope === 'train' ? 'Held-out values do not influence fitting.' : 'Held-out information now influences fitting: data leakage.'}</p>
      <p>Information flow: training → fit mean → transform. Held-out values → transform{scope === 'all' ? ', and also → fit mean (the leaking connection)' : ' only; no connection to fit mean'}.</p>
      <dl className="grid gap-2"><div><dt>Training values</dt><dd>{data.train.join(', ')}</dd></div><div><dt>Held-out values</dt><dd>{data.test.join(', ')}</dd></div><div><dt>Held-out values after subtracting the mean</dt><dd>{data.transformed.join(', ')}</dd></div></dl>
      <p>This demonstrates information leakage, not how much an accuracy score changes. Transform both sets using the training mean; never refit on the held-out set.</p>
      <Button onClick={() => { setScope('train'); setHeldOut(10) }}>Reset experiment</Button>
    </section>
    <section className="grid gap-3" aria-labelledby="transfer-title">
      <h2 id="transfer-title" className="text-section-title font-semibold">Apply the idea to a new situation</h2>
      <p>You split patient records into training and test sets. Some ages are missing. Which median should fill those gaps before evaluating the model?</p>
      <fieldset className="grid gap-2"><legend>Choose an approach</legend>{[['all','Find one median using all patients.'],['train','Learn the training median and use it for both sets.'],['separate','Learn a separate median for each set.']].map(([id,label]) => <label key={id} className="flex gap-3 items-center min-h-11"><input type="radio" name="imputation" value={id} checked={answer === id} onChange={() => { setAnswer(id); setChecked('') }} />{label}</label>)}</fieldset>
      <Button variant="primary" disabled={!answer} onClick={() => setChecked(answer)}>Check my reasoning</Button>
      {checked && <p role="status">{feedback(checked)}</p>}
    </section>
    <p className="text-sm">Source: <a href={source} target="_blank" rel="noreferrer">scikit-learn: common pitfalls and data leakage</a>. The numeric example is authored synthetic data, not imported course content.</p>
  </div>
}
