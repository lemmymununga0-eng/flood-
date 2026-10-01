import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppProviders } from "./providers";
import AuthLayout from "./layouts/AuthLayout";
import DashboardLayout from "./layouts/DashboardLayout";
import PublicLayout from "./layouts/PublicLayout";
import About from "./pages/About";
import AIModel from "./pages/AIModel";
import Alerts from "./pages/Alerts";
import Analytics from "./pages/Analytics";
import CitizenReports from "./pages/CitizenReports";
import CreateAlert from "./pages/CreateAlert";
import Dashboard from "./pages/Dashboard";
import DataSources from "./pages/DataSources";
import HistoricalEventDetail from "./pages/HistoricalEventDetail";
import HistoricalEvents from "./pages/HistoricalEvents";
import Landing from "./pages/Landing";
import LocationDetail from "./pages/LocationDetail";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";
import Notifications from "./pages/Notifications";
import PredictionDetail from "./pages/PredictionDetail";
import Predictions from "./pages/Predictions";
import Profile from "./pages/Profile";
import RiskMap from "./pages/RiskMap";
import Settings from "./pages/Settings";
import Signup from "./pages/Signup";
import SystemStatus from "./pages/SystemStatus";

export default function App() {
  return (
    <AppProviders>
    <BrowserRouter>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route path="/" element={<Landing />} />
          <Route path="/about" element={<About />} />
        </Route>

        <Route element={<AuthLayout />}>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
        </Route>

        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/risk-map" element={<RiskMap />} />
          <Route path="/locations/:id" element={<LocationDetail />} />
          <Route path="/predictions" element={<Predictions />} />
          <Route path="/predictions/:id" element={<PredictionDetail />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/historical-events" element={<HistoricalEvents />} />
          <Route path="/historical-events/:id" element={<HistoricalEventDetail />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/alerts/create" element={<CreateAlert />} />
          <Route path="/reports" element={<CitizenReports />} />
          <Route path="/ai-model" element={<AIModel />} />
          <Route path="/data-sources" element={<DataSources />} />
          <Route path="/system-status" element={<SystemStatus />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/profile" element={<Profile />} />
        </Route>

        <Route path="/dashboard-old" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
    </AppProviders>
  );
}
