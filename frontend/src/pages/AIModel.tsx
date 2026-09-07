import { EmptyState } from "../components/ui/States";

export default function AIModel() {
  return (
    <div>
      <div className="page-header">
        <h1>AI Model Intelligence</h1>
        <p>Active model information, performance, and explainability.</p>
      </div>
      <EmptyState
        title="No trained model exists yet"
        detail="Roadmap Phases 5–9 (Baseline Models through Model Packaging) have not started — see docs/ROADMAP.md and docs/ML-METHODOLOGY.md. Model type, version, training date, dataset version, feature count, performance metrics, SHAP explanations, and the model-comparison table will appear here once training actually happens, populated with real measured numbers only."
      />
    </div>
  );
}
