import { useState } from "react";
import { analyzePhoto } from "./api.js";

export default function UploadForm() {
  const [file, setFile] = useState(null);
  const [apartment, setApartment] = useState("");
  const [date, setDate] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setResult(null);

    if (!file) {
      setError("Selecciona una fotografía.");
      return;
    }

    setLoading(true);
    try {
      const data = await analyzePhoto({ file, apartment, date, notes });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const tone = !result ? "low" : result.nivel_riesgo === "ALTO" ? "high" : result.nivel_riesgo === "MEDIO" ? "medium" : "low";

  return (
    <div className="upload-form">
      <section className="table-card">
        <h2>📸 Analizar Fotografía de Servicio</h2>

        <form onSubmit={handleSubmit} className="form-grid">
          <div className="form-field">
            <label>Fotografía de evidencia</label>
            <input
              type="file"
              accept=".jpg,.jpeg,.png,.webp,.jfif"
              onChange={(e) => setFile(e.target.files[0])}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-field">
              <label>Apartamento</label>
              <input type="text" placeholder="Ej: A-101" value={apartment} onChange={(e) => setApartment(e.target.value)} required />
            </div>
            <div className="form-field">
              <label>Fecha (DD/MM/AAAA)</label>
              <input type="text" placeholder="24/08/2026" value={date} onChange={(e) => setDate(e.target.value)} required />
            </div>
          </div>

          <div className="form-field">
            <label>Novedad reportada (opcional)</label>
            <input
              type="text"
              placeholder="Ej: Se encontró una fuga de agua debajo del lavamanos"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Analizando..." : "⚡ Analizar Fotografía"}
          </button>
        </form>

        {error && <div className="error-banner">⚠️ {error}</div>}
      </section>

      {result && (
        <section className="table-card">
          <h2>📊 Resultado del análisis</h2>
          <p className={`result-score badge badge--${tone}`}>
            Riesgo {result.nivel_riesgo} — {result.puntaje_riesgo}/100
          </p>

          {result.fraude_cruzado && (
            <p className="badge badge--high" style={{ marginTop: 8 }}>
              🚨 Fraude cruzado — la foto pertenece a {result.apartamento_coincidente}
            </p>
          )}

          <table>
            <tbody>
              <tr><td>Coincide con</td><td>{result.foto_coincidente || "Ninguna (primera visita)"}</td></tr>
              <tr><td>Método</td><td>{result.metodo_comparacion || "—"}</td></tr>
              <tr><td>Similitud visual</td><td>{result.similitud_visual ?? 0}%</td></tr>
              <tr><td>Fecha EXIF</td><td>{result.fecha_exif || "No detectada"}</td></tr>
              {result.novedad_categoria && (
                <tr>
                  <td>🧠 Novedad</td>
                  <td>{result.novedad_categoria} ({result.novedad_prioridad}) — {result.novedad_resumen}</td>
                </tr>
              )}
              <tr><td>Recomendación</td><td><strong>{result.recomendacion}</strong></td></tr>
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
