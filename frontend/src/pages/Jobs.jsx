import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api.js";
import { useAuth } from "../auth.jsx";

export default function Jobs() {
  const { user } = useAuth();
  const [jobs, setJobs] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState("");
  const canRetry = user && (user.role === "admin" || user.role === "operator");

  const load = () => {
    const params = { limit: 200 };
    if (statusFilter) params.status = statusFilter;
    api.get("/jobs", { params }).then((r) => setJobs(r.data)).catch((e) => setError(e.message));
  };

  useEffect(load, [statusFilter]);

  const retry = async (id) => {
    try {
      await api.post(`/jobs/${id}/retry`);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  return (
    <div>
      <h2>İşler</h2>
      {error && <div className="error">{error}</div>}
      <div className="toolbar">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">Tüm durumlar</option>
          <option value="queued">queued</option>
          <option value="running">running</option>
          <option value="succeeded">succeeded</option>
          <option value="failed">failed</option>
        </select>
      </div>
      <table className="table">
        <thead>
          <tr><th>#</th><th>Tip</th><th>Durum</th><th>Cihaz</th><th>Sonuç/Hata</th><th>Başlangıç</th><th>Bitiş</th><th></th></tr>
        </thead>
        <tbody>
          {jobs.map((j) => (
            <tr key={j.id}>
              <td>{j.id}</td>
              <td>{j.job_type}</td>
              <td><span className={`badge st-${j.status}`}>{j.status}</span></td>
              <td>{j.device_id ? <Link to={`/devices/${j.device_id}`}>#{j.device_id}</Link> : "-"}</td>
              <td className="mono">{j.error ? j.error.slice(0, 100) : j.result ? j.result.slice(0, 100) : "-"}</td>
              <td>{new Date(j.created_at).toLocaleString("tr-TR")}</td>
              <td>{j.finished_at ? new Date(j.finished_at).toLocaleString("tr-TR") : "-"}</td>
              <td>{canRetry && j.status === "failed" && <button onClick={() => retry(j.id)}>Tekrar Dene</button>}</td>
            </tr>
          ))}
          {jobs.length === 0 && <tr><td colSpan="8">İş yok</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
