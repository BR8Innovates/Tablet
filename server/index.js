// Fuel Station Manager API + static host. Zero dependencies (Node >= 22.5, built-in SQLite).
//   node server/index.js          → http://localhost:3000
// Env: PORT, DATA_DIR (default ./data), SESSION_SECRET (default: generated and kept in DATA_DIR).
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { DatabaseSync } from "node:sqlite";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const WEB = path.join(ROOT, "fuelstation");
const DATA_DIR = path.resolve(process.env.DATA_DIR || path.join(ROOT, "data"));
fs.mkdirSync(DATA_DIR, { recursive: true });

const secretFile = path.join(DATA_DIR, ".secret");
const SECRET = process.env.SESSION_SECRET
  || (fs.existsSync(secretFile) ? fs.readFileSync(secretFile, "utf8") : (() => {
    const s = crypto.randomBytes(32).toString("hex");
    fs.writeFileSync(secretFile, s, { mode: 0o600 });
    return s;
  })());

const db = new DatabaseSync(path.join(DATA_DIR, "fuelstation.db"));
db.exec(`
  PRAGMA journal_mode = WAL;
  CREATE TABLE IF NOT EXISTS stations (id TEXT PRIMARY KEY, name TEXT NOT NULL, currency TEXT NOT NULL, created_at INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY, station_id TEXT NOT NULL REFERENCES stations(id), username TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
    role TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, salt TEXT NOT NULL, hash TEXT NOT NULL, created_at INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS records (
    station_id TEXT NOT NULL, col TEXT NOT NULL, id TEXT NOT NULL, json TEXT NOT NULL,
    PRIMARY KEY (station_id, col, id));
`);
const q = {
  userByName: db.prepare("SELECT * FROM users WHERE username = ?"),
  userById: db.prepare("SELECT * FROM users WHERE id = ?"),
  stationUsers: db.prepare("SELECT * FROM users WHERE station_id = ? ORDER BY created_at"),
  station: db.prepare("SELECT * FROM stations WHERE id = ?"),
  records: db.prepare("SELECT col, json FROM records WHERE station_id = ?"),
  put: db.prepare("INSERT INTO records (station_id, col, id, json) VALUES (?, ?, ?, ?) ON CONFLICT(station_id, col, id) DO UPDATE SET json = excluded.json"),
  del: db.prepare("DELETE FROM records WHERE station_id = ? AND col = ? AND id = ?"),
};

// ---------- rules (the source of truth for roles) ----------
const COLLECTIONS = ["products", "pumps", "nozzles", "prices", "shifts", "readings", "customers", "credits", "payments", "expenses", "expenseTypes", "sources", "closings"];
const ATTENDANT_WRITE = new Set(["readings", "credits", "payments", "expenses", "closings", "customers"]);
const ROLES = ["owner", "manager", "attendant"];
const canWrite = (role, col, op) => role !== "attendant" || (ATTENDANT_WRITE.has(col) && !(op === "delete" && col === "customers"));
const ID_RE = /^[A-Za-z0-9_-]{8,64}$/;

// ---------- crypto ----------
const hashPw = (pw, salt) => crypto.scryptSync(pw, salt, 64).toString("base64");
const sameHash = (a, b) => { const x = Buffer.from(a), y = Buffer.from(b); return x.length === y.length && crypto.timingSafeEqual(x, y); };
const b64u = (b) => Buffer.from(b).toString("base64url");
const sign = (payload) => { const body = b64u(JSON.stringify(payload)); return body + "." + crypto.createHmac("sha256", SECRET).update(body).digest("base64url"); };
function verify(token) {
  const [body, sig] = String(token || "").split(".");
  if (!body || !sig) return null;
  const good = crypto.createHmac("sha256", SECRET).update(body).digest("base64url");
  if (!sameHash(sig, good)) return null;
  const p = JSON.parse(Buffer.from(body, "base64url").toString());
  return p.exp > Date.now() ? p : null;
}
const newToken = (u) => sign({ uid: u.id, exp: Date.now() + 30 * 864e5 });

// ---------- helpers ----------
class HttpError extends Error { constructor(status, message) { super(message); this.status = status; } }
const publicUser = (u) => ({ id: u.id, stationId: u.station_id, username: u.username, name: u.name, role: u.role, active: !!u.active });
const publicStation = (s) => ({ id: s.id, name: s.name, currency: s.currency });

