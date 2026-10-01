export function withheldCount(dropped: string[] | undefined): number {
  return (dropped ?? []).filter((item) => item.endsWith(':quarantined')).length
}
