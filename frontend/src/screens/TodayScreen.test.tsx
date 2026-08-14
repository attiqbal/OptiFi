import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { TodayScreen } from './TodayScreen'
import { renderWithVariant } from '../test/renderWithVariant'
import type { TodayResponse } from '../api/types'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return { ...actual, api: { ...actual.api, today: vi.fn() } }
})

const BASE_UAP = {
  source: 's',
  producer: 'p',
  generated_at: '2026-01-01T00:00:00Z',
  assumptions: [],
  limitations: [],
  dependencies: [],
  provenance_chain: [],
  disagreement_set_ref: null,
}

const RESPONSE: TodayResponse = {
  portfolio_variant: 'default',
  portfolio_value: { ...BASE_UAP, id: '1', subject: 'net capital', information_class: 'FACT', validation_status: 'VERIFIED', result: 428600, confidence: 'HIGH' },
  risk: { ...BASE_UAP, id: '2', subject: 'risk', information_class: 'ESTIMATE', validation_status: 'PROVISIONAL', result: 5.2, confidence: 'LOW' },
  capital_efficiency: { ...BASE_UAP, id: '3', subject: 'ces', information_class: 'ESTIMATE', validation_status: 'PROVISIONAL', result: 60, confidence: 'LOW', authoritative: false },
  developments: [
    {
      headline: 'UK interest-rate expectations changed',
      fact: null,
      estimates: [],
      judgement: null,
      portfolio_impact: 'Negligible',
      suggested_action: 'NO ACTION',
      confidence: { data_quality: 'High', model_agreement: 'High', data_freshness: 'Current', causal_distance: 'Short', conflicting_signals: 0, overall_confidence: 'High' },
      evidence_ids: [],
    },
  ],
}

describe('TodayScreen', () => {
  it('shows a real loading state before data arrives', async () => {
    const { api } = await import('../api/client')
    vi.mocked(api.today).mockReturnValue(new Promise(() => {})) // never resolves
    renderWithVariant(<TodayScreen />)
    expect(screen.getByRole('status')).toHaveTextContent(/Loading/)
  })

  it('shows a real error state when the API call fails', async () => {
    const { api } = await import('../api/client')
    vi.mocked(api.today).mockRejectedValue(new Error('backend unavailable'))
    renderWithVariant(<TodayScreen />)
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('backend unavailable'))
  })

  it('never shows the Capital Efficiency Score as authoritative while PROVISIONAL', async () => {
    const { api } = await import('../api/client')
    vi.mocked(api.today).mockResolvedValue(RESPONSE)
    renderWithVariant(<TodayScreen />)
    await waitFor(() => expect(screen.getByText(/provisional — not authoritative/)).toBeInTheDocument())
  })
})
