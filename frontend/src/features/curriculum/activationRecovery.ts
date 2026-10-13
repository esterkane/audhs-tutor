import type { Schemas } from '../../lib/api'
export type ActivationRequest = {
  version: 1
  draftId: string
  key: string
  command: Schemas['ActivateLesson']
}
export const activationKey = (learner: string, draft: string) => `lesson-activation:v1:${learner}:${draft}`
export function parseActivation(raw: string, draftId: string): ActivationRequest {
  if (raw.length > 4096) throw new Error('Oversized recovery')
  const value = JSON.parse(raw) as ActivationRequest
  const c = value?.command
  if (
    value?.version !== 1 ||
    value.draftId !== draftId ||
    typeof value.key !== 'string' ||
    !value.key.trim() ||
    value.key.length > 128 ||
    !c ||
    typeof c.promotion_id !== 'string' ||
    !c.promotion_id ||
    c.promotion_id.length > 128 ||
    !Number.isInteger(c.expected_version) ||
    c.expected_version < 1 ||
    !/^[a-f0-9]{64}$/.test(c.payload_sha256) ||
    Object.keys(c).length !== 3 ||
    Object.keys(value).length !== 4
  )
    throw new Error('Invalid recovery')
  return value
}
