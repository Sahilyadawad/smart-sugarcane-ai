import { Route, Routes } from 'react-router-dom'
import PublicLayout from './layouts/PublicLayout'
import DashboardLayout from './layouts/DashboardLayout'
import { ProtectedRoute, PublicOnlyRoute } from './components/ProtectedRoute'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Irrigation from './pages/Irrigation'
import PlantAnalysis from './pages/PlantAnalysis'
import SoilAnalysis from './pages/SoilAnalysis'
import Varieties from './pages/Varieties'
import Fertilizer from './pages/Fertilizer'
import Assistant from './pages/Assistant'
import HistoryPage from './pages/History'
import SettingsPage from './pages/Settings'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<Landing />} />
      </Route>

      <Route element={<PublicOnlyRoute />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/irrigation" element={<Irrigation />} />
          <Route path="/plant-analysis" element={<PlantAnalysis />} />
          <Route path="/soil-analysis" element={<SoilAnalysis />} />
          <Route path="/varieties" element={<Varieties />} />
          <Route path="/fertilizer" element={<Fertilizer />} />
          <Route path="/assistant" element={<Assistant />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
