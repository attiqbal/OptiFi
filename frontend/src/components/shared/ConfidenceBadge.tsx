import type { ConfidenceBreakdown } from '../../api/types'

// APP_UX_BLUEPRINT.md Section 13: confidence is never a single invented
// number — expanding it shows the real breakdown the backend derived
// from actual pipeline fields (evidence_store.py's confidence_breakdown).
export function ConfidenceBadge({ breakdown }: { breakdown: ConfidenceBreakdown }) {
  return (
    <details>
      <summary className="muted">Confidence: {breakdown.overall_confidence}</summary>
      <dl className="confidence-breakdown">
        <dt>Data quality</dt>
        <dd>{breakdown.data_quality}</dd>
        <dt>Model agreement</dt>
        <dd>{breakdown.model_agreement}</dd>
        <dt>Data freshness</dt>
        <dd>{breakdown.data_freshness}</dd>
        <dt>Causal distance</dt>
        <dd>{breakdown.causal_distance}</dd>
        <dt>Conflicting signals</dt>
        <dd>{breakdown.conflicting_signals}</dd>
      </dl>
    </details>
  )
}
