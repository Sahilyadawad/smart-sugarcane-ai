import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LoadingBlock } from './ui'

export function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center">
        <LoadingBlock label="Checking your session..." />
      </div>
    )
  }

  if (!isAuthenticated) {
    // Remember where they were headed so login can send them back.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}

export function PublicOnlyRoute() {
  const { isAuthenticated, loading } = useAuth()
  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center">
        <LoadingBlock label="Loading..." />
      </div>
    )
  }
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <Outlet />
}
