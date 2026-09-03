import { useEffect, useState } from "react";
import { fetchUsers, createUser } from "./api.js";

export default function Users() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("operario");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(null);
  const [createOk, setCreateOk] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setUsers(await fetchUsers());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setCreateError(null);
    setCreateOk(false);
    setCreating(true);
    try {
      await createUser({ username, password, fullName, role });
      setUsername("");
      setPassword("");
      setFullName("");
      setRole("operario");
      setCreateOk(true);
      await load();
    } catch (err) {
      setCreateError(err.message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="upload-form">
      <section className="table-card">
        <h2>➕ Crear usuario</h2>
        <form onSubmit={handleCreate} className="form-grid">
          <div className="form-row">
            <div className="form-field">
              <label>Usuario</label>
              <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required />
            </div>
            <div className="form-field">
              <label>Contraseña</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
          </div>
          <div className="form-row">
            <div className="form-field">
              <label>Nombre completo (opcional)</label>
              <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} />
            </div>
            <div className="form-field">
              <label>Rol</label>
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="operario">👷 Operario</option>
                <option value="administrador">🛡️ Administrador</option>
              </select>
            </div>
          </div>
          <button type="submit" className="btn-primary" disabled={creating}>
            {creating ? "Creando..." : "Crear usuario"}
          </button>
        </form>

        {createError && <div className="error-banner">⚠️ {createError}</div>}
        {createOk && !createError && <div className="hint">✅ Usuario creado correctamente.</div>}
      </section>

      <section className="table-card">
        <h2>👥 Usuarios registrados</h2>
        {error && <div className="error-banner">⚠️ {error}</div>}
        {loading ? (
          <p className="hint">Cargando...</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Nombre</th>
                <th>Rol</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.username}</td>
                  <td>{u.full_name || "—"}</td>
                  <td>
                    <span className={`badge ${u.role === "administrador" ? "badge--high" : "badge--low"}`}>
                      {u.role}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
