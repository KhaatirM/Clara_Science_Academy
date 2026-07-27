/** Strip /app prefix from server-provided SPA URLs for React Router (basename is already /app). */
export function spaRoute(path: string): string {
  let normalized = path.replace(/^\/app(?=\/|$)/, '')

  // Legacy Flask group-assignment URLs (pre-SPA) — map to React create routes.
  const legacyClassGroup = normalized.match(/\/management\/class\/(\d+)\/group-assignment/)
  if (legacyClassGroup) {
    return `/management/assignments/create/group/${legacyClassGroup[1]}`
  }
  if (normalized.includes('/management/group-assignment')) {
    return '/management/assignments/create/group'
  }

  return normalized || '/'
}
