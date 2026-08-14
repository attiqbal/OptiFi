import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ValidationStatusFlag } from './ValidationStatusFlag'

describe('ValidationStatusFlag', () => {
  it('renders nothing for VERIFIED', () => {
    const { container } = render(<ValidationStatusFlag status="VERIFIED" />)
    expect(container).toBeEmptyDOMElement()
  })

  it.each(['PROVISIONAL', 'CONFLICTED', 'STALE', 'INCOMPLETE', 'REJECTED', 'SUPERSEDED'] as const)(
    'flags %s visibly',
    (status) => {
      render(<ValidationStatusFlag status={status} />)
      expect(screen.getByText(status)).toBeInTheDocument()
    },
  )
})
