import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api.js";

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/dashboard/summary")
      .then((r) => setSummary(r.data))
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="error">{error}</div>;
  if (!summary) return <div className="loading">Yükleniyor...</div>;

  return (
    <div>
      <h2>Dashboard</h2>
      <div className="cards">
        <div className="card"><span className="card-value">{summary.devices_total}</span><span className="card-label">Toplam Cihaz</span></div>
        <div className="card up"><span className="card-value">{summary.devices_up}</span><span className="card-label">Çevrimiçi</span></div>
        <div className="card down"><span className="card-value">{summary.devices_down}</span><span className="card-label">Çevrimdışı</span></div>
        <div className="card warn"><span className="card-value">{summary.open_alerts}</span><span className="card-label">Açık Alarm</span></div>
        <div className="card"><span className="card-value">{summary.jobs_last_24h}</span><span className="card-label">İş (24s)</span></div>
      </div>

      <h3>Cihaz Tipleri</h3>
      <div className="cards">
        {Object.entries(summary.by_type).map(([type, count]) => (
          <div className="card" key={type}>
            <span className="card-value">{count}</span>
            <span className="card-label">{type}</span>
          </div>
        ))}
      </div>

      <h3>Son Alarmlar</h3>
      <table className="table">
        <thead>
          <tr><th>#</th><th>Önem</th><th>Mesaj</th><th>Durum</th><th>Tarih</th></tr>
        </thead>
        <tbody>
          {summary.recent_alerts.map((a) => (
            <tr key={a.id}>
              <td>{a.id}</td>
              <td><span className={`badge sev-${a.severity}`}>{a.severity}</span></td>
              <td>{a.message}</td>
              <td>{a.acknowledged ? "Onaylandı" : "Açık"}</td>
              <td>{new Date(a.created_at).toLocaleString("tr-TR")}</td>
            </tr>
          ))}
          {summary.recent_alerts.length === 0 && <tr><td colSpan="5">Alarm yok</td></tr>}
        </tbody>
      </table>

      <h3>Son İşler <Link to="/jobs" className="link">tümü</Link></h3>
      <table className="table">
        <thead>
          <tr><th>#</th><th>Tip</th><th>Durum</th><th>Cihaz</th><th>Tarih</th></tr>
        </thead>
        <tbody>
          {summary.recent_jobs.map((j) => (
            <tr key={j.id}>
              <td>{j.id}</td>
              <td>{j.job_type}</td>
              <td><span className={`badge st-${j.status}`}>{j.status}</span></td>
              <td>{j.device_id ? <Link to={`/devices/${j.device_id}`}>#{j.device_id}</Link> : "-"}</td>
              <td>{new Date(j.created_at).toLocaleString("tr-TR")}</td>
            </tr>
          ))}
          {summary.recent_jobs.length === 0 && <tr><td colSpan="5">İş yok</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
