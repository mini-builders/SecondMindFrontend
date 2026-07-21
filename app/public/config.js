// Production backend URL — change to http://localhost:8000 for local development
window.BACKEND_URL =
  window.location.hostname === "localhost"
    ? "http://localhost:8000"
    : "https://secondmind-backend-production.up.railway.app";
