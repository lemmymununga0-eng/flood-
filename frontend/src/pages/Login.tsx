import { useNavigate } from "react-router-dom";

export default function Login() {
  const navigate = useNavigate();

  return (
    <div className="public-page">
      <header className="public-topbar">
        <div style={{ fontWeight: 700 }}>FLOODSHIELD ZAMBIA</div>
      </header>
      <div className="card auth-card">
        <h1 style={{ marginTop: 0 }}>Welcome back</h1>
        <p className="text-secondary" style={{ marginTop: 0 }}>
          Sign in to your account
        </p>
        <div className="demo-banner">
          No authentication backend exists yet (no <code>SystemUser</code> table — see
          docs/DATABASE.md). This form does not check a real password. Use "Continue"
          below to reach the dashboard directly.
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            navigate("/dashboard");
          }}
        >
          <div className="field">
            <label htmlFor="email">Email or Username</label>
            <input id="email" type="email" placeholder="you@example.org" />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" placeholder="••••••••" />
          </div>
          <button className="btn btn-primary" type="submit" style={{ width: "100%" }}>
            Continue to dashboard
          </button>
        </form>
      </div>
    </div>
  );
}
