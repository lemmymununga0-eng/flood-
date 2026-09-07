import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="page-content" style={{ textAlign: "center", paddingTop: "4rem" }}>
      <h1 style={{ fontSize: "3rem", margin: 0 }}>404</h1>
      <p className="text-secondary">Page Not Found</p>
      <p className="text-muted">The page you are looking for might have been removed or doesn't exist.</p>
      <Link className="btn btn-primary" to="/">
        Go Back Home
      </Link>
    </div>
  );
}
