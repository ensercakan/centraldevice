import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api.js";

const TYPE_LABELS = {
  router: "Router",
  switch: "Switch",
  access_point: "Access Point",
  repeater: "Repeater",
  modem: "Modem",
  other: "Diğer",
};

export default function Devices() {
  const [devices, setDevices] = useState([]);
  const [q, setQ] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ hostname: "", ip_address: "", device_type: "other", site: "" });
  const [error, setError] = useState("");

  const load = () => {
    const params = {};
    if (q) params.q = q;
    if (typeFilter) params.device_type = typeFilter;
    api.get("/devices", { params }).then((r) => setDevices(r.data)).catch((e) => setError(e.message));
  };

  useEffect(load, [q, typeFilter]);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/devices", form);
      setShowForm(false);
      setForm({ hostname: "", ip_address: "", device_type: "other", site: "" });
      load();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const discover = async () => {
    const subnet = window.prompt("Taranacak ağ (örn. 192.168.1.0/24):", "192.168.1.0/24");
    if (!subnet) return;
    try {
      await api.post("/devices/discover", { subnet });
      load();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Cihaz silinsin mi?")) return;
    try {
      await api.delete(`/devices/${id}`);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  return (
    <div>
      <h2>Cihazlar</h2>
      {error && <div className="error">{error}</div>}
      <div className="toolbar">
        <input placeholder="Ara (ad/ip/site)" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
          <option value="">Tüm tipler</option>
          {Object.entries(TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <button onClick={() => setShowForm(!showForm)}>+ Yeni Cihaz</button>
        <button onClick={discover}>Ağı Tara</button>
      </div>

      {showForm && (
        <form className="inline-form" onSubmit={submit}>
          <input placeholder="Hostname" value={form.hostname} onChange={(e) => setForm({ ...form, hostname: e.target.value })} required />
          <input placeholder="IP adresi" value={form.ip_address} onChange={(e) => setForm({ ...form, ip_address: e.target.value })} required />
          <select value={form.device_type} onChange={(e) => setForm({ ...form, device_type: e.target.value })}>
            {Object.entries(TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <input placeholder="Site" value={form.site} onChange={(e) => setForm({ ...form, site: e.target.value })} />
          <button type="submit">Kaydet</button>
        </form>
      )}

      <table className="table">
        <thead>
          <tr>
            <th>#</th><th>Hostname</th><th>IP</th><th>Tip</th><th>Üretici/Model</th>
            <th>Site</th><th>Durum</th><th>Son Görülme</th><th></th>
          </tr>
        </thead>
        <tbody>
          {devices.map((d) => (
            <tr key={d.id}>
              <td>{d.id}</td>
              <td><Link to={`/devices/${d.id}`}>{d.hostname}</Link></td>
              <td>{d.ip_address}</td>
              <td>{TYPE_LABELS[d.device_type] || d.device_type}</td>
              <td>{[d.vendor, d.model].filter(Boolean).join(" / ")}</td>
              <td>{d.site}</td>
              <td><span className={`badge st-${d.status}`}>{d.status}</span></td>
              <td>{d.last_seen ? new Date(d.last_seen).toLocaleString("tr-TR") : "-"}</td>
              <td><button className="danger" onClick={() => remove(d.id)}>Sil</button></td>
            </tr>
          ))}
          {devices.length === 0 && <tr><td colSpan="9">Cihaz bulunamadı</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
