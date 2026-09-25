import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { AuthorityPage, NotFoundPage } from './pages/PlaceholderPages'
import { ComplaintDetailPage } from './pages/ComplaintDetailPage'
import { ComplaintsPage } from './pages/ComplaintsPage'
import { HomePage } from './pages/HomePage'

/** Route table. Rendered inside a router by main.tsx (BrowserRouter) or tests (MemoryRouter). */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="complaints" element={<ComplaintsPage />} />
        <Route path="complaints/:id" element={<ComplaintDetailPage />} />
        <Route path="authority" element={<AuthorityPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
