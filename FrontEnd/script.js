// script.js — shared utilities
// Auth helpers used across pages
function authHeader() {
  const token = localStorage.getItem("token");
  return { "Authorization": `Bearer ${token}` };
}

function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  window.location.href = "login.html";
}
