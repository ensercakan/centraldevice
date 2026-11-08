import { useEffect, useState } from "react";
import api from "../api.js";
import { useAuth } from "../auth.jsx";

export default function Alerts() {
  const { user } = useAuth();
  const [alerts, setAlerts] = useState([]);
  const [showAcked, setShowAcked] = useState(true);
  const canAck = user && (user.role === "admin" || user.role === "operator");

  const load = () => {
    api.get("/alerts", { params: { limit: 200, ...(showAcked ? {} : { acknowledged: false }) } })
      .then((r) => setAlerts(r.data));
  };

  useEffect(load, [showAcked]);

  const ack = async (id) => {
    await api.post(`/alerts/${id}/acknowledge`);
    load();
  };

  return (
    <div>
      <h2>Alarmlar</h2>
      <div className="toolbar">
        <label>
          <input type="checkbox" checked={showAcked} onChange={(e) => setShowAcked(e.target.checked)} /> Onaylananları da göster
        </label>
      </div>
      <table className="table">
        <thead><tr><th>#</th><th>Önem</th><th>Mesaj</th><th>Cihaz</th><th>Tarih</th><th></th></tr></thead>
        <tbody>
          {alerts.map((a) => (
            <tr key={a.id}>
              <td>{a.id}</td>
              <td><span className={`badge sev-${a.severity}`}>{a.severity}</span></td>
              <td>{a.message}</td>
              <td>{a.device_id || "-"}</td>
              <td>{new Date(a.created_at).toLocaleString("tr-TR")}</td>
              <td>{canAck && !a.acknowledged && <button onClick={() => ack(a.id)}>Onayla</button>}</td>
            </tr>
          ))}
          {alerts.length === 0 && <tr><td colSpan="6">Alarm yok</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
