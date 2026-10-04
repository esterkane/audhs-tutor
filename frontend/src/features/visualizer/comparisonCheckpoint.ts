import { experiments, type ExperimentId } from './experiments'
export type ComparisonCheckpoint = {
  version: 1
  active: ExperimentId | null
  compared: boolean
  hint: boolean
  prediction: '' | 'Smaller' | 'Larger' | 'Unchanged'
}
export const initialComparison: ComparisonCheckpoint = { version: 1, active: null, compared: false, hint: false, prediction: '' }
export function parseComparison(value: unknown): ComparisonCheckpoint {
  const state = value as ComparisonCheckpoint
  if (!state || state.version !== 1 ||
      !(state.active === null || experiments.some(experiment => experiment.id === state.active)) ||
      typeof state.compared !== 'boolean' || typeof state.hint !== 'boolean' ||
      !['', 'Smaller', 'Larger', 'Unchanged'].includes(state.prediction))
    throw new Error('Invalid comparison checkpoint')
  return { version: 1, active: state.active, compared: state.compared, hint: state.hint, prediction: state.prediction }
}
