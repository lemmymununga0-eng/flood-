import { Outlet } from "react-router-dom";

// Intentionally inert this phase — a no-op passthrough so the route tree has a named
// slot for public-page chrome without changing any rendered markup yet.
export default function PublicLayout() {
  return <Outlet />;
}
