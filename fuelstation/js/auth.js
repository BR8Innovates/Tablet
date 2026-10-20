import * as store from "./store.js";

const enc = new TextEncoder();
const toB64 = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf)));
const fromB64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));

async function hash(password, saltB64) {
  const key = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt: fromB64(saltB64), iterations: 150000, hash: "SHA-256" }, key, 256);
  return toB64(bits);
}
const newSalt = () => toB64(crypto.getRandomValues(new Uint8Array(16)));

export async function credentials(username, password) {
  const salt = newSalt();
  return { username: username.trim().toLowerCase(), salt, hash: await hash(password, salt) };
}

export async function register({ stationName, currency, name, username, password }) {
  if (password.length < 6) throw new Error("Password must be at least 6 characters.");
  if (store.findUserByName(username)) throw new Error("That username is already taken.");
  const owner = store.createStation({ stationName, currency }, { name, ...(await credentials(username, password)) });
  store.startSession(owner);
}

export async function login(username, password) {
  const user = store.findUserByName(username);
  if (!user || user.active === false || (await hash(password, user.salt)) !== user.hash) {
    throw new Error("Wrong username or password.");
  }
  store.startSession(user);
}

export const logout = () => store.endSession();

export async function addTeamMember({ name, username, password, role }) {
  if (password.length < 6) throw new Error("Password must be at least 6 characters.");
  if (store.findUserByName(username)) throw new Error("That username is already taken.");
  store.addUser({ name, role, ...(await credentials(username, password)) });
}

// What each role may open. Enforced in the UI today; mirror these on the server later.
export const ACCESS = {
  owner: ["home", "dashboard", "daily", "customers", "payments", "setup"],
  manager: ["home", "dashboard", "daily", "customers", "payments", "setup"],
  attendant: ["daily", "customers"],
};
export const canOpen = (role, route) => (ACCESS[role] || []).includes(route);
