import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../api.js";

export default function DeviceDetail() {
  const { id } = useParams();
  const [device, setDevice] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [template, setTemplate] = useState("interface {interface}\n description {description}");
  const [variables, setVariables] = useState('{"interface": "Gi0/1", "description": "uplink"}');
  const [credForm, setCredForm] = useState({ name: "", access_method: "snmp", secret: '{"community": "public"}' });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = () => {
    api.get(`/devices/${id}`).then((r) => setDevice(r.data)).catch((e) => setError(e.message));
    api.get("/jobs", { params: { device_id: id, limit: 20 } }).then((r) => setJobs(r.data));
    api.get("/alerts", { params: { limit: 20 } }).then((r) => setAlerts(r.data.filter((a) => a.device_id === Number(id))));
    api.get(`/devices/${id}/metrics`, { params: { limit: 50 } }).then((r) => setMetrics(r.data));
  };

  useEffect(load, [id]);

  const act = async (fn, label) => {
    setMessage(""); setError("");
    try {
      const r = await fn();
      setMessage(`${label} iş kuyruğa alındı (job #${r.data.job_id})`);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const pushConfig = () =>
    act(
      () => api.post(`/devices/${id}/config`, { template, variables: JSON.parse(variables || "{}") }),
      "Config push"
    ).catch(() => setError("variables alanı geçerli JSON olmalı"));

  const addCred = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.post(`/devices/${id}/credentials`, {
        name: credForm.name,
        access_method: credForm.access_method,
        secret: JSON.parse(credForm.secret),
      });
      setMessage("Kimlik bilgisi kaydedildi (şifreli).");
      setCredForm({ name: "", access_method: "snmp", secret: "" });
      load();
    } catch (err) {
      setError(err.response?.data?.detail || "JSON geçersiz");
    }
  };

  if (error && !device) return <div className="error">{error}</div>;
  if (!device) return <div className="loading">Yükleniyor...</div>;

  return (
    <div>
      <h2>{device.hostname} <span className={`badge st-${device.status}`}>{device.status}</span></h2>
      {message && <div className="info">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="cards">
        <div className="card"><span className="card-label">IP</span><span className="card-value small">{device.ip_address}</span></div>
        <div className="card"><span className="card-label">Tip</span><span className="card-value small">{device.device_type}</span></div>
        <div className="card"><span className="card-label">Üretici</span><span className="card-value small">{device.vendor || "-"}</span></div>
        <div className="card"><span className="card-label">Model</span><span className="card-value small">{device.model || "-"}</span></div>
        <div className="card"><span className="card-label">Seri No</span><span className="card-value small">{device.serial || "-"}</span></div>
        <div className="card"><span className="card-label">Site</span><span className="card-value small">{device.site || "-"}</span></div>
      </div>

      <h3>İşlemler</h3>
      <div className="toolbar">
        <button onClick={() => act(() => api.post(`/devices/${id}/poll`), "Poll")}>SNMP Poll</button>
        <button onClick={() => act(() => api.post(`/devices/${id}/reboot`), "Reboot")}>Yeniden Başlat</button>
      </div>

      <h3>Config Push</h3>
      <textarea rows="4" value={template} onChange={(e) => setTemplate(e.target.value)} placeholder="Şablon (örn. CLI komutları, {degisken} formatı)" />
      <textarea rows="3" value={variables} onChange={(e) => setVariables(e.target.value)} placeholder='Değişkenler JSON, örn. {"ssid": "wifi"} ' />
      <button onClick={pushConfig}>Gönder</button>

      <h3>Kimlik Bilgileri</h3>
      <table className="table">
        <thead><tr><th>#</th><th>Ad</th><th>Yöntem</th></tr></thead>
        <tbody>
          {device.credentials?.map((c) => (
            <tr key={c.id}><td>{c.id}</td><td>{c.name}</td><td>{c.access_method}</td></tr>
          ))}
          {(!device.credentials || device.credentials.length === 0) && <tr><td colSpan="3">Kayıtlı kimlik yok</td></tr>}
        </tbody>
      </table>
      <form className="inline-form" onSubmit={addCred}>
        <input placeholder="Ad" value={credForm.name} onChange={(e) => setCredForm({ ...credForm, name: e.target.value })} required />
        <select value={credForm.access_method} onChange={(e) => setCredForm({ ...credForm, access_method: e.target.value })}>
          <option value="snmp">SNMP</option>
          <option value="ssh">SSH</option>
          <option value="tr069">TR-069</option>
          <option value="rest">REST API</option>
        </select>
        <input placeholder='Secret JSON' value={credForm.secret} onChange={(e) => setCredForm({ ...credForm, secret: e.target.value })} required />
        <button type="submit">Ekle</button>
      </form>

      <h3>Metrikler (son 50)</h3>
      <table className="table">
        <thead><tr><th>Zaman</th><th>Metrik</th><th>Değer</th></tr></thead>
        <tbody>
          {metrics.slice(-20).map((m, i) => (
            <tr key={i}><td>{new Date(m.ts).toLocaleString("tr-TR")}</td><td>{m.metric_key}</td><td>{m.value}</td></tr>
          ))}
          {metrics.length === 0 && <tr><td colSpan="3">Metrik yok</td></tr>}
        </tbody>
      </table>

      <h3>İşler</h3>
      <table className="table">
        <thead><tr><th>#</th><th>Tip</th><th>Durum</th><th>Hata</th><th>Tarih</th></tr></thead>
        <tbody>
          {jobs.map((j) => (
            <tr key={j.id}>
              <td>{j.id}</td><td>{j.job_type}</td>
              <td><span className={`badge st-${j.status}`}>{j.status}</span></td>
              <td>{j.error ? String(j.error).slice(0, 80) : "-"}</td>
              <td>{new Date(j.created_at).toLocaleString("tr-TR")}</td>
            </tr>
          ))}
          {jobs.length === 0 && <tr><td colSpan="5">İş yok</td></tr>}
        </tbody>
      </table>

      <h3>Alarmlar</h3>
      <table className="table">
        <thead><tr><th>#</th><th>Önem</th><th>Mesaj</th><th>Durum</th></tr></thead>
        <tbody>
          {alerts.map((a) => (
            <tr key={a.id}>
              <td>{a.id}</td><td><span className={`badge sev-${a.severity}`}>{a.severity}</span></td>
              <td>{a.message}</td><td>{a.acknowledged ? "Onaylandı" : "Açık"}</td>
            </tr>
          ))}
          {alerts.length === 0 && <tr><td colSpan="4">Alarm yok</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
