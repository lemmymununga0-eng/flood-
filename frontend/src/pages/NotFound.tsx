import { Link } from "react-router-dom";
import { Icon } from "../components/ui/icons";

export default function NotFound() {
  return (
    <div style={{ display: "flex", justifyContent: "center", padding: "4rem 1rem" }}>
      <div className="card" style={{ maxWidth: 420, textAlign: "center" }}>
        <div className="icon-chip" style={{ margin: "0 auto 0.75rem" }}>
          <Icon name="warning" />
        </div>
        <h1 style={{ fontSize: "3rem", margin: 0 }}>404</h1>
        <p className="text-secondary">Page Not Found</p>
        <p className="text-muted">The page you are looking for might have been removed or doesn't exist.</p>
        <Link className="btn btn-primary" to="/">
          Go Back Home
        </Link>
      </div>
    </div>
  );
}
