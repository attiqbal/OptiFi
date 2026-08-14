import type { CallToAction, SuggestedAction } from '../../api/types'

const ALLOWED_SUGGESTED_ACTIONS: readonly string[] = ['NO ACTION', 'MONITOR', 'REVIEW', 'ANALYSE', 'COMPARE']
const ALLOWED_CALLS_TO_ACTION: readonly string[] = ['Review', 'Analyse', 'Compare', 'Learn more']

/** APP_UX_BLUEPRINT.md Section 3: never a directive ("Buy X", "Execute").
 * Enforced twice: at the type level (SuggestedAction/CallToAction unions
 * in api/types.ts reject a bad literal at compile time) and here at
 * runtime, since a plain `fetch` response isn't type-checked at the
 * network boundary — an unrecognised value is rendered flagged, never
 * silently passed through as if it were a validated action label. */
export function SuggestedActionPill({ action }: { action: SuggestedAction | string }) {
  const known = ALLOWED_SUGGESTED_ACTIONS.includes(action)
  const className = `pill pill--${action.toLowerCase().replace(/\s+/g, '-')}`
  return (
    <span className={known ? className : 'pill'} data-unrecognised-action={!known}>
      {known ? action : `Unrecognised action (not rendered as a suggestion): ${action}`}
    </span>
  )
}

export function CallToActionButton({ action, onClick }: { action: CallToAction | string; onClick?: () => void }) {
  const known = ALLOWED_CALLS_TO_ACTION.includes(action)
  return (
    <button type="button" className="scenario-picker__button" onClick={onClick} disabled={!known}>
      {known ? action : 'Unavailable'}
    </button>
  )
}
