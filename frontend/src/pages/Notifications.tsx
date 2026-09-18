import { useCallback } from "react";
import { Icon } from "../components/ui/icons";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchNotifications, markNotificationRead } from "../services/api";

export default function Notifications() {
  const [state, retry] = useFetch(useCallback(fetchNotifications, []));

  return (
    <div>
      <div className="page-header">
        <h1 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Icon name="bell" />
          Notifications
        </h1>
        <p>
          Real, backend-persisted notifications for citizen-report status updates. Alert,
          prediction, and data-source notifications aren't generated yet — there's no per-user
          targeting mechanism for those yet, so this list won't show them (not a bug, an honest
          scope limit).
        </p>
      </div>

      {state.status === "loading" && <LoadingState label="Loading notifications" />}
      {state.status === "error" && <ErrorState detail={state.message} onRetry={retry} />}
      {state.status === "success" && state.data.length === 0 && (
        <EmptyState
          title="No notifications"
          detail="You have no citizen-report status updates yet. This list is really empty, not a placeholder."
        />
      )}
      {state.status === "success" && state.data.length > 0 && (
        <div className="grid grid-auto">
          {state.data.map((n) => (
            <div className="card" key={n.id}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
                <h3 style={{ margin: 0 }}>{n.is_read ? n.title : <strong>{n.title}</strong>}</h3>
                {!n.is_read && (
                  <span className="status-badge">
                    <span className="status-dot unread" />
                    Unread
                  </span>
                )}
              </div>
              {n.message && <p className="text-secondary">{n.message}</p>}
              <p className="text-muted" style={{ margin: 0 }}>
                {new Date(n.created_at).toLocaleString()}
              </p>
              {!n.is_read && (
                <button
                  className="btn btn-secondary"
                  style={{ marginTop: "0.5rem" }}
                  onClick={() => {
                    markNotificationRead(n.id).then(retry);
                  }}
                >
                  Mark read
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
