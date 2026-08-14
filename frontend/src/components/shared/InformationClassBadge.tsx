import type { InformationClass } from '../../api/types'

const LABEL: Record<InformationClass, string> = {
  FACT: 'FACT',
  ESTIMATE: 'ESTIMATE',
  JUDGEMENT: 'JUDGEMENT',
}

// Distinguished by label text (not colour alone) for accessibility — a
// screen reader or a colour-blind user gets the same distinction a
// sighted user reading colour does. APP_UX_BLUEPRINT.md Section 3: every
// FACT/ESTIMATE/JUDGEMENT must be visually distinguishable.
export function InformationClassBadge({ informationClass }: { informationClass: InformationClass }) {
  return <span className={`badge badge--${informationClass.toLowerCase()}`}>{LABEL[informationClass]}</span>
}
