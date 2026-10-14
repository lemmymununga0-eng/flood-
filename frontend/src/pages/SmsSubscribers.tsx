import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../components/ui/icons";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { canSendSms, useAuth } from "../context/AuthContext";
import { useFetch } from "../hooks/useFetch";
import { fetchLocations } from "../services/api";
import { formatUtc } from "../services/sms";
import {
  addSubscriber,
  fetchSubscribers,
  optOutSubscriber,
  removeSubscriber,
  resubscribe,
} from "../services/subscribers";
import type { SmsSubscriber } from "../types";

function statusOf(s: SmsSubscriber): string {
  if (s.opted_out_at) return `Opted out ${formatUtc(s.opted_out_at)}`;
  if (!s.consent_at) return "No consent recorded — will not be texted";
  if (!s.active) return "Inactive";
  return `Subscribed · consent ${formatUtc(s.consent_at)}`;
}

export default function SmsSubscribers() {
  const { user, status } = useAuth();
  const allowed = canSendSms(user);
  const [reload, setReload] = useState(0);
  const [subs, retry] = useFetch(
    useCallback(() => (allowed ? fetchSubscribers() : Promise.resolve([])), [allowed, reload]),
  );
  const [locs] = useFetch(useCallback(fetchLocations, []));

  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [locationId, setLocationId] = useState<number | "">("");
  const [consent, setConsent] = useState(false);
  const [consentNote, setConsentNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const locName = (id: number | null) =>
    id === null
      ? "All areas"
      : locs.status === "success"
        ? (locs.data.find((l) => l.id === id)?.name ?? `#${id}`)
        : `#${id}`;

  async function run(action: () => Promise<unknown>, done: string) {
    setError(null);
    setNotice(null);
    try {
      await action();
      setReload((n) => n + 1);
      setNotice(done);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  async function onAdd(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    await run(async () => {
      await addSubscriber({
        phone,
        name,
        location_id: locationId === "" ? null : locationId,
        consent,
        consent_note: consentNote,
      });
      setPhone("");
      setName("");
      setConsent(false);
      setConsentNote("");
    }, "Number registered with recorded consent. Nothing has been sent.");
    setBusy(false);
  }

  const onResubscribe = (s: SmsSubscriber) => {
    const note = window.prompt(
      `Re-subscribe ${s.phone}? Only do this if they have agreed to receive flood-alert SMS again. How was consent given?`,
      "",
    );
    if (note === null) return;
    void run(() => resubscribe(s.id, note), "Re-subscribed with fresh consent.");
  };

  if (status === "checking") return <LoadingState label="Checking your session" />;

  if (!allowed) {
    return (
      <div>
        <div className="page-header">
          <h1>SMS Recipients</h1>
        </div>
        <div className="card" style={{ maxWidth: 480 }}>
          <p className="text-secondary">
            Managing SMS recipients requires an ADMIN account — enforced by the server.
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
          SMS Recipients
        </h1>
        <p>
          Only numbers with recorded consent can be texted, and only when an administrator sends
          from <Link to="/alerts/sms">SMS Alerts</Link>. Registering a number sends nothing.
        </p>
      </div>

      <form className="card" style={{ maxWidth: 520, marginBottom: "1rem" }} onSubmit={onAdd}>
        <div className="field">
          <label htmlFor="sub-phone">Phone number (international format)</label>
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
        <div className="field">
          <label htmlFor="sub-note">How was consent given? (optional)</label>
          <input
            id="sub-note"
            placeholder="e.g. verbal, in person, 2026-10-10"
            value={consentNote}
            onChange={(e) => setConsentNote(e.target.value)}
          />
        </div>
        <label className="check-row">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />{" "}
          This person has explicitly agreed to receive flood-alert SMS and can opt out at any time.
        </label>
        {error && <ErrorState title="Something went wrong" detail={error} />}
        {notice && <p className="text-secondary">{notice}</p>}
        <button className="btn btn-primary" type="submit" disabled={busy || !consent}>
          {busy ? "Adding…" : "Add number"}
        </button>
      </form>

      {subs.status === "loading" && <LoadingState label="Loading recipients" />}
      {subs.status === "error" && <ErrorState detail={subs.message} onRetry={retry} />}
      {subs.status === "success" && subs.data.length === 0 && (
        <EmptyState
          title="No numbers registered yet"
          detail="Add your own number above, then send yourself a test from SMS Alerts."
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
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {subs.data.map((s) => (
                <tr key={s.id}>
                  <td>{s.phone}</td>
                  <td>{s.name || "—"}</td>
                  <td>{locName(s.location_id)}</td>
                  <td>{statusOf(s)}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    {s.can_receive ? (
                      <button
                        className="btn btn-secondary"
                        onClick={() => run(() => optOutSubscriber(s.id), "Opt-out recorded.")}
                      >
                        Opt out
                      </button>
                    ) : (
                      <button className="btn btn-secondary" onClick={() => onResubscribe(s)}>
                        Record consent
                      </button>
                    )}{" "}
                    <button
                      className="btn btn-secondary"
                      onClick={() => {
                        if (window.confirm(`Delete ${s.phone} and its opt-out history?`))
                          void run(() => removeSubscriber(s.id), "Number deleted.");
                      }}
                    >
                      Delete
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
                <div className="text-muted">{statusOf(s)}</div>
                <div className="record-card-actions">
                  {s.can_receive ? (
                    <button
                      className="btn btn-secondary"
                      onClick={() => run(() => optOutSubscriber(s.id), "Opt-out recorded.")}
                    >
                      Opt out
                    </button>
                  ) : (
                    <button className="btn btn-secondary" onClick={() => onResubscribe(s)}>
                      Record consent
                    </button>
                  )}
                  <button
                    className="btn btn-secondary"
                    onClick={() => {
                      if (window.confirm(`Delete ${s.phone} and its opt-out history?`))
                        void run(() => removeSubscriber(s.id), "Number deleted.");
                    }}
                  >
                    Delete
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
