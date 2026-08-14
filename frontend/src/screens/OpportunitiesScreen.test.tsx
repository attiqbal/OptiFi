import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { OpportunitiesScreen } from './OpportunitiesScreen'
import { renderWithVariant } from '../test/renderWithVariant'
import type { Opportunity } from '../api/types'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return { ...actual, api: { ...actual.api, opportunities: vi.fn() } }
})

const CONFIDENCE = {
  data_quality: 'High',
  model_agreement: 'High',
  data_freshness: 'Current',
  causal_distance: 'Short',
  conflicting_signals: 0,
  overall_confidence: 'High',
}

const OPPORTUNITY: Opportunity = {
  kind: 'excess_idle_cash',
  headline: '£1,234/year opportunity',
  description: 'Your cash reserve exceeds your selected liquidity requirement.',
  fact: {
    id: 'f1',
    subject: 'cash holding',
    information_class: 'FACT',
    validation_status: 'VERIFIED',
    result: {},
    source: 's',
    producer: 'p',
    generated_at: '2026-01-01T00:00:00Z',
    confidence: 'HIGH',
    assumptions: [],
    limitations: [],
    dependencies: [],
    provenance_chain: [],
    disagreement_set_ref: null,
  },
  estimates: [],
  call_to_action: 'Review',
  confidence: CONFIDENCE,
  evidence_ids: ['f1'],
}

describe('OpportunitiesScreen', () => {
  it('renders the real no-opportunities state as a valid screen, not an error', async () => {
    const { api } = await import('../api/client')
    vi.mocked(api.opportunities).mockResolvedValue({
      portfolio_variant: 'efficient',
      opportunities: [],
      no_opportunities_message: 'No new opportunities today. Your capital allocation remains efficient against your current mandate.',
    })

    renderWithVariant(<OpportunitiesScreen />, { portfolio: 'efficient' })

    await waitFor(() => expect(screen.getByText(/No new opportunities today/)).toBeInTheDocument())
  })

  it('renders a real opportunity card with a non-directive call to action', async () => {
    const { api } = await import('../api/client')
    vi.mocked(api.opportunities).mockResolvedValue({
      portfolio_variant: 'default',
      opportunities: [OPPORTUNITY],
      no_opportunities_message: null,
    })

    renderWithVariant(<OpportunitiesScreen />, { portfolio: 'default' })

    await waitFor(() => expect(screen.getByText(OPPORTUNITY.headline)).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Review' })).toBeInTheDocument()
  })
})