function snapshot(user) {
  const data = Object.fromEntries(COLLECTIONS.map((c) => [c, []]));
  for (const r of q.records.all(user.station_id)) data[r.col]?.push(JSON.parse(r.json));
  const out = { user: publicUser(user), station: publicStation(q.station.get(user.station_id)), data };
  if (user.role === "owner") out.users = q.stationUsers.all(user.station_id).map(publicUser);
  return out;
}

function seed(stationId) {
  const put = (col, o) => { const id = crypto.randomUUID(); q.put.run(stationId, col, id, JSON.stringify({ id, createdAt: Date.now(), ...o })); };
  for (const n of ["Petrol", "Diesel"]) put("products", { name: n, category: "Fuel", unit: "L" });
  [["Morning", "06:00", "14:00"], ["Evening", "14:00", "22:00"], ["Night", "22:00", "06:00"]].forEach(([name, start, end]) => put("shifts", { name, start, end }));
  for (const n of ["Salary", "Electricity", "Maintenance", "Transport", "Tea & Misc"]) put("expenseTypes", { name: n });
  for (const n of ["UPI", "Card", "Bank Transfer", "Fleet Card"]) put("sources", { name: n });
}

// Behind a hosting proxy (Render, Fly, Railway…) set TRUST_PROXY=1 so rate limits use the real client address.
const TRUST_PROXY = process.env.TRUST_PROXY === "1";
const clientIp = (req) => (TRUST_PROXY && String(req.headers["x-forwarded-for"] || "").split(",")[0].trim()) || req.socket.remoteAddress;
const attempts = new Map();
function throttle(key) {
  const now = Date.now(), list = (attempts.get(key) || []).filter((t) => now - t < 15 * 60e3);
  if (list.length >= 10) throw new HttpError(429, "Too many attempts. Try again in a few minutes.");
  list.push(now); attempts.set(key, list);
}
const str = (v, max, label) => {
  if (typeof v !== "string" || !v.trim() || v.length > max) throw new HttpError(400, `${label} is required.`);
  return v.trim();
};
const checkPassword = (pw) => { if (typeof pw !== "string" || pw.length < 6 || pw.length > 200) throw new HttpError(400, "Password must be at least 6 characters."); };

// ---------- realtime (Server-Sent Events) ----------
// Every change is pushed to the other devices signed in to the same station. In-memory, so run a single instance.
const hubs = new Map();                       // stationId -> Set<{ res, client }>
const tickets = new Map();                    // one-time stream tickets (so the session token never sits in a URL)
function broadcast(stationId, event, fromClient) {
  const line = `data: ${JSON.stringify(event)}\n\n`;
  for (const c of hubs.get(stationId) || []) if (c.client !== fromClient) c.res.write(line);
}
setInterval(() => {
  const now = Date.now();
  for (const [t, v] of tickets) if (v.exp < now) tickets.delete(t);
  for (const set of hubs.values()) for (const c of set) c.res.write(": ping\n\n");
}, 25000).unref();

function openStream(req, res, url) {
  const t = tickets.get(url.searchParams.get("ticket"));
  tickets.delete(url.searchParams.get("ticket"));
  const u = t && t.exp > Date.now() && q.userById.get(t.uid);
  if (!u || !u.active) { res.writeHead(401); return res.end(); }
  res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform", Connection: "keep-alive", "X-Accel-Buffering": "no" });
  res.write("retry: 3000\n\n");
  const conn = { res, client: url.searchParams.get("client") || "" };
  if (!hubs.has(u.station_id)) hubs.set(u.station_id, new Set());
  hubs.get(u.station_id).add(conn);
  req.on("close", () => hubs.get(u.station_id)?.delete(conn));
}

// ---------- routes ----------
const routes = [];
const route = (method, pattern, handler) => routes.push({ method, re: new RegExp("^" + pattern.replace(/:(\w+)/g, "(?<$1>[^/]+)") + "$"), handler });

route("GET", "/api/health", () => ({ ok: true }));

