export default function Settings() {
  return (
    <div>
      <div className="page-header">
        <h1>Settings</h1>
        <p>General preferences. Not persisted yet — no user/session backend exists.</p>
      </div>
      <div className="card" style={{ maxWidth: 480 }}>
        <div className="field">
          <label htmlFor="tz">Timezone</label>
          <input id="tz" defaultValue="Africa/Lusaka (GMT+2)" disabled />
        </div>
        <div className="field">
          <label>
            <input type="checkbox" defaultChecked disabled /> Enable system notifications
          </label>
        </div>
        <div className="field">
          <label>
            <input type="checkbox" disabled /> Auto-sync data
          </label>
        </div>
        <p className="text-muted">
          Disabled: no <code>SystemUser</code>/settings backend exists yet to save these to.
        </p>
      </div>
    </div>
  );
}
