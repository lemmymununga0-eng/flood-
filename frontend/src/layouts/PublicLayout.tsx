import { Link, Outlet } from "react-router-dom";
import BrandMark from "../components/ui/BrandMark";
import { useAuth } from "../context/AuthContext";

/**
 * Chrome for the public (signed-out-capable) pages.
 *
 * This was previously an inert passthrough, which left `/about` with no sidebar, no
 * topbar and no links at all — reachable from the dashboard sidebar's "Help & About",
 * at which point the only way back into the app was the browser's back button or
 * editing the URL. Putting the header here rather than in each page means any public
 * page added later inherits a way out by construction.
 *
 * The right-hand action is context-aware: a signed-in user gets back to the dashboard,
 * everyone else gets Sign in.
 */
export default function PublicLayout() {
  const { user, status } = useAuth();
  const signedIn = status === "authenticated" && !!user;

  return (
    <div className="public-page">
      <header className="public-topbar">
        <Link to="/" style={{ textDecoration: "none", color: "inherit" }}>
          <BrandMark />
        </Link>
        <nav>
          <Link className="btn btn-secondary" to="/about">
            How It Works
          </Link>
          <Link className="btn btn-secondary" to="/risk-map">
            Public Risk Map
          </Link>
          {signedIn ? (
            <Link className="btn btn-primary" to="/dashboard">
              Back to Dashboard
            </Link>
          ) : (
            <Link className="btn btn-primary" to="/login">
              Sign In
            </Link>
          )}
        </nav>
      </header>

      <Outlet />
    </div>
  );
}
