import { currentStation } from "./store.js";

// ---------- safe templating ----------
class Raw { constructor(s) { this.s = s; } }
export const raw = (s) => new Raw(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const val = (v) => (v instanceof Raw ? v.s : Array.isArray(v) ? v.map(val).join("") : esc(v));
export const html = (strs, ...vals) => new Raw(strs.reduce((o, s, i) => o + s + (i < vals.length ? val(vals[i]) : ""), ""));
export const render = (el, tpl) => { el.innerHTML = tpl.s; };
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

// ---------- dates ----------
const pad = (n) => String(n).padStart(2, "0");
export const dateKey = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const todayKey = () => dateKey(new Date());
export const parseKey = (k) => { const [y, m, d] = k.split("-").map(Number); return new Date(y, m - 1, d); };
export const shiftDate = (k, n) => { const d = parseKey(k); d.setDate(d.getDate() + n); return dateKey(d); };
export const fmtDate = (k, opts = { weekday: "short", day: "numeric", month: "short" }) => parseKey(k).toLocaleDateString(undefined, opts);

// ---------- numbers ----------
export const num = (v) => { const n = parseFloat(v); return Number.isFinite(n) ? n : 0; };
export const round2 = (n) => Math.round((n + Number.EPSILON) * 100) / 100;
export function money(n) {
  const cur = currentStation()?.currency || "";
  const v = round2(n || 0);
  return (v < 0 ? "-" : "") + cur + Math.abs(v).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}
export const qty = (n) => round2(n || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });

// ---------- toast ----------
export function toast(msg) {
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.classList.add("show"), 10);
  setTimeout(() => { t.classList.remove("show"); setTimeout(() => t.remove(), 250); }, 2200);
}

// ---------- modal form ----------
// fields: [{name,label,type,options,value,required,placeholder,step,hint,showIf(values),readonly}]
// opts: {title, fields, submitLabel, onSubmit(values), onDelete, onChange(values,set), note}
export function openForm(opts) {
  const overlay = document.createElement("div");
  overlay.className = "overlay";
  const fieldHtml = (f) => {
    const v = f.value ?? "";
    const common = `name="${esc(f.name)}" ${f.required ? "required" : ""} ${f.readonly ? "readonly" : ""}`;
    let input;
    if (f.type === "select") {
      input = html`<select ${raw(common)}>${f.options.map((o) => html`<option value="${o.value}" ${String(o.value) === String(v) ? raw("selected") : ""}>${o.label}</option>`)}</select>`;
    } else if (f.type === "textarea") {
      input = html`<textarea ${raw(common)} rows="2" placeholder="${f.placeholder || ""}">${v}</textarea>`;
    } else {
      const mode = f.type === "number" ? `inputmode="decimal" step="${f.step || "any"}" min="${f.min ?? 0}"` : "";
      input = html`<input type="${f.type || "text"}" ${raw(common)} ${raw(mode)} value="${v}" placeholder="${f.placeholder || ""}" autocomplete="off">`;
    }
    return html`<label class="field" data-field="${f.name}"><span>${f.label}${f.required ? " *" : ""}</span>${input}${f.hint ? html`<small>${f.hint}</small>` : ""}</label>`;
  };
  overlay.innerHTML = html`
    <form class="sheet" novalidate>
      <div class="sheet-head"><h2>${opts.title}</h2><button type="button" class="icon-btn" data-close aria-label="Close">✕</button></div>
      ${opts.note ? html`<p class="muted">${opts.note}</p>` : ""}
      <div class="sheet-body">${opts.fields.map(fieldHtml)}</div>
      <p class="form-error" hidden></p>
      <div class="sheet-foot">
        ${opts.onDelete ? html`<button type="button" class="btn danger" data-delete>Delete</button>` : ""}
        <button type="submit" class="btn primary">${opts.submitLabel || "Save"}</button>
      </div>
    </form>`.s;
  document.body.appendChild(overlay);
  document.body.classList.add("no-scroll");
  const form = $("form", overlay);
  const close = () => { overlay.remove(); if (!$(".overlay")) document.body.classList.remove("no-scroll"); };
  const values = () => {
    const out = {};
    for (const f of opts.fields) {
      const el = form.elements[f.name];
      out[f.name] = f.type === "number" ? (el.value === "" ? null : parseFloat(el.value)) : el.value.trim();
    }
    return out;
  };
  const set = (name, v) => { form.elements[name].value = v ?? ""; };
  const refresh = () => {
    const vals = values();
    for (const f of opts.fields) if (f.showIf) $(`[data-field="${f.name}"]`, form).hidden = !f.showIf(vals);
    return vals;
  };
  refresh();
  form.addEventListener("input", (e) => {
    const vals = refresh();
    opts.onChange?.(vals, set, e.target.name);
    refresh();
  });
  overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) close(); });
  $("[data-close]", form).onclick = close;
  if (opts.onDelete) $("[data-delete]", form).onclick = async () => {
    if (await confirmBox("Delete this entry?", "This cannot be undone.")) { await opts.onDelete(); close(); }
  };
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = $(".form-error", form);
    const vals = values();
    for (const f of opts.fields) {
      const visible = !f.showIf || f.showIf(vals);
      if (visible && f.required && (vals[f.name] === "" || vals[f.name] === null)) {
        err.textContent = `${f.label} is required.`; err.hidden = false; form.elements[f.name].focus(); return;
      }
    }
    try { await opts.onSubmit(vals); close(); }
    catch (ex) { err.textContent = ex.message || "Something went wrong."; err.hidden = false; }
  });
  const first = form.querySelector("input:not([readonly]):not([type=date]), select");
  if (first && !opts.noFocus) setTimeout(() => first.focus(), 50);
  return close;
}

export function confirmBox(title, message, okLabel = "Delete") {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "overlay center";
    overlay.innerHTML = html`<div class="dialog"><h2>${title}</h2><p class="muted">${message}</p>
      <div class="sheet-foot"><button class="btn" data-no>Cancel</button><button class="btn danger" data-yes>${okLabel}</button></div></div>`.s;
    document.body.appendChild(overlay);
    const done = (v) => { overlay.remove(); resolve(v); };
    $("[data-no]", overlay).onclick = () => done(false);
    $("[data-yes]", overlay).onclick = () => done(true);
  });
}

export const opts = (arr, label = "name") => arr.map((x) => ({ value: x.id, label: x[label] }));
