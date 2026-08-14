// Mirrors backend/app's Pydantic response shapes one-to-one.
// information_class/validation_status/confidence are literal unions, not
// `string` — a screen cannot accidentally render a value the pipeline
// never produces (SYSTEM_ARCHITECTURE.md Section 6: frontend renders
// what arrives, it does not invent new categories of its own).

export type InformationClass = 'FACT' | 'ESTIMATE' | 'JUDGEMENT'

export type ValidationStatus =
  | 'VERIFIED'
  | 'PROVISIONAL'
  | 'CONFLICTED'
  | 'STALE'
  | 'INCOMPLETE'
  | 'REJECTED'
  | 'SUPERSEDED'

export type ConfidenceLevel = 'LOW' | 'MODERATE' | 'HIGH'

// APP_UX_BLUEPRINT.md Section 3: every call-to-action is Review/Monitor/
// Analyse/Compare/Learn more/No action — never a directive ("Buy X",
// "Execute"). A value outside either union below is a TypeScript compile
// error wherever it's assigned to a typed field. Two vocabularies, not
// one, because Section 5's "Today" status line ("Suggested action: NO
// ACTION") and Section 6's Opportunity Feed button ("[Review]") use
// different casing conventions in the spec's own mockups.
export type SuggestedAction = 'NO ACTION' | 'MONITOR' | 'REVIEW' | 'ANALYSE' | 'COMPARE'
export type CallToAction = 'Review' | 'Analyse' | 'Compare' | 'Learn more'

export interface UAP {
  id: string
  subject: string
  information_class: InformationClass
  validation_status: ValidationStatus
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  result: any
  source: string
  producer: string
  generated_at: string
  confidence: ConfidenceLevel
  assumptions: string[]
  limitations: string[]
  dependencies: string[]
  provenance_chain: string[]
  disagreement_set_ref: string | null
  // ScenarioResult-only fields, present when this UAP is a scenario result.
  scenario_description?: string
  affected_entity_id?: string
  base_case?: number
  range_low?: number
  range_high?: number
  sensitivity_factors?: string[]
}

export interface ConfidenceBreakdown {
  data_quality: string
  model_agreement: string
  data_freshness: string
  causal_distance: string
  conflicting_signals: number
  overall_confidence: string
}

export type PortfolioVariant = 'default' | 'efficient'

export interface Development {
  headline: string
  fact: UAP | null
  estimates: UAP[]
  judgement: UAP | null
  portfolio_impact: string
  suggested_action: SuggestedAction
  confidence: ConfidenceBreakdown
  evidence_ids: string[]
  affected?: string[]
  your_exposure?: number
  potential_annual_improvement?: number
}

export interface TodayResponse {
  portfolio_variant: PortfolioVariant
  portfolio_value: UAP
  risk: UAP
  capital_efficiency: UAP & { authoritative: boolean }
  developments: Development[]
}

export interface Holding {
  entity_id: string
  label: string
  sector: string
  geography: string
  currency: string
  weight: number
  value: number
  fact: UAP
}

export interface PortfolioResponse {
  portfolio_variant: PortfolioVariant
  assets_total: number
  liabilities_total: number
  net_capital: number
  liabilities: UAP[]
  data_freshness: {
    checked_against_present_time: boolean
    stale_items: { kind: string; description: string; subject: string | null }[]
  }
  holdings: Holding[]
  allocation: Record<string, number>
  sector_exposure: Record<string, number>
  geographic_exposure: Record<string, number>
  currency_exposure: Record<string, number>
  concentration: {
    largest_holding: string
    largest_weight: number
    technology_target_max: number
    technology_breach: boolean
  }
  liquidity: { actual_cash: number; minimum_reserve: number; liquidity_efficiency: UAP }
  risk: { covariance: UAP; portfolio_variance: UAP; historical_var_95: UAP; parametric_var_95: UAP }
  performance: { sharpe_ratio: UAP }
  capital_efficiency: UAP & { sub_scores: Record<string, UAP> }
}

export interface Opportunity {
  kind: string
  headline: string
  description: string
  fact: UAP
  estimates: UAP[]
  call_to_action: CallToAction
  confidence: ConfidenceBreakdown
  evidence_ids: string[]
}

export interface OpportunitiesResponse {
  portfolio_variant: PortfolioVariant
  opportunities: Opportunity[]
  no_opportunities_message: string | null
}

export interface RiskResponse {
  portfolio_variant: PortfolioVariant
  risk_contributors: UAP
  concentration: { largest_holding: string; largest_weight: number }
  volatility: { portfolio_variance: UAP; portfolio_std_dev: number }
  drawdown_scenarios: { historical_var_95: UAP; parametric_var_95: UAP; rate_cut_scenario: UAP }
  fx_exposure: Record<string, number>
  duration: UAP
  scenario_sensitivity: Record<string, UAP>
}

export interface ResearchResponse {
  asset_id: string
  covered: boolean
  message?: string
  label?: string
  current_state?: UAP
  fundamentals?: { note: string }
  forecasts?: UAP[]
  scenarios?: Record<string, UAP>
  risk?: UAP
  causal_exposures?: UAP[]
  news_events?: { note: string }
  asset_plus_you?: {
    current_portfolio_exposure: number
    if_10000_invested: { additional_amount: number; exposure_after: number }
    sector_exposure: { current: number }
    limitations: string[]
  }
  confidence?: ConfidenceBreakdown
}

export interface ScenarioSummary {
  scenario_id: string
  family: string
  description: string
  horizon: string
  runnable_against_demo_portfolio: boolean
}

export interface ScenarioRunResponse {
  scenario_id: string
  available: boolean
  message?: string
  assumptions?: { description: string; perturbed_entity_id: string; magnitude: number; unit: string; horizon: string }
  affected_variables?: string[]
  portfolio_distribution?: { base_case: number; range_low: number; range_high: number; contributions: unknown }
  winners?: string | null
  losers?: string | null
  per_entity_results?: Record<string, UAP>
  uncertainties?: string[]
  confidence?: ConfidenceBreakdown
}

export interface AskResponse {
  routing: { engines: string[]; reasoning: string[] }
  facts: UAP[]
  estimates: UAP[]
  judgements: UAP[]
  disagreement_notes: string[]
  non_verified_disclosures: string[]
  roadblocks: { kind: string; description: string; subject: string | null }[]
  suggested_action: string
  why_ids: string[]
  candidate: UAP | null
}

export interface EvidenceResponse {
  root_id: string
  chain: UAP[]
}
