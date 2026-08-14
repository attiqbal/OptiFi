import type { ReactElement } from 'react'
import { render } from '@testing-library/react'
import { createMemoryRouter, Outlet, RouterProvider } from 'react-router-dom'
import type { AppContext } from '../App'

/** Screens read the demo-portfolio variant via useOutletContext (App.tsx)
 * — this wires the same context shape without mounting the full app
 * shell/nav, so screen tests stay focused on the screen itself. */
export function renderWithVariant(ui: ReactElement, context: Partial<AppContext> = {}) {
  const value: AppContext = { portfolio: 'default', setPortfolio: () => {}, ...context }
  const router = createMemoryRouter([
    {
      path: '/',
      element: <Outlet context={value} />,
      children: [{ index: true, element: ui }],
    },
  ])
  return render(<RouterProvider router={router} />)
}