route("POST", "/api/register", ({ body, ip }) => {
  throttle("reg:" + ip);
  const username = str(body.username, 60, "Username").toLowerCase();
  checkPassword(body.password);
  if (q.userByName.get(username)) throw new HttpError(409, "That username is already taken.");
  const station = { id: crypto.randomUUID(), name: str(body.stationName, 120, "Station name"), currency: str(body.currency || "₹", 8, "Currency") };
  const salt = crypto.randomBytes(16).toString("base64");
  const user = { id: crypto.randomUUID(), name: str(body.name, 120, "Name") };
  db.exec("BEGIN");
  try {
    db.prepare("INSERT INTO stations VALUES (?, ?, ?, ?)").run(station.id, station.name, station.currency, Date.now());
    db.prepare("INSERT INTO users VALUES (?, ?, ?, ?, 'owner', 1, ?, ?, ?)").run(user.id, station.id, username, user.name, salt, hashPw(body.password, salt), Date.now());
    seed(station.id);
    db.exec("COMMIT");
  } catch (e) { db.exec("ROLLBACK"); throw e; }
  const u = q.userById.get(user.id);
  return { token: newToken(u), ...snapshot(u) };
});

route("POST", "/api/login", ({ body, ip }) => {
  const username = String(body.username || "").trim().toLowerCase();
  throttle(`login:${ip}:${username}`);
  const u = q.userByName.get(username);
  if (!u || !u.active || !sameHash(hashPw(String(body.password || ""), u.salt), u.hash)) throw new HttpError(401, "Wrong username or password.");
  attempts.delete(`login:${ip}:${username}`);
  return { token: newToken(u), ...snapshot(u) };
});

route("GET", "/api/me", ({ user }) => snapshot(user));

route("POST", "/api/stream-ticket", ({ user }) => {
  const ticket = crypto.randomBytes(18).toString("base64url");
  tickets.set(ticket, { uid: user.id, exp: Date.now() + 60000 });
  return { ticket };
});

route("PUT", "/api/c/:col/:id", ({ user, params, body, client }) => {
  if (!COLLECTIONS.includes(params.col)) throw new HttpError(404, "Unknown collection.");
  if (!ID_RE.test(params.id)) throw new HttpError(400, "Bad id.");
  if (!canWrite(user.role, params.col, "put")) throw new HttpError(403, "Your role can't change this.");
  if (!body || typeof body !== "object" || Array.isArray(body)) throw new HttpError(400, "Bad record.");
  const json = JSON.stringify({ ...body, id: params.id });
  if (json.length > 20000) throw new HttpError(413, "Record too large.");
  q.put.run(user.station_id, params.col, params.id, json);
  broadcast(user.station_id, { t: "put", col: params.col, rec: JSON.parse(json) }, client);
  return { ok: true };
});

route("DELETE", "/api/c/:col/:id", ({ user, params, client }) => {
  if (!COLLECTIONS.includes(params.col)) throw new HttpError(404, "Unknown collection.");
  if (!canWrite(user.role, params.col, "delete")) throw new HttpError(403, "Your role can't change this.");
  q.del.run(user.station_id, params.col, params.id);
  broadcast(user.station_id, { t: "del", col: params.col, id: params.id }, client);
  return { ok: true };
});

route("PATCH", "/api/station", ({ user, body, client }) => {
  if (user.role === "attendant") throw new HttpError(403, "Your role can't change this.");
  db.prepare("UPDATE stations SET name = ?, currency = ? WHERE id = ?").run(str(body.name, 120, "Station name"), str(body.currency, 8, "Currency"), user.station_id);
  const station = publicStation(q.station.get(user.station_id));
  broadcast(user.station_id, { t: "station", station }, client);
  return { station };
});

const ownerOnly = (user) => { if (user.role !== "owner") throw new HttpError(403, "Only the owner can manage the team."); };
route("POST", "/api/users", ({ user, body, client }) => {
  ownerOnly(user);
  const username = str(body.username, 60, "Username").toLowerCase();
  checkPassword(body.password);
  if (!ROLES.includes(body.role)) throw new HttpError(400, "Bad role.");
  if (q.userByName.get(username)) throw new HttpError(409, "That username is already taken.");
  const salt = crypto.randomBytes(16).toString("base64");
  db.prepare("INSERT INTO users VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)").run(crypto.randomUUID(), user.station_id, username, str(body.name, 120, "Name"), body.role, salt, hashPw(body.password, salt), Date.now());
  broadcast(user.station_id, { t: "users" }, client);
  return { users: q.stationUsers.all(user.station_id).map(publicUser) };
});

