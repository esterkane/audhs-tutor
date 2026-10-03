/** Browser-tab-only coordination for explicitly requested text readings. */
let active: { stop: () => void } | null = null

export function claimReading(stop: () => void): () => void {
  const previous = active
  const owner = { stop }
  active = owner
  previous?.stop()
  return () => {
    if (active === owner) active = null
  }
}
