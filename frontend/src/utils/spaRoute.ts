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

  // Legacy Flask assignments hub → SPA Assignments tab (not Home).
  const legacyMgmtHub = normalized.match(/^\/management\/assignments-and-grades(?:\/(\d+))?(?:\?.*)?$/)
  if (legacyMgmtHub) {
    return legacyMgmtHub[1]
      ? `/management/assignments/${legacyMgmtHub[1]}`
      : '/management/assignments'
  }
  if (normalized.startsWith('/management/assignments-and-grades')) {
    const params = new URLSearchParams(normalized.split('?')[1] || '')
    const classId = params.get('class_id')
    return classId ? `/management/assignments/${classId}` : '/management/assignments'
  }

  return normalized || '/'
}
