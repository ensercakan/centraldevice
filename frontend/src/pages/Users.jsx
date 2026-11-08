import { useEffect, useState } from "react";
import api from "../api.js";

export default function Users() {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({ username: "", email: "", password: "", role: "viewer" });
  const [error, setError] = useState("");

  const load = () => {
    api.get("/users").then((r) => setUsers(r.data)).catch((e) => setError(e.message));
  };

  useEffect(load, []);

  const create = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/users", form);
      setForm({ username: "", email: "", password: "", role: "viewer" });
      load();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const toggleActive = async (u) => {
    await api.patch(`/users/${u.id}`, { is_active: !u.is_active });
    load();
  };

  const changeRole = async (u, role) => {
    await api.patch(`/users/${u.id}`, { role });
    load();
  };

  return (
    <div>
      <h2>Kullanıcılar</h2>
      {error && <div className="error">{error}</div>}
      <form className="inline-form" onSubmit={create}>
        <input placeholder="Kullanıcı adı" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
        <input placeholder="E-posta" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
        <input placeholder="Şifre (min 8)" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
        <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
          <option value="viewer">viewer</option>
          <option value="operator">operator</option>
          <option value="admin">admin</option>
        </select>
        <button type="submit">Ekle</button>
      </form>
      <table className="table">
        <thead><tr><th>#</th><th>Kullanıcı</th><th>E-posta</th><th>Rol</th><th>Aktif</th><th></th></tr></thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.id}</td>
              <td>{u.username}</td>
              <td>{u.email}</td>
              <td>
                <select value={u.role} onChange={(e) => changeRole(u, e.target.value)}>
                  <option value="viewer">viewer</option>
                  <option value="operator">operator</option>
                  <option value="admin">admin</option>
                </select>
              </td>
              <td>{u.is_active ? "Evet" : "Hayır"}</td>
              <td><button onClick={() => toggleActive(u)}>{u.is_active ? "Pasifleştir" : "Aktifleştir"}</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
