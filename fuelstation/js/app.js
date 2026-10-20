import * as store from "./store.js";
import * as auth from "./auth.js";
import { html, render, $, $$ } from "./ui.js";
import * as home from "./views/home.js";
import * as daily from "./views/daily.js";
import * as customers from "./views/customers.js";
import * as payments from "./views/payments.js";
import * as setup from "./views/setup.js";
import * as dashboard from "./views/dashboard.js";

const VIEWS = { home, dashboard, daily, customers, payments, setup };
const NAV = [["home", "Home", "🏠"], ["dashboard", "Insights", "📊"], ["daily", "Daily", "📝"], ["customers", "Customers", "👥"], ["payments", "Payments", "💳"], ["setup", "Setup", "⚙️"]];
const app = $("#app");

function boot() {
  if (store.currentUser()) shell(); else authScreen("login");
}

// ---------- sign in / register ----------
function authScreen(mode) {
  const reg = mode === "register";
  render(app, html`
    <div class="auth">
      <div class="auth-card">
        <div class="logo">⛽</div>
        <h1>Fuel Station Manager</h1>
        <p class="muted">${reg ? "Create your station account" : "Sign in to your station"}</p>
        <form id="authForm" novalidate>
          ${reg ? html`
            <label class="field"><span>Station name</span><input name="stationName" required autocomplete="organization"></label>
            <label class="field"><span>Your name</span><input name="name" required autocomplete="name"></label>
            <label class="field"><span>Currency symbol</span><input name="currency" value="₹" required></label>` : ""}
          <label class="field"><span>Username</span><input name="username" required autocomplete="username" autocapitalize="none"></label>
          <label class="field"><span>Password</span><input name="password" type="password" required autocomplete="${reg ? "new-password" : "current-password"}"></label>
          <p class="form-error" hidden></p>
          <button class="btn primary block" type="submit">${reg ? "Create account" : "Sign in"}</button>
        </form>
        <button class="link" id="switch">${reg ? "Already have an account? Sign in" : "New station? Create account"}</button>
      </div>
    </div>`);
  $("#switch").onclick = () => authScreen(reg ? "login" : "register");
  $("#authForm").onsubmit = async (e) => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target));
    const err = $(".form-error", e.target);
    const btn = $("button[type=submit]", e.target);
    try {
      const need = reg ? ["stationName", "name", "username", "password"] : ["username", "password"];
      if (need.some((k) => !String(f[k] || "").trim())) throw new Error("Please fill in all fields.");
      btn.disabled = true;
      await (reg ? auth.register({ ...f, currency: f.currency.trim() }) : auth.login(f.username, f.password));
      location.hash = "";
      shell();
    } catch (ex) { err.textContent = ex.message; err.hidden = false; btn.disabled = false; }
  };
}

// ---------- app shell ----------
function shell() {
  const user = store.currentUser(), station = store.currentStation();
  const allowed = NAV.filter(([k]) => auth.canOpen(user.role, k));
  render(app, html`
    <header class="topbar"><div class="brand">⛽ <span>${station.name}</span></div>
      <button class="user-pill" id="userBtn" aria-label="Account">${user.name.slice(0, 1).toUpperCase()}</button></header>
    <nav class="nav" id="nav">${allowed.map(([k, label, icon]) => html`<a href="#/${k}" data-route="${k}"><i>${icon}</i><span>${label}</span></a>`)}</nav>
    <main class="main"><div id="view"></div></main>`);
  $("#userBtn").onclick = () => { location.hash = auth.canOpen(user.role, "setup") ? "#/setup/station" : "#/daily"; };
  window.onhashchange = route;
  route();
}

function route() {
  const user = store.currentUser();
  if (!user) return boot();
  const [name, param] = location.hash.replace(/^#\/?/, "").split("/");
  const first = auth.canOpen(user.role, "home") ? "home" : "daily";
  const key = VIEWS[name] && auth.canOpen(user.role, name) ? name : first;
  if (key !== name) { location.replace("#/" + key); return; }
  $$("#nav a").forEach((a) => a.classList.toggle("on", a.dataset.route === key));
  const view = $("#view");
  view.className = "view v-" + key;
  view.onclick = view.onchange = view.oninput = null;
  VIEWS[key].mount(view, param);
  window.scrollTo(0, 0);
}

boot();
if ("serviceWorker" in navigator) navigator.serviceWorker.register("service-worker.js").catch(() => {});
