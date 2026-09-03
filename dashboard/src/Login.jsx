import { useState } from "react";
import { login } from "./api.js";

export default function Login({ onLogin }) {
  const [rolSeleccionado, setRolSeleccionado] = useState("operario");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const data = await login(username, password);

      console.log("Respuesta del login:", data);
      console.log("Rol recibido:", data.role);

      if (!data.access_token) {
        throw new Error("El servidor no devolvió un token de acceso.");
      }

      if (data.role !== rolSeleccionado) {
        sessionStorage.removeItem("photocheck_token");
        sessionStorage.removeItem("photocheck_role");
        sessionStorage.removeItem("photocheck_name");

        setError(
          `Esta cuenta es de "${data.role}", no de "${rolSeleccionado}". Selecciona la pestaña correcta arriba.`,
        );

        return;
      }

      // Guardar sesión
      sessionStorage.setItem("photocheck_token", data.access_token);
      sessionStorage.setItem("photocheck_role", data.role);
      sessionStorage.setItem(
        "photocheck_name",
        data.full_name || username
      );

      console.log(
        "Token guardado:",
        !!sessionStorage.getItem("photocheck_token")
      );

      onLogin();
    } catch (err) {
      console.error("Error de login:", err);
      setError(err.message || "No se pudo iniciar sesión.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>
          PhotoCheck <span>AI</span>
        </h1>

        <div className="role-switch">
          <button
            type="button"
            className={`role-option ${
              rolSeleccionado === "operario"
                ? "role-option--active"
                : ""
            }`}
            onClick={() => setRolSeleccionado("operario")}
          >
            👷 Operario
          </button>

          <button
            type="button"
            className={`role-option ${
              rolSeleccionado === "administrador"
                ? "role-option--active"
                : ""
            }`}
            onClick={() => setRolSeleccionado("administrador")}
          >
            🛡️ Administrador
          </button>
        </div>

        <input
          type="text"
          placeholder="Usuario"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
          required
        />

        <input
          type="password"
          placeholder="Contraseña"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        {error && (
          <div className="login-error">
            ⚠️ {error}
          </div>
        )}

        <button
          type="submit"
          className="btn-primary"
          disabled={loading}
        >
          {loading
            ? "Ingresando..."
            : `Ingresar como ${rolSeleccionado}`}
        </button>
      </form>
    </div>
  );
}