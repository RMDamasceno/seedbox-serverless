import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./services/auth-context";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import Dashboard from "./pages/Dashboard";
import DownloadList from "./pages/DownloadList";
import AddDownload from "./pages/AddDownload";
import DownloadDetail from "./pages/DownloadDetail";
import InfraStatus from "./pages/InfraStatus";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/downloads" element={<DownloadList />} />
            <Route path="/downloads/new" element={<AddDownload />} />
            <Route path="/downloads/:id" element={<DownloadDetail />} />
            <Route path="/infrastructure" element={<InfraStatus />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
