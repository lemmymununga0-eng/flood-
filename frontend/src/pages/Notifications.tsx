import { EmptyState } from "../components/ui/States";

export default function Notifications() {
  return (
    <div>
      <div className="page-header">
        <h1>Notifications</h1>
      </div>
      <EmptyState
        title="No notifications"
        detail="Notification generation (new predictions, issued alerts, citizen reports, data-source sync) isn't implemented yet — this is an honest empty state, not a missing feature bug."
      />
    </div>
  );
}
