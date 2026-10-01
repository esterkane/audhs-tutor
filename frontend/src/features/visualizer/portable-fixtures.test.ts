import { expect, it } from 'vitest'
import fixtures from './fixtures/portable-evaluation-v1.json'
import { evaluate, parsePreset } from './engine'
for (const sample of fixtures.cases) {
  it(`portable reference: ${sample.name}`, () => {
    const preset = parsePreset(JSON.stringify(sample.preset))
    const result = evaluate(preset, sample.frame, sample.seconds, sample.dt, new Map(Object.entries(sample.initialMemory)))
    expect(Math.abs(result.scale - sample.expected.scale)).toBeLessThan(fixtures.tolerance)
    expect(Math.abs(result.energy - sample.expected.energy)).toBeLessThan(fixtures.tolerance)
    for (const [id, value] of Object.entries(sample.expected.values)) {
      expect(Math.abs(result.values.get(id)! - value!)).toBeLessThan(fixtures.tolerance)
    }
  })
}
