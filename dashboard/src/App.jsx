import { useEffect, useState } from "react";
import { fetchStats, fetchVisits, photoUrl } from "./api.js";
import Login from "./Login.jsx";
import UploadForm from "./UploadForm.jsx";
import Users from "./Users.jsx";

function StatCard({ label, value, tone }) {
  return (
    <div className={`stat-card stat-card--${tone}`}>
      <div className="stat-card__value">{value}</div>
      <div className="stat-card__label">{label}</div>
    </div>
  );
}

function RiskBadge({ score }) {
  let tone = "low";
  let texto = "Bajo";
  if (score >= 70) {
    tone = "high";
    texto = "Alto";
  } else if (score >= 40) {
    tone = "medium";
    texto = "Medio";
  }
  return (
    <span className={`badge badge--${tone}`}>
      {texto} ({score ?? 0})
    </span>
  );
}

function EstadoBadge({ estado }) {
  const map = {
    APPROVED: { texto: "Aprobada", tone: "low" },
    PENDING_REVIEW: { texto: "Revisión pendiente", tone: "high" },
    REJECTED: { texto: "Rechazada", tone: "high" },
  };
  const info = map[estado] || { texto: estado, tone: "medium" };
  return <span className={`badge badge--${info.tone}`}>{info.texto}</span>;
}

export default function App() {
  const [authed, setAuthed] = useState(!!sessionStorage.getItem("photocheck_token"));
  const [view, setView] = useState(
    sessionStorage.getItem("photocheck_role") === "operario" ? "upload" : "dashboard",
  );
  const [stats, setStats] = useState(null);
  const [visits, setVisits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  function handleLogout() {
    sessionStorage.removeItem("photocheck_token");
    sessionStorage.removeItem("photocheck_role");
    sessionStorage.removeItem("photocheck_name");
    setAuthed(false);
  }

  function handleLogin() {
    setAuthed(true);
    setView(sessionStorage.getItem("photocheck_role") === "operario" ? "upload" : "dashboard");
  }

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [statsData, visitsData] = await Promise.all([fetchStats(), fetchVisits()]);
      setStats(statsData);
      setVisits(visitsData);
    } catch (err) {
      if (err.message === "SESSION_INVALID") {
        handleLogout();
        return;
      }
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Solo consultamos /stats y /visits cuando REALMENTE estamos viendo el
  // dashboard — un operario nunca dispara estas llamadas (le darían 403).
  useEffect(() => {
    if (authed && view === "dashboard") loadData();
  }, [authed, view]);

  if (!authed) {
    return <Login onLogin={handleLogin} />;
  }

  const nombre = sessionStorage.getItem("photocheck_name");
  const rol = sessionStorage.getItem("photocheck_role");

  return (
    <div className="dashboard">
      <div className="barra-usuario">
        <span>👤 {nombre} ({rol})</span>
        <button className="btn-logout" onClick={handleLogout}>Cerrar sesión</button>
      </div>

      {rol === "administrador" && (
        <nav className="view-tabs">
          <button className={`tab ${view === "dashboard" ? "tab--active" : ""}`} onClick={() => setView("dashboard")}>
            📊 Dashboard
          </button>
          <button className={`tab ${view === "upload" ? "tab--active" : ""}`} onClick={() => setView("upload")}>
            📸 Subir Evidencia
          </button>
          <button className={`tab ${view === "users" ? "tab--active" : ""}`} onClick={() => setView("users")}>
            👥 Usuarios
          </button>
        </nav>
      )}

      {view === "upload" ? (
        <UploadForm />
      ) : view === "users" ? (
        <Users />
      ) : (
        <>
          <header className="dashboard__header">
            <div>
              <h1>
                PhotoCheck <span>AI</span>
              </h1>
              <p>Panel del supervisor — evidencias fotográficas registradas</p>
            </div>
            <button className="btn-refresh" onClick={loadData} disabled={loading}>
              {loading ? "Actualizando..." : "🔄 Actualizar"}
            </button>
          </header>

          {error && <div className="error-banner">⚠️ {error}. ¿Está corriendo la API en el puerto 8000?</div>}

          {stats && (
            <section className="stats-grid">
              <StatCard label="Total evidencias" value={stats.total} tone="neutral" />
              <StatCard label="Válidas" value={stats.validas} tone="low" />
              <StatCard label="Requieren revisión" value={stats.requieren_revision} tone="high" />
              <StatCard label="Posibles duplicadas" value={stats.posibles_duplicadas} tone="high" />
            </section>
          )}

          <section className="table-card">
            <h2>Evidencias registradas</h2>
            {loading && visits.length === 0 ? (
              <p className="hint">Cargando...</p>
            ) : visits.length === 0 ? (
              <p className="hint">Todavía no hay visitas registradas. Sube una foto desde la pestaña "Subir Evidencia".</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Foto</th>
                    <th>Apartamento</th>
                    <th>Operario</th>
                    <th>Fecha</th>
                    <th>Similitud</th>
                    <th>Riesgo</th>
                    <th>Estado</th>
                    <th>Método</th>
                    <th>Novedad</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {visits.map((v) => (
                    <tr key={v.id}>
                      <td>
                        <div className="thumb-pair">
                          <div className="thumb-slot">
                            <a href={photoUrl(v.id)} target="_blank" rel="noopener noreferrer">
                              <img src={photoUrl(v.id)} alt={`Foto actual visita ${v.id}`} className="thumb" />
                            </a>
                            <span className="thumb-label">Actual</span>
                          </div>
                          {v.coincide_con_id && (
                            <div className="thumb-slot">
                              <a href={photoUrl(v.coincide_con_id)} target="_blank" rel="noopener noreferrer">
                                <img src={photoUrl(v.coincide_con_id)} alt={`Foto anterior visita ${v.coincide_con_id}`} className="thumb" />
                              </a>
                              <span className="thumb-label">Anterior</span>
                            </div>
                          )}
                        </div>
                      </td>
                      <td>{v.apartamento}</td>
                      <td>{v.operario || "—"}</td>
                      <td>{v.fecha}</td>
                      <td>{v.similitud != null ? `${v.similitud}%` : "—"}</td>
                      <td><RiskBadge score={v.riesgo} /></td>
                      <td><EstadoBadge estado={v.estado} /></td>
                      <td>{v.metodo || "—"}</td>
                      <td>
                        {v.novedad_categoria ? (
                          <span title={v.novedad_resumen}>{v.novedad_categoria} ({v.novedad_prioridad})</span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>{v.fraude_cruzado && <span className="badge badge--high">🚨 Fraude cruzado</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </div>
  );
}
