import { EmptyState } from "../components/ui/States";

export default function CitizenReports() {
  return (
    <div>
      <div className="page-header">
        <h1>Citizen Flood Reports</h1>
        <p>Community-submitted flooding reports, pending verification.</p>
      </div>
      <EmptyState
        title="No citizen reports have been submitted"
        detail="Citizen reporting isn't wired up on the backend yet (no CitizenReport table/endpoint — see docs/DATABASE.md 'Not yet implemented'). This screen is a placeholder for that future feature, not a live form yet."
      />
    </div>
  );
}
