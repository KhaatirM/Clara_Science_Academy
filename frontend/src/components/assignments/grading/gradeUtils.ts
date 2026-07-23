export type GradeBucket = 'A' | 'B' | 'C' | 'D' | 'F' | 'ungraded'

export type SpreadFilter = 'all' | 'passing' | 'failing' | 'ungraded'

export function letterFromPercent(pct: number): string {
  if (pct >= 90) return 'A'
  if (pct >= 80) return 'B'
  if (pct >= 70) return 'C'
  if (pct >= 60) return 'D'
  return 'F'
}

export function percentFromScore(score: string, totalPoints: number): number | null {
  const trimmed = score.trim()
  if (!trimmed) return null
  const n = parseFloat(trimmed)
  if (Number.isNaN(n)) return null
  if (totalPoints <= 0) return 0
  return Math.round((n / totalPoints) * 1000) / 10
}

export function scoreFromPercent(percent: number, totalPoints: number): string {
  const pts = (percent / 100) * totalPoints
  return String(Math.round(pts * 10) / 10)
}

export function bucketFromDraft(score: string, totalPoints: number, isVoided: boolean): GradeBucket {
  if (isVoided) return 'ungraded'
  const trimmed = score.trim()
  if (!trimmed) return 'ungraded'
  const pct = percentFromScore(trimmed, totalPoints)
  if (pct == null) return 'ungraded'
  if (pct >= 90) return 'A'
  if (pct >= 80) return 'B'
  if (pct >= 70) return 'C'
  if (pct >= 60) return 'D'
  return 'F'
}

export function matchesSpreadFilter(
  bucket: GradeBucket,
  filter: SpreadFilter,
  score: string,
  isVoided: boolean,
): boolean {
  if (isVoided) return false
  if (filter === 'all') return true
  if (filter === 'ungraded') return bucket === 'ungraded'
  if (filter === 'passing') return bucket === 'A' || bucket === 'B' || bucket === 'C' || bucket === 'D'
  if (filter === 'failing') return bucket === 'F' && score.trim() !== ''
  return true
}

export function initials(name: string) {
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] || '?') + (parts[parts.length - 1]?.[0] || '')).toUpperCase()
}

export function formatShortWhen(iso: string | null | undefined) {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleString(undefined, {
    month: '2-digit',
    day: '2-digit',
    hour: 'numeric',
    minute: '2-digit',
  })
}
