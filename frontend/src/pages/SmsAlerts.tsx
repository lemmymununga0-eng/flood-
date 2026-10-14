import { Fragment, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../components/ui/icons";
import { ErrorState, LoadingState } from "../components/ui/States";
import { canSendSms, useAuth } from "../context/AuthContext";
import { useFetch } from "../hooks/useFetch";
import { fetchLocations } from "../services/api";
import {
  fetchSmsBroadcast,
  fetchSmsHistory,
  fetchSmsStatus,
  formatUtc,
  newIdempotencyKey,
  previewSms,
  sendBroadcastSms,
  sendTestSms,
} from "../services/sms";
import { fetchSubscribers } from "../services/subscribers";
import type {
  RiskLevel,
  SmsBroadcastDetail,
  SmsBroadcastSummary,
  SmsMessageRecord,
  SmsPreview,
  SmsProviderStatus,
} from "../types";

// Honest wording: "submitted" is what the provider said when we handed it the message,
// NOT proof the handset received it. Only a delivery report can say "delivered".
const BROADCAST_STATUS: Record<SmsBroadcastSummary["status"], string> = {
  sending: "Sending…",
  submitted: "Submitted to provider — delivery not confirmed",
  partial: "Partly submitted — some recipients were not accepted",
  failed: "Failed — the provider did not accept it; nothing was sent",
  unknown: "Unknown — no usable provider response; it may or may not have been sent",
  simulated: "Simulated — nothing was sent",
};

const DELIVERY: Record<SmsMessageRecord["delivery_status"], string> = {
  not_reported: "No delivery report yet",
  pending: "Carrier has it, not yet delivered",
  delivered: "Delivered (confirmed by provider report)",
  failed: "Delivery failed",
};

function MessageTable({ messages }: { messages: SmsMessageRecord[] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>To</th>
            <th>Submission</th>
            <th>Provider message ID</th>
            <th>Delivery</th>
          </tr>
        </thead>
        <tbody>
          {messages.map((m) => (
            <tr key={m.id}>
              <td>{m.phone_masked}</td>
              <td>
                <strong>{m.submission_status}</strong>
                <div className="text-muted">{m.submission_detail}</div>
                {m.cost && <div className="text-muted">Cost: {m.cost}</div>}
              </td>
              <td>{m.provider_message_id ?? "—"}</td>
              <td>
                {DELIVERY[m.delivery_status]}
                {m.delivery_reported_at && (
                  <div className="text-muted">{formatUtc(m.delivery_reported_at)}</div>
                )}
                {m.failure_reason && <div className="text-muted">{m.failure_reason}</div>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProviderCard({ s }: { s: SmsProviderStatus }) {
  return (
    <div className="card" style={{ marginBottom: "1rem" }}>
      <h3 style={{ marginTop: 0 }}>Provider</h3>
      {!s.real ? (
        <p>
          <strong>Simulation mode.</strong> Nothing is sent to any phone; attempts are recorded as
          “simulated”. Set <code>SMS_PROVIDER=africastalking</code> on the backend to send for real.
        </p>
      ) : (
        <p>
          <strong>Africa&apos;s Talking ({s.environment})</strong>
          {s.environment === "sandbox" && (
            <span className="text-muted">
              {" "}
              — sandbox messages go to the Africa&apos;s Talking simulator, not to real handsets.
            </span>
          )}
        </p>
      )}
      {!s.configured && (
        <ErrorState
          title="Provider is not configured"
          detail={`Missing or invalid on the backend: ${s.missing.join("; ")}`}
        />
      )}
      {s.real && (
        <ul className="text-secondary" style={{ paddingLeft: "1.1rem", margin: 0 }}>
          <li>
            Test SMS accepted by provider: <strong>{s.real_test_accepted ? "yes" : "not yet"}</strong>
          </li>
          <li>
            Group broadcasts:{" "}
            <strong>
              {s.group_broadcast_unlocked
                ? "unlocked"
                : !s.broadcast_enabled
                  ? "off (SMS_BROADCAST_ENABLED=false)"
                  : "locked until a real test SMS is accepted"}
            </strong>
          </li>
          <li>
            Delivery reports:{" "}
            <strong>{s.delivery_reports_enabled ? "callback configured" : "not configured — delivery will stay “no report”"}</strong>
          </li>
          <li>Sender ID: {s.sender_id_set ? "set" : "not set (provider default)"}</li>
        </ul>
      )}
    </div>
  );
}

export default function SmsAlerts() {
  const { user, status } = useAuth();
  const allowed = canSendSms(user);
  const [reload, setReload] = useState(0);
  const [provider] = useFetch(useCallback(() => (allowed ? fetchSmsStatus() : new Promise<never>(() => {})), [allowed, reload]));
  const [locs] = useFetch(useCallback(fetchLocations, []));
  const [subs] = useFetch(useCallback(() => (allowed ? fetchSubscribers() : Promise.resolve([])), [allowed, reload]));
  const [history, retryHistory] = useFetch(useCallback(() => (allowed ? fetchSmsHistory() : Promise.resolve([])), [allowed, reload]));

  const [mode, setMode] = useState<"test" | "broadcast">("test");
  const [locationId, setLocationId] = useState<number | "">("");
  const [risk, setRisk] = useState<RiskLevel>("high");
  const [message, setMessage] = useState("");
  const [testSub, setTestSub] = useState<number | "">("");

  const [preview, setPreview] = useState<SmsPreview | null>(null);
  const [key, setKey] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState<"preview" | "send" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SmsBroadcastDetail | null>(null);
  const [open, setOpen] = useState<SmsBroadcastDetail | null>(null);

  // Any edit invalidates the preview and the confirmation: what is sent is what was shown.
  useEffect(() => {
    setPreview(null);
    setKey(null);
    setConfirmed(false);
  }, [mode, locationId, risk, message, testSub]);

  const consenting = subs.status === "success" ? subs.data.filter((s) => s.can_receive) : [];
  const ready = locationId !== "" && message.trim() !== "" && (mode === "broadcast" || testSub !== "");

  async function onPreview() {
    if (locationId === "") return;
    setBusy("preview");
    setError(null);
    setResult(null);
    try {
      const p = await previewSms({
        location_id: locationId,
        risk_level: risk,
        message,
        ...(mode === "test" && testSub !== "" ? { subscriber_id: testSub } : {}),
      });
      setPreview(p);
      setKey(newIdempotencyKey());
      setConfirmed(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setBusy(null);
    }
  }

  async function onSend() {
    if (locationId === "" || !preview || !key || !confirmed) return;
    setBusy("send");
    setError(null);
    try {
      const base = { location_id: locationId, risk_level: risk, message, idempotency_key: key };
      const sent =
        mode === "test"
          ? await sendTestSms({ ...base, subscriber_id: Number(testSub) })
          : await sendBroadcastSms({ ...base, expected_recipient_count: preview.recipient_count });
      setResult(sent);
      setPreview(null);
      setConfirmed(false);
      setReload((n) => n + 1);
    } catch (err) {
      // The request failed: say so. Nothing is reported as sent.
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setBusy(null);
    }
  }

  async function toggleDetail(id: number) {
    if (open?.id === id) return setOpen(null);
    try {
      setOpen(await fetchSmsBroadcast(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  if (status === "checking") return <LoadingState label="Checking your session" />;
  if (!allowed) {
    return (
      <div>
        <div className="page-header">
          <h1>SMS Alerts</h1>
        </div>
        <div className="card" style={{ maxWidth: 480 }}>
          <p className="text-secondary">Sending SMS requires an ADMIN account — enforced by the server.</p>
          {status === "anonymous" && (
            <Link className="btn btn-primary" to="/login">
              Sign in
            </Link>
          )}
        </div>
      </div>
    );
  }

  const canSendReal = preview?.can_send ?? false;

  return (
    <div>
      <div className="page-header">
        <h1 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Icon name="alerts" />
          SMS Alerts
        </h1>
        <p>
          Manual sending only — nothing is ever texted automatically. Recipients must have recorded
          consent (<Link to="/alerts/subscribers">manage recipients</Link>).
        </p>
      </div>

      {provider.status === "loading" && <LoadingState label="Checking SMS provider" />}
      {provider.status === "error" && <ErrorState detail={provider.message} />}
      {provider.status === "success" && <ProviderCard s={provider.data} />}

      <div className="card" style={{ maxWidth: 640, marginBottom: "1rem" }}>
        <h3 style={{ marginTop: 0 }}>1. Compose</h3>
        <div className="field">
          <label>Send to</label>
          <label className="check-row">
            <input type="radio" checked={mode === "test"} onChange={() => setMode("test")} /> One test
            message to my own registered number
          </label>
          <label className="check-row">
            <input type="radio" checked={mode === "broadcast"} onChange={() => setMode("broadcast")} />{" "}
            Group broadcast to all consenting recipients for the location
          </label>
        </div>
        {mode === "test" && (
          <div className="field">
            <label htmlFor="test-sub">Test recipient</label>
            <select id="test-sub" value={testSub} onChange={(e) => setTestSub(e.target.value ? Number(e.target.value) : "")}>
              <option value="">Select a registered, consenting number…</option>
              {consenting.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name || "Unnamed"} · {s.phone}
                </option>
              ))}
            </select>
            {subs.status === "success" && consenting.length === 0 && (
              <p className="text-muted">
                No consenting numbers yet — <Link to="/alerts/subscribers">register your own number</Link> first.
              </p>
            )}
          </div>
        )}
        <div className="field">
          <label htmlFor="sms-loc">Location</label>
          <select id="sms-loc" value={locationId} onChange={(e) => setLocationId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Select a location…</option>
            {locs.status === "success" &&
              locs.data.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="sms-risk">Risk level</label>
          <select id="sms-risk" value={risk} onChange={(e) => setRisk(e.target.value as RiskLevel)}>
            <option value="low">Low</option>
            <option value="moderate">Moderate</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="sms-msg">Message ({message.length}/200)</label>
          <textarea id="sms-msg" rows={3} maxLength={200} value={message} onChange={(e) => setMessage(e.target.value)} />
        </div>
        <button className="btn btn-primary" disabled={!ready || busy !== null} onClick={onPreview}>
          {busy === "preview" ? "Checking…" : "Preview"}
        </button>
      </div>

      {error && (
        <div style={{ maxWidth: 640 }}>
          <ErrorState title="Not sent" detail={error} />
        </div>
      )}

      {preview && (
        <div className="card" style={{ maxWidth: 640, marginBottom: "1rem" }}>
          <h3 style={{ marginTop: 0 }}>2. Review &amp; confirm</h3>
          <p className="text-muted" style={{ marginBottom: 4 }}>
            Exact text ({preview.length} characters, ~{preview.segments} SMS part
            {preview.segments === 1 ? "" : "s"}):
          </p>
          <blockquote style={{ margin: "0 0 1rem", padding: "0.75rem", background: "var(--surface-2, #f3f4f6)", borderRadius: 8 }}>
            {preview.body}
          </blockquote>
          <p>
            <strong>{preview.recipient_count}</strong> recipient{preview.recipient_count === 1 ? "" : "s"}
            {preview.recipients.length > 0 && (
              <span className="text-muted">
                {" "}
                — {preview.recipients.map((r) => `${r.name || "Unnamed"} (${r.phone_masked})`).join(", ")}
              </span>
            )}
          </p>
          {preview.skipped_not_allowlisted > 0 && (
            <p className="text-muted">
              {preview.skipped_not_allowlisted} consenting number(s) excluded by SMS_ALLOWED_NUMBERS.
            </p>
          )}
          {preview.blocking_reasons.length > 0 && (
            <ErrorState title="Cannot send yet" detail={preview.blocking_reasons.join(" ")} />
          )}
          {canSendReal && (
            <>
              <label className="check-row">
                <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} /> I confirm
                sending this message to {preview.recipient_count} recipient{preview.recipient_count === 1 ? "" : "s"}
                {provider.status === "success" && !provider.data.real ? " (simulation — nothing will actually be sent)" : "."}
              </label>
              <button className="btn btn-primary" disabled={!confirmed || busy !== null} onClick={onSend}>
                {busy === "send" ? "Sending…" : mode === "test" ? "Send test SMS" : `Send to ${preview.recipient_count}`}
              </button>
            </>
          )}
        </div>
      )}

      {result && (
        <div className="card" style={{ maxWidth: 800, marginBottom: "1rem" }}>
          <h3 style={{ marginTop: 0 }}>Result (recorded by the backend)</h3>
          <p>
            <strong>{BROADCAST_STATUS[result.status]}</strong>
            {result.replayed && <span className="text-muted"> — this was an earlier send; nothing new was sent.</span>}
          </p>
          <p className="text-muted">
            {result.accepted_count} of {result.recipient_count} accepted by {result.provider}
            {result.environment !== "none" ? ` (${result.environment})` : ""} · {result.delivered_count} confirmed delivered
          </p>
          <MessageTable messages={result.messages} />
        </div>
      )}

      <div className="card" style={{ marginBottom: "1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <h3 style={{ marginTop: 0 }}>History</h3>
          <button className="btn btn-secondary" onClick={() => setReload((n) => n + 1)}>
            Refresh
          </button>
        </div>
        {history.status === "loading" && <LoadingState label="Loading history" />}
        {history.status === "error" && <ErrorState detail={history.message} onRetry={retryHistory} />}
        {history.status === "success" && history.data.length === 0 && (
          <p className="text-secondary">No SMS has been attempted yet.</p>
        )}
        {history.status === "success" && history.data.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>When</th>
                  <th>Type</th>
                  <th>Outcome</th>
                  <th>Accepted</th>
                  <th>Delivered</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {history.data.map((b) => (
                  <Fragment key={b.id}>
                    <tr>
                      <td>{formatUtc(b.created_at)}</td>
                      <td>{b.kind === "test" ? "Test" : "Broadcast"}</td>
                      <td>{BROADCAST_STATUS[b.status]}</td>
                      <td>
                        {b.accepted_count}/{b.recipient_count}
                      </td>
                      <td>{b.delivered_count}</td>
                      <td>
                        <button className="btn btn-secondary" onClick={() => toggleDetail(b.id)}>
                          {open?.id === b.id ? "Hide" : "Details"}
                        </button>
                      </td>
                    </tr>
                    {open?.id === b.id && (
                      <tr>
                        <td colSpan={6}>
                          <p className="text-muted">{open.body}</p>
                          <MessageTable messages={open.messages} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
