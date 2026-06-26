/** Routes that render legacy Jinja-parity management shells. */
export const LEGACY_HOME_PATH = /^\/management\/?$/
export const LEGACY_MGMT_PATH = /^\/management\/(calendar|school-years|school-year\/closure|students)/

/** Bootstrap CDN — used only by `frontend/scripts/build-scoped-bootstrap.mjs`. */
export const BOOTSTRAP_LEGACY_CSS =
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css'

/** Pre-scoped Bootstrap for legacy SPA pages (does not affect sidebar). */
export const BOOTSTRAP_SCOPED_CSS = '/static/css/bootstrap-scoped.css?v=1'

export const SHARED_CALENDAR_CSS = '/static/css/shared_calendar.css?v=2'
export const CALENDAR_LEGACY_CSS = '/static/css/management_admin_calendar.css?v=11'
export const CLOSURE_LEGACY_CSS = '/static/css/management_admin_school_year_closure.css?v=3'
export const SCHOOL_YEARS_LEGACY_CSS = '/static/css/management_admin_school_years.css?v=2'
export const STUDENTS_LEGACY_CSS = '/static/css/management_admin_students.css?v=7'
export const HOME_LEGACY_CSS = '/static/css/management_admin_home.css?v=2'

export function isLegacyMgmtPath(pathname: string): boolean {
  return LEGACY_HOME_PATH.test(pathname) || LEGACY_MGMT_PATH.test(pathname)
}
