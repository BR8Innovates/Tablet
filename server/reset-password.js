// Reset a forgotten password (run on the computer that hosts the data):
//   node server/reset-password.js <username> <new-password>
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { DatabaseSync } from "node:sqlite";

const [username, password] = process.argv.slice(2);
if (!username || !password || password.length < 6) {
  console.error("Usage: node server/reset-password.js <username> <new-password (min 6 chars)>");
  process.exit(1);
}
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const db = new DatabaseSync(path.join(path.resolve(process.env.DATA_DIR || path.join(root, "data")), "fuelstation.db"));
const user = db.prepare("SELECT id FROM users WHERE username = ?").get(username.trim().toLowerCase());
if (!user) { console.error("No such user."); process.exit(1); }
const salt = crypto.randomBytes(16).toString("base64");
db.prepare("UPDATE users SET salt = ?, hash = ?, active = 1 WHERE id = ?").run(salt, crypto.scryptSync(password, salt, 64).toString("base64"), user.id);
console.log(`Password updated for ${username}.`);
