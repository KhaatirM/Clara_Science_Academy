import type { SchoolTimezone, SessionUser } from './session'

export interface ManagementOutletContext {
  user: SessionUser
  schoolTimezone: SchoolTimezone | null
}
