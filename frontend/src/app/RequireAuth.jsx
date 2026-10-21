import { Navigate, Outlet, useLocation } from "react-router-dom"

import { isLoggedIn } from "@/lib/auth"

export function RequireAuth() {
  const location = useLocation()
  if (!isLoggedIn()) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  return <Outlet />
}
