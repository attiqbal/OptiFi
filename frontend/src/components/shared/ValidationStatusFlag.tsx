import type { ValidationStatus } from '../../api/types'

// A non-VERIFIED validation_status must be visibly flagged wherever the
// item reaches the user (APP_UX_BLUEPRINT.md Section 3) — renders
// nothing at all for VERIFIED, never a silent "trust me" default.
export function ValidationStatusFlag({ status }: { status: ValidationStatus }) {
  if (status === 'VERIFIED') return null
  return (
    <span className="badge badge--flag" role="status">
      {status}
    </span>
  )
}
