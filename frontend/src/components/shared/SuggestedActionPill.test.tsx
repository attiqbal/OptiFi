import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CallToActionButton, SuggestedActionPill } from './SuggestedActionPill'
import type { SuggestedAction } from '../../api/types'

describe('SuggestedActionPill', () => {
  it('renders every allowed action', () => {
    const actions: SuggestedAction[] = ['NO ACTION', 'MONITOR', 'REVIEW', 'ANALYSE', 'COMPARE']
    actions.forEach((action) => {
      render(<SuggestedActionPill action={action} />)
      expect(screen.getByText(action)).toBeInTheDocument()
    })
  })

  it('rejects a directive action at the type level', () => {
    // @ts-expect-error "Buy AAPL" is not a SuggestedAction — APP_UX_BLUEPRINT.md
    // Section 3's "never a directive" rule enforced as a compile error.
    const bad: SuggestedAction = 'Buy AAPL'
    void bad
  })

  it('never silently renders an unrecognised value as if it were valid', () => {
    render(<SuggestedActionPill action="Buy AAPL" />)
    const el = screen.getByText(/Unrecognised action/)
    expect(el).toHaveAttribute('data-unrecognised-action', 'true')
    expect(screen.queryByText('Buy AAPL')).not.toBeInTheDocument()
  })
})

describe('CallToActionButton', () => {
  it('renders known calls to action as enabled buttons', () => {
    render(<CallToActionButton action="Review" />)
    expect(screen.getByRole('button', { name: 'Review' })).toBeEnabled()
  })

  it('disables and hides an unrecognised call to action rather than rendering it', () => {
    render(<CallToActionButton action="Execute trade" />)
    const button = screen.getByRole('button', { name: 'Unavailable' })
    expect(button).toBeDisabled()
    expect(screen.queryByText('Execute trade')).not.toBeInTheDocument()
  })
})
