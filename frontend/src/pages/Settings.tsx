import { Icon } from "../components/ui/icons";

export default function Settings() {
  return (
    <div>
      <div className="page-header">
        <h1 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Icon name="settings" />
          Settings
        </h1>
        <p>
          General preferences. Not persisted yet — real auth/session exist, but there's
          no dedicated settings/preferences table to save these to.
        </p>
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
          These preferences are not editable yet — saving them needs a settings store that has not been built.
        </p>
      </div>
    </div>
  );
}