route("PATCH", "/api/users/:id", ({ user, params, body, client }) => {
  ownerOnly(user);
  const t = q.userById.get(params.id);
  if (!t || t.station_id !== user.station_id) throw new HttpError(404, "No such user.");
  const role = body.role ?? t.role, active = body.active === undefined ? !!t.active : !!body.active;
  if (!ROLES.includes(role)) throw new HttpError(400, "Bad role.");
  if (t.id === user.id && (role !== "owner" || !active)) throw new HttpError(400, "You can't remove your own owner access.");
  db.prepare("UPDATE users SET name = ?, role = ?, active = ? WHERE id = ?").run(body.name ? str(body.name, 120, "Name") : t.name, role, active ? 1 : 0, t.id);
  if (body.password) {
    checkPassword(body.password);
    const salt = crypto.randomBytes(16).toString("base64");
    db.prepare("UPDATE users SET salt = ?, hash = ? WHERE id = ?").run(salt, hashPw(body.password, salt), t.id);
  }
  broadcast(user.station_id, { t: "users" }, client);
  return { users: q.stationUsers.all(user.station_id).map(publicUser) };
});

// ---------- http ----------
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json", ".webmanifest": "application/manifest+json", ".png": "image/png", ".svg": "image/svg+xml", ".ico": "image/x-icon" };

function serveStatic(req, res) {
  let rel = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (rel.endsWith("/")) rel += "index.html";
  const file = path.join(WEB, rel);
  if (!file.startsWith(WEB + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end("Not found"); }
  const ext = path.extname(file);
  res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream", "Cache-Control": ext === ".html" || file.endsWith("service-worker.js") ? "no-cache" : "public, max-age=300" });
  fs.createReadStream(file).pipe(res);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0; const chunks = [];
    req.on("data", (c) => { size += c.length; if (size > 1e6) { reject(new HttpError(413, "Body too large.")); req.destroy(); } else chunks.push(c); });
    req.on("end", () => { try { resolve(chunks.length ? JSON.parse(Buffer.concat(chunks)) : {}); } catch { reject(new HttpError(400, "Invalid JSON.")); } });
    req.on("error", reject);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://x");
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("Referrer-Policy", "same-origin");
  if (TRUST_PROXY) res.setHeader("Strict-Transport-Security", "max-age=15552000");
  if (url.pathname === "/api/stream") return openStream(req, res, url);
  if (!url.pathname.startsWith("/api/")) return serveStatic(req, res);
  const send = (status, obj) => { res.writeHead(status, { "Content-Type": "application/json", "Cache-Control": "no-store" }); res.end(JSON.stringify(obj)); };
  try {
    const hit = routes.map((r) => ({ r, m: r.method === req.method && url.pathname.match(r.re) })).find((x) => x.m);
    if (!hit) throw new HttpError(404, "Not found.");
    const ctx = { params: hit.m.groups || {}, ip: clientIp(req), client: String(req.headers["x-client-id"] || ""), body: req.method === "GET" || req.method === "DELETE" ? {} : await readBody(req) };
    if (!["/api/health", "/api/register", "/api/login"].includes(url.pathname)) {
      const p = verify((req.headers.authorization || "").replace(/^Bearer /, ""));
      const u = p && q.userById.get(p.uid);
      if (!u || !u.active) throw new HttpError(401, "Please sign in again.");
      ctx.user = u;
    }
    send(200, await hit.r.handler(ctx));
  } catch (e) {
    if (!(e instanceof HttpError)) console.error(e);
    send(e.status || 500, { error: e.status ? e.message : "Server error." });
  }
});

// ---------- automatic backups ----------
// A consistent copy of the database at start-up and then daily, keeping the newest 14 in data/backups.
function backup() {
  try {
    const dir = path.join(DATA_DIR, "backups");
    fs.mkdirSync(dir, { recursive: true });
    const file = path.join(dir, `fuelstation-${new Date().toISOString().slice(0, 10)}.db`);
    if (!fs.existsSync(file)) db.exec(`VACUUM INTO '${file.replace(/'/g, "''")}'`);
    fs.readdirSync(dir).filter((f) => /^fuelstation-.*\.db$/.test(f)).sort().slice(0, -14).forEach((f) => fs.unlinkSync(path.join(dir, f)));
  } catch (e) { console.error("Backup failed:", e.message); }
}
backup();
setInterval(backup, 6 * 3600e3).unref();

const PORT = Number(process.env.PORT || 3000);
server.listen(PORT, process.env.HOST || "0.0.0.0", () => console.log(`Fuel Station Manager on http://localhost:${PORT}`));
