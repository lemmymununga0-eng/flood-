import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../components/ui/icons";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { canManageAlerts, useAuth } from "../context/AuthContext";
import { useFetch } from "../hooks/useFetch";
import { fetchLocations } from "../services/api";
import {
  addSubscriber,
  fetchSubscribers,
  removeSubscriber,
  testSubscriber,
} from "../services/subscribers";
import type { SmsDelivery } from "../types";

export default function SmsSubscribers() {
  const { user, status } = useAuth();
  const allowed = canManageAlerts(user);
  const [reload, setReload] = useState(0);
  const [subs, retry] = useFetch(
    useCallback(() => (allowed ? fetchSubscribers() : Promise.resolve([])), [allowed, reload]),
  );
  const [locs] = useFetch(useCallback(fetchLocations, []));

  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [locationId, setLocationId] = useState<number | "">("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const locName = (id: number | null) =>
    id === null
      ? "All areas"
      : locs.status === "success"
        ? (locs.data.find((l) => l.id === id)?.name ?? `#${id}`)
        : `#${id}`;

  async function onAdd(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await addSubscriber({ phone, name, location_id: locationId === "" ? null : locationId });
      setPhone("");
      setName("");
      setReload((n) => n + 1);
      setNotice("Number registered. It will receive SMS for matching alerts.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  }

  async function onRemove(id: number) {
    setError(null);
    setNotice(null);
    try {
      await removeSubscriber(id);
      setReload((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  async function onTest(id: number) {
    setError(null);
    setNotice(null);
    try {
      const [r]: SmsDelivery[] = await testSubscriber(id);
      setNotice(
        r.status === "sent"
          ? `Test SMS sent to ${r.to}.`
          : r.status === "simulated"
            ? `Demo mode: no real SMS sent to ${r.to}. Set SMS_PROVIDER to send for real.`
            : `Test SMS to ${r.to} ${r.status}: ${r.detail}`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  if (status === "checking") return <LoadingState label="Checking your session" />;

  if (!allowed) {
    return (
      <div>
        <div className="page-header">
          <h1>SMS Subscribers</h1>
        </div>
        <div className="card" style={{ maxWidth: 480 }}>
          <p className="text-secondary">
            Managing SMS numbers requires an ADMIN, ANALYST, or OPERATOR account.
          </p>
          {status === "anonymous" && (
            <Link className="btn btn-primary" to="/login">
              Sign in
            </Link>
          )}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Icon name="alerts" />
          SMS Subscribers
        </h1>
        <p>
          Registered numbers are texted automatically whenever an alert is issued with the SMS
          channel for their area. Use “Send test” to prove delivery to one number.
        </p>
      </div>

      <form className="card" style={{ maxWidth: 520, marginBottom: "1rem" }} onSubmit={onAdd}>
        <div className="field">
          <label htmlFor="sub-phone">Phone number</label>
          <input
            id="sub-phone"
            required
            placeholder="+260971234567"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="sub-name">Name (optional)</label>
          <input id="sub-name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="sub-loc">Receive alerts for</label>
          <select
            id="sub-loc"
            value={locationId}
            onChange={(e) => setLocationId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">All areas</option>
            {locs.status === "success" &&
              locs.data.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
          </select>
        </div>
        {error && <ErrorState title="Something went wrong" detail={error} />}
        {notice && <p className="text-secondary">{notice}</p>}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Adding…" : "Add number"}
        </button>
      </form>

      {subs.status === "loading" && <LoadingState label="Loading subscribers" />}
      {subs.status === "error" && <ErrorState detail={subs.message} onRetry={retry} />}
      {subs.status === "success" && subs.data.length === 0 && (
        <EmptyState
          title="No numbers registered yet"
          detail="Add a phone number above to start receiving alert SMS."
        />
      )}
      {subs.status === "success" && subs.data.length > 0 && (
        <div className="card table-wrap">
          <table>
            <thead>
              <tr>
                <th>Number</th>
                <th>Name</th>
                <th>Area</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {subs.data.map((s) => (
                <tr key={s.id}>
                  <td>{s.phone}</td>
                  <td>{s.name || "—"}</td>
                  <td>{locName(s.location_id)}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button className="btn btn-secondary" onClick={() => onTest(s.id)}>
                      Send test
                    </button>{" "}
                    <button className="btn btn-secondary" onClick={() => onRemove(s.id)}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="record-cards">
            {subs.data.map((s) => (
              <div className="record-card" key={s.id}>
                <strong>{s.phone}</strong>
                <div className="text-muted">
                  {s.name || "No name"} · {locName(s.location_id)}
                </div>
                <div className="record-card-actions">
                  <button className="btn btn-secondary" onClick={() => onTest(s.id)}>
                    Send test
                  </button>
                  <button className="btn btn-secondary" onClick={() => onRemove(s.id)}>
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
