/** Routes that render legacy Jinja-parity management shells (mgmt-sy / mgmt-syc). */
export const LEGACY_MGMT_PATH = /^\/management\/(school-years|school-year\/closure)/

export const BOOTSTRAP_LEGACY_CSS =
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css'

export const CLOSURE_LEGACY_CSS = '/static/css/management_admin_school_year_closure.css?v=2'
export const SCHOOL_YEARS_LEGACY_CSS = '/static/css/management_admin_school_years.css?v=1'

export function isLegacyMgmtPath(pathname: string): boolean {
  return LEGACY_MGMT_PATH.test(pathname)
}
