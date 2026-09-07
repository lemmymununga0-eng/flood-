export default function Profile() {
  return (
    <div>
      <div className="page-header">
        <h1>Profile</h1>
      </div>
      <div className="card" style={{ maxWidth: 480 }}>
        <p className="text-secondary">
          No authentication or user-account backend exists yet (see docs/DATABASE.md —
          <code>SystemUser</code> is "Not yet implemented"). There is no real profile to
          show. This page is a placeholder for when auth is built.
        </p>
      </div>
    </div>
  );
}
