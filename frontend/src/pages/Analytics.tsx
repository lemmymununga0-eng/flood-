import { EmptyState } from "../components/ui/States";

export default function Analytics() {
  return (
    <div>
      <div className="page-header">
        <h1>Flood Risk Analytics</h1>
        <p>Rainfall trends, risk trends, seasonality, and model performance comparison.</p>
      </div>
      <EmptyState
        title="No analytics data available yet"
        detail="Rainfall/risk trend charts need real weather observations (none stored yet — NASA POWER is blocked in this environment) and the model comparison table needs actually-trained models (none exist yet). Nothing here is fabricated to fill the page."
      />
    </div>
  );
}
