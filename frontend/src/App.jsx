import { Navigate, NavLink, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Devices from "./pages/Devices.jsx";
import DeviceDetail from "./pages/DeviceDetail.jsx";
import Jobs from "./pages/Jobs.jsx";
import Alerts from "./pages/Alerts.jsx";
import Users from "./pages/Users.jsx";

function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="layout">
      <nav className="sidebar">
        <div className="brand">centraldevice</div>
        <NavLink to="/">Dashboard</NavLink>
        <NavLink to="/devices">Cihazlar</NavLink>
        <NavLink to="/jobs">İşler</NavLink>
        <NavLink to="/alerts">Alarmlar</NavLink>
        {user && user.role === "admin" && <NavLink to="/users">Kullanıcılar</NavLink>}
        <div className="sidebar-footer">
          <span>{user?.username} ({user?.role})</span>
          <button onClick={logout}>Çıkış</button>
        </div>
      </nav>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

function ProtectedRoute() {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading">Yükleniyor...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Layout />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/devices" element={<Devices />} />
        <Route path="/devices/:id" element={<DeviceDetail />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/users" element={<Users />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
