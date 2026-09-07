import FloodEventsPanel from "./components/FloodEventsPanel";
import LocationsPanel from "./components/LocationsPanel";
import PredictionsPanel from "./components/PredictionsPanel";
import WeatherPanel from "./components/WeatherPanel";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>FloodShield Zambia</h1>
        <p>
          Early development skeleton — Phase 1 (Research &amp; Data) of the project
          roadmap. Real data, real API calls, no fabricated predictions. Not a finished
          system.
        </p>
      </header>
      <main className="grid">
        <LocationsPanel />
        <FloodEventsPanel />
        <WeatherPanel />
        <PredictionsPanel />
      </main>
      <footer className="app-footer">
        <p>Model-estimated flood risk is decision-support only, not an official warning.</p>
      </footer>
    </div>
  );
}
