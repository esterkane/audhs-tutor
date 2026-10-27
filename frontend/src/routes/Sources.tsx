import { Navigate, useLocation } from 'react-router-dom'
export function Sources() {
  const location = useLocation()
  return <Navigate replace to={'/library' + location.search + location.hash} />
}
