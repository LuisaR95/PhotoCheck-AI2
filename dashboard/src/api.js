/**
 * PhotoCheck AI - Cliente de la API
 * --------------------------------------------------------------
 * API backend: http://127.0.0.1:8000
 */

const API_BASE = "http://127.0.0.1:8000";
const TOKEN_KEY = "photocheck_token";

/**
 * Devuelve el header de autenticación.
 */
function authHeader() {
  const token = sessionStorage.getItem(TOKEN_KEY);

  return token
    ? { Authorization: `Bearer ${token}` }
    : {};
}

/**
 * LOGIN
 */
export async function login(username, password) {
  const body = new URLSearchParams();

  body.append("username", username);
  body.append("password", password);

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));

    throw new Error(
      err.detail || "Usuario o contraseña incorrectos."
    );
  }

  return res.json();
}

/**
 * ESTADÍSTICAS
 */
export async function fetchStats() {
  const res = await fetch(`${API_BASE}/stats`, {
    headers: authHeader(),
  });

  if (res.status === 401 || res.status === 403) {
    throw new Error("SESSION_INVALID");
  }

  if (!res.ok) {
    throw new Error("No se pudo cargar el resumen");
  }

  return res.json();
}

/**
 * VISITAS
 */
export async function fetchVisits() {
  const res = await fetch(`${API_BASE}/visits`, {
    headers: authHeader(),
  });

  if (res.status === 401 || res.status === 403) {
    throw new Error("SESSION_INVALID");
  }

  if (!res.ok) {
    throw new Error("No se pudieron cargar las visitas");
  }

  return res.json();
}

/**
 * USUARIOS
 */
export async function fetchUsers() {
  const res = await fetch(`${API_BASE}/users`, {
    method: "GET",
    headers: {
      ...authHeader(),
    },
  });

  if (res.status === 401 || res.status === 403) {
    throw new Error("SESSION_INVALID");
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));

    throw new Error(
      data.detail || "No se pudieron cargar los usuarios"
    );
  }

  return res.json();
}

/**
 * CREAR USUARIO
 */
export async function createUser({
  username,
  password,
  fullName,
  role,
}) {
  const res = await fetch(`${API_BASE}/users`, {
    method: "POST",
    headers: {
      ...authHeader(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username,
      password,
      full_name: fullName,
      role,
    }),
  });

  const data = await res.json().catch(() => ({}));

  if (res.status === 401 || res.status === 403) {
    throw new Error("SESSION_INVALID");
  }

  if (!res.ok) {
    throw new Error(
      data.detail || "No se pudo crear el usuario"
    );
  }

  return data;
}

/**
 * ANALIZAR FOTOGRAFÍA
 */
export async function analyzePhoto({
  file,
  apartment,
  date,
  notes,
}) {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("apartment", apartment);
  formData.append("date", date);

  if (notes) {
    formData.append("notes", notes);
  }

  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: {
      ...authHeader(),
    },
    body: formData,
  });

  const data = await res.json().catch(() => ({}));

  if (res.status === 401 || res.status === 403) {
    throw new Error("SESSION_INVALID");
  }

  if (!res.ok) {
    throw new Error(
      data.detail || "Error al analizar la fotografía."
    );
  }

  return data;
}

/**
 * URL DE LA FOTOGRAFÍA DE UNA VISITA
 */
export function photoUrl(visitId) {
  const token = sessionStorage.getItem(TOKEN_KEY);

  return `${API_BASE}/visits/${visitId}/photo?token=${encodeURIComponent(
    token || ""
  )}`;
}