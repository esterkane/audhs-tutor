// Official guide Markdown is for ingestion. Only the HTML guide exposes heading anchors.
export function guideCitationHref(url: string): string {
  return url.replace(
    /^(https:\/\/supabase\.com\/docs\/guides\/(?:[a-z0-9_-]+\/)*[a-z0-9_-]+)\.md(#[^\s#]+)$/,
    '$1$2',
  )
}
