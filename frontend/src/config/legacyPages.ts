/** Per-route legacy CSS for management pages that still use mgmt-* / Bootstrap markup. */
export const BOOTSTRAP_LEGACY_CSS =
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css'

/** Pre-scoped Bootstrap for legacy SPA pages (does not affect sidebar). */
export const BOOTSTRAP_SCOPED_CSS = '/static/css/bootstrap-scoped.css?v=1'

export const SHARED_CALENDAR_CSS = '/static/css/shared_calendar.css?v=2'
export const CALENDAR_LEGACY_CSS = '/static/css/management_admin_calendar.css?v=11'
export const CLOSURE_LEGACY_CSS = '/static/css/management_admin_school_year_closure.css?v=3'
export const SCHOOL_YEARS_LEGACY_CSS = '/static/css/management_admin_school_years.css?v=2'
export const STUDENTS_LEGACY_CSS = '/static/css/management_admin_students.css?v=7'
export const HOME_LEGACY_CSS = '/static/css/management_admin_home.css?v=11'
export const COMPONENTS_LEGACY_CSS = '/static/css/components.css?v=1'
export const ASSISTANT_APPROVAL_LEGACY_CSS = '/static/css/assistant_approval.css?v=1'

/** Routes that need scoped Bootstrap (modals / legacy markup). */
export const BOOTSTRAP_MGMT_PATH =
  /^\/management(?:\/students(?:\/new)?|\/calendar|\/school-years|\/school-year\/closure)|^\/teacher\/classes\/\d+/

type StyleRule = { test: RegExp; sheets: string[] }

const PAGE_STYLE_RULES: StyleRule[] = [
  { test: /^\/management\/?$/, sheets: [HOME_LEGACY_CSS] },
  { test: /^\/teacher\/?$/, sheets: [HOME_LEGACY_CSS] },
  { test: /^\/student\/?$/, sheets: [HOME_LEGACY_CSS] },
  { test: /^\/student\/assignments(?:\/|$)/, sheets: [HOME_LEGACY_CSS] },
  { test: /^\/student\/(calendar|schedule|settings|jobs|classes|grades|collaborate)(?:\/|$)/, sheets: [HOME_LEGACY_CSS] },
  { test: /^\/student\/calendar\/?$/, sheets: [SHARED_CALENDAR_CSS, HOME_LEGACY_CSS] },
  { test: /^\/teacher\/(classes|students|assignments-and-grades|attendance|schedule|settings)(?:\/|$)/, sheets: [HOME_LEGACY_CSS] },
  { test: /^\/teacher\/classes\/\d+\/?$/, sheets: [HOME_LEGACY_CSS, COMPONENTS_LEGACY_CSS, ASSISTANT_APPROVAL_LEGACY_CSS] },
  { test: /^\/teacher\/calendar\/?$/, sheets: [SHARED_CALENDAR_CSS, HOME_LEGACY_CSS] },
  { test: /^\/management\/students\/?$/, sheets: [STUDENTS_LEGACY_CSS] },
  { test: /^\/management\/students\/new\/?$/, sheets: [STUDENTS_LEGACY_CSS] },
  { test: /^\/management\/calendar\/?$/, sheets: [SHARED_CALENDAR_CSS, CALENDAR_LEGACY_CSS] },
  { test: /^\/management\/school-years\/?$/, sheets: [SCHOOL_YEARS_LEGACY_CSS] },
  {
    test: /^\/management\/school-year\/closure/,
    sheets: [CLOSURE_LEGACY_CSS],
  },
]

export function stylesForMgmtPath(pathname: string): string[] {
  const sheets: string[] = []
  for (const rule of PAGE_STYLE_RULES) {
    if (rule.test.test(pathname)) {
      for (const href of rule.sheets) {
        if (!sheets.includes(href)) sheets.push(href)
      }
    }
  }
  if (BOOTSTRAP_MGMT_PATH.test(pathname)) {
    if (!sheets.includes(BOOTSTRAP_SCOPED_CSS)) sheets.push(BOOTSTRAP_SCOPED_CSS)
  }
  return sheets
}

export function needsScopedBootstrap(pathname: string): boolean {
  return BOOTSTRAP_MGMT_PATH.test(pathname)
}

/** @deprecated Use stylesForMgmtPath — kept for compatibility. */
export function isLegacyMgmtPath(pathname: string): boolean {
  return stylesForMgmtPath(pathname).length > 0
}
