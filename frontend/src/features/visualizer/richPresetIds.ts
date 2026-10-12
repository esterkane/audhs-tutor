/** Stable checkpoint identities; no preset payloads or renderer dependency here. */
export const RICH_PRESET_IDS = ['geiss-3-layers', 'geiss-tunnel-mix', 'geiss-planar-mix'] as const
export type RichPresetId = typeof RICH_PRESET_IDS[number]
