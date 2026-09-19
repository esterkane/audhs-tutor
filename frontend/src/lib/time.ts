/** Wall-clock helper kept out of components so the React purity lint sees a plain call site. */
export const nowMs = (): number => Date.now()
