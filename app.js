(() => {
  "use strict";

  const STORAGE_KEY = "vitals:v1";
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // ---------- Date helpers ----------
  const pad2 = (n) => String(n).padStart(2, "0");
  const dateKey = (d) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
  const todayKey = () => dateKey(new Date());
  const addDays = (d, n) => { const c = new Date(d); c.setDate(c.getDate() + n); return c; };
  const lastNDayKeys = (n) => {
    const out = [];
    const now = new Date();
    for (let i = n - 1; i >= 0; i--) out.push(dateKey(addDays(now, -i)));
    return out;
  };
  const weekdayShort = (key) => {
    const [y, m, d] = key.split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: "short" });
  };
  const fmtDateShort = (key) => {
    const [y, m, d] = key.split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  };
  const fmtTime = (iso) => new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });

  // ---------- Default state ----------
  function defaultState() {
    return {
      profile: { name: "", height: null },
      goals: { steps: 8000, water: 2000, active: 30, sleep: 8, weightUnit: "kg" },
      days: {},           // key -> { steps, water, active }
      activities: [],      // { id, ts, type, duration, steps, calories, notes }
      sleep: [],           // { id, ts, bedtime, waketime, hours, quality, notes }
      body: [],            // { id, ts, weight, bodyfat, hr, notes }
      theme: null,
    };
  }

  let state = loadState();

  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultState();
      const parsed = JSON.parse(raw);
      const base = defaultState();
      return {
        ...base,
        ...parsed,
        profile: { ...base.profile, ...(parsed.profile || {}) },
        goals: { ...base.goals, ...(parsed.goals || {}) },
        days: parsed.days || {},
        activities: parsed.activities || [],
        sleep: parsed.sleep || [],
        body: parsed.body || [],
      };
    } catch (e) {
      console.warn("Failed to load state, resetting.", e);
      return defaultState();
    }
  }

  function saveState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function getDay(key) {
    if (!state.days[key]) state.days[key] = { steps: 0, water: 0, active: 0 };
    return state.days[key];
  }

  function uid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  // ---------- Toast ----------
  let toastTimer = null;
  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("show"), 1800);
  }

  // ---------- Theme ----------
  function applyTheme() {
    const root = document.documentElement;
    if (state.theme === "dark" || state.theme === "light") {
      root.setAttribute("data-theme", state.theme);
    } else {
      root.removeAttribute("data-theme");
    }
    const prefersDark = state.theme
      ? state.theme === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    $("#themeToggle").textContent = prefersDark ? "☀️" : "🌙";
  }
  $("#themeToggle").addEventListener("click", () => {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const current = state.theme || (prefersDark ? "dark" : "light");
    state.theme = current === "dark" ? "light" : "dark";
    saveState();
    applyTheme();
  });

  // ---------- Tabs ----------
  function showView(name) {
    $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
    $$(".tab").forEach((t) => {
      const active = t.dataset.view === name;
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", String(active));
    });
    renderAll();
  }
  $("#tabbar").addEventListener("click", (e) => {
    const btn = e.target.closest(".tab");
    if (!btn) return;
    showView(btn.dataset.view);
  });

  // ---------- Canvas ring gauge ----------
  function drawRing(canvas, value, goal, color) {
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const size = canvas.width; // assume square, css controls display size via width/height attrs
    const cssSize = canvas.clientWidth || size;
    if (canvas.width !== cssSize * dpr) {
      canvas.width = cssSize * dpr;
      canvas.height = cssSize * dpr;
    }
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const cx = w / 2, cy = h / 2;
    const r = w / 2 - w * 0.09;
    const lineWidth = w * 0.09;
    const pct = goal > 0 ? Math.max(0, Math.min(1, value / goal)) : 0;

    const trackColor = getComputedStyle(document.documentElement).getPropertyValue("--ring-track").trim() || "#e6e9f2";

    ctx.lineCap = "round";
    ctx.lineWidth = lineWidth;

    ctx.beginPath();
    ctx.strokeStyle = trackColor;
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();

    ctx.beginPath();
    ctx.strokeStyle = color;
    const start = -Math.PI / 2;
    ctx.arc(cx, cy, r, start, start + Math.PI * 2 * pct);
    ctx.stroke();
  }

  // ---------- Canvas bar chart ----------
  function drawBarChart(canvas, labels, values, color, opts = {}) {
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const cssW = canvas.clientWidth || 300;
    const cssH = canvas.clientHeight || parseInt(canvas.getAttribute("height") || "180", 10);
    canvas.width = cssW * dpr;
    canvas.height = cssH * dpr;
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const max = Math.max(1, ...values, opts.goal || 0);
    const padL = 8 * dpr, padR = 8 * dpr, padT = 10 * dpr, padB = 22 * dpr;
    const plotW = w - padL - padR, plotH = h - padT - padB;
    const n = values.length;
    const gap = plotW * 0.08 / n;
    const barW = (plotW - gap * (n - 1)) / n;

    const mutedColor = getComputedStyle(document.documentElement).getPropertyValue("--muted").trim() || "#888";

    if (opts.goal) {
      const gy = padT + plotH - (opts.goal / max) * plotH;
      ctx.beginPath();
      ctx.strokeStyle = mutedColor;
      ctx.globalAlpha = 0.5;
      ctx.setLineDash([4 * dpr, 4 * dpr]);
      ctx.moveTo(padL, gy);
      ctx.lineTo(w - padR, gy);
      ctx.lineWidth = 1 * dpr;
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    }

    values.forEach((v, i) => {
      const bh = max > 0 ? (v / max) * plotH : 0;
      const x = padL + i * (barW + gap);
      const y = padT + plotH - bh;
      ctx.fillStyle = color;
      const radius = Math.min(6 * dpr, barW / 2);
      roundRect(ctx, x, y, barW, Math.max(bh, 2 * dpr), radius);
      ctx.fill();

      ctx.fillStyle = mutedColor;
      ctx.font = `${10 * dpr}px sans-serif`;
      ctx.textAlign = "center";
      ctx.fillText(labels[i], x + barW / 2, h - 6 * dpr);
    });
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  // ---------- Canvas line chart ----------
  function drawLineChart(canvas, labels, values, color) {
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const cssW = canvas.clientWidth || 300;
    const cssH = canvas.clientHeight || parseInt(canvas.getAttribute("height") || "180", 10);
    canvas.width = cssW * dpr;
    canvas.height = cssH * dpr;
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const pts = values.map((v, i) => (v == null ? null : { i, v })).filter(Boolean);
    const mutedColor = getComputedStyle(document.documentElement).getPropertyValue("--muted").trim() || "#888";

    if (pts.length === 0) {
      ctx.fillStyle = mutedColor;
      ctx.font = `${12 * dpr}px sans-serif`;
      ctx.textAlign = "center";
      ctx.fillText("No data yet", w / 2, h / 2);
      return;
    }

    const vals = pts.map((p) => p.v);
    const min = Math.min(...vals), max = Math.max(...vals);
    const range = max - min || 1;
    const padL = 10 * dpr, padR = 10 * dpr, padT = 14 * dpr, padB = 22 * dpr;
    const plotW = w - padL - padR, plotH = h - padT - padB;
    const n = values.length;

    const xAt = (i) => padL + (n > 1 ? (i / (n - 1)) * plotW : plotW / 2);
    const yAt = (v) => padT + plotH - ((v - min) / range) * plotH;

    ctx.beginPath();
    pts.forEach((p, idx) => {
      const x = xAt(p.i), y = yAt(p.v);
      if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5 * dpr;
    ctx.lineJoin = "round";
    ctx.stroke();

    pts.forEach((p) => {
      const x = xAt(p.i), y = yAt(p.v);
      ctx.beginPath();
      ctx.fillStyle = color;
      ctx.arc(x, y, 3 * dpr, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.fillStyle = mutedColor;
    ctx.font = `${10 * dpr}px sans-serif`;
    ctx.textAlign = "center";
    const step = Math.max(1, Math.floor(n / 6));
    labels.forEach((l, i) => {
      if (i % step === 0 || i === n - 1) ctx.fillText(l, xAt(i), h - 6 * dpr);
    });
  }

  // ---------- Insights / analysis engine (runs on demand) ----------
  function sum(arr) { return arr.reduce((a, b) => a + b, 0); }
  function avg(arr) { return arr.length ? sum(arr) / arr.length : 0; }
  function pctChange(curr, prev) {
    if (prev <= 0) return curr > 0 ? 100 : 0;
    return ((curr - prev) / prev) * 100;
  }

  function generateInsights() {
    const insights = [];
    const thisWeekKeys = lastNDayKeys(7);
    const prevWeekKeys = lastNDayKeys(14).slice(0, 7);

    const thisWeekSteps = sum(thisWeekKeys.map((k) => (state.days[k] ? state.days[k].steps : 0)));
    const prevWeekSteps = sum(prevWeekKeys.map((k) => (state.days[k] ? state.days[k].steps : 0)));
    const stepsChange = pctChange(thisWeekSteps, prevWeekSteps);
    insights.push({
      icon: "👣",
      html: `Weekly steps: <b>${thisWeekSteps.toLocaleString()}</b> — ${trendPhrase(stepsChange)} vs. the previous 7 days.`,
    });

    const thisWeekWater = sum(thisWeekKeys.map((k) => (state.days[k] ? state.days[k].water : 0)));
    const prevWeekWater = sum(prevWeekKeys.map((k) => (state.days[k] ? state.days[k].water : 0)));
    const waterChange = pctChange(thisWeekWater, prevWeekWater);
    insights.push({
      icon: "💧",
      html: `Weekly water intake: <b>${thisWeekWater.toLocaleString()} ml</b> — ${trendPhrase(waterChange)} vs. last week.`,
    });

    const thisWeekActive = sum(thisWeekKeys.map((k) => (state.days[k] ? state.days[k].active : 0)));
    const prevWeekActive = sum(prevWeekKeys.map((k) => (state.days[k] ? state.days[k].active : 0)));
    const activeChange = pctChange(thisWeekActive, prevWeekActive);
    insights.push({
      icon: "⏱️",
      html: `Active minutes this week: <b>${thisWeekActive}</b> — ${trendPhrase(activeChange)} vs. last week.`,
    });

    const recentSleep = state.sleep.filter((s) => Date.now() - s.ts <= 7 * 24 * 3600 * 1000);
    if (recentSleep.length) {
      const avgHours = avg(recentSleep.map((s) => s.hours));
      const avgQuality = avg(recentSleep.map((s) => s.quality));
      insights.push({
        icon: "🌙",
        html: `Average sleep this week: <b>${avgHours.toFixed(1)}h</b>, quality ${avgQuality.toFixed(1)}/5 across ${recentSleep.length} night${recentSleep.length === 1 ? "" : "s"}.`,
      });

      // correlation: steps on nights with >=7h sleep vs <7h sleep (using next-day totals)
      const wellRested = [];
      const underSlept = [];
      recentSleep.forEach((s) => {
        const nightKey = dateKey(new Date(s.ts));
        const nextDay = addDays(new Date(s.ts), 1);
        const nextKey = dateKey(nextDay);
        const stepsThatDay = state.days[nightKey] ? state.days[nightKey].steps : (state.days[nextKey] ? state.days[nextKey].steps : 0);
        if (s.hours >= 7) wellRested.push(stepsThatDay);
        else underSlept.push(stepsThatDay);
      });
      if (wellRested.length && underSlept.length) {
        const wAvg = avg(wellRested), uAvg = avg(underSlept);
        const diff = wAvg - uAvg;
        insights.push({
          icon: "🔗",
          html: diff >= 0
            ? `On nights with 7h+ sleep you averaged <b>${Math.round(wAvg)}</b> steps vs <b>${Math.round(uAvg)}</b> on shorter nights — sleep looks like it's paying off.`
            : `Steps were similar regardless of sleep length recently (7h+: ${Math.round(wAvg)}, under 7h: ${Math.round(uAvg)}).`,
        });
      }
    } else {
      insights.push({ icon: "🌙", html: `No sleep entries in the last 7 days — log a night's sleep to unlock sleep insights.` });
    }

    const bestDay = thisWeekKeys
      .map((k) => ({ k, steps: state.days[k] ? state.days[k].steps : 0 }))
      .sort((a, b) => b.steps - a.steps)[0];
    if (bestDay && bestDay.steps > 0) {
      insights.push({ icon: "🏆", html: `Best day this week: <b>${weekdayShort(bestDay.k)}</b> with ${bestDay.steps.toLocaleString()} steps.` });
    }

    const g = state.goals;
    const stepsGoalDays = thisWeekKeys.filter((k) => state.days[k] && state.days[k].steps >= g.steps).length;
    insights.push({
      icon: "🎯",
      html: `You hit your step goal on <b>${stepsGoalDays}/7</b> days this week.`,
    });

    const weightSeries = last30(state.body).filter((b) => b.weight != null);
    if (weightSeries.length >= 2) {
      const first = weightSeries[0].weight;
      const lastW = weightSeries[weightSeries.length - 1].weight;
      const delta = lastW - first;
      const unit = g.weightUnit;
      insights.push({
        icon: "⚖️",
        html: `Weight ${delta === 0 ? "held steady" : delta < 0 ? `dropped ${Math.abs(delta).toFixed(1)} ${unit}` : `rose ${delta.toFixed(1)} ${unit}`} over the last ${weightSeries.length} logged entries (30 days).`,
      });
    }

    return insights;
  }

  function trendPhrase(changePct) {
    const rounded = Math.round(Math.abs(changePct));
    if (Math.abs(changePct) < 3) return `about the same`;
    return changePct > 0
      ? `<span class="insight-up">up ${rounded}%</span>`
      : `<span class="insight-down">down ${rounded}%</span>`;
  }

  $("#btnInsights").addEventListener("click", () => {
    const insights = generateInsights();
    const body = $("#insightsBody");
    if (!insights.length) {
      body.innerHTML = `<p class="muted">Not enough data yet — log a few days of activity, water, and sleep to see insights.</p>`;
      return;
    }
    body.innerHTML = insights
      .map((i) => `<div class="insight-item"><span class="ii-icon">${i.icon}</span><span>${i.html}</span></div>`)
      .join("");
    toast("Insights updated");
  });

  // ---------- Rendering: Dashboard ----------
  function renderDashboard() {
    const key = todayKey();
    const day = getDay(key);
    const g = state.goals;

    $("#ringStepsValue").textContent = day.steps;
    $("#ringStepsGoal").textContent = g.steps;
    $("#ringWaterValue").textContent = day.water;
    $("#ringWaterGoal").textContent = g.water;
    $("#ringActiveValue").textContent = day.active;
    $("#ringActiveGoal").textContent = g.active;

    const sleepToday = latestSleepHoursForNight(key);
    $("#ringSleepValue").textContent = sleepToday != null ? sleepToday.toFixed(1) : "0";
    $("#ringSleepGoal").textContent = g.sleep;

    drawRing($("#ringSteps"), day.steps, g.steps, "#2563eb");
    drawRing($("#ringWater"), day.water, g.water, "#0ea5e9");
    drawRing($("#ringActive"), day.active, g.active, "#f59e0b");
    drawRing($("#ringSleep"), sleepToday || 0, g.sleep, "#8b5cf6");

    const keys = lastNDayKeys(7);
    drawBarChart(
      $("#chartStepsWeek"),
      keys.map(weekdayShort),
      keys.map((k) => (state.days[k] ? state.days[k].steps : 0)),
      "#2563eb",
      { goal: g.steps }
    );

    const weightSeries = last30(state.body).filter((b) => b.weight != null);
    drawLineChart(
      $("#chartWeightTrend"),
      weightSeries.map((b) => fmtDateShort(dateKey(new Date(b.ts)))),
      weightSeries.map((b) => b.weight),
      "#10b981"
    );

    renderStreaks();
  }

  function latestSleepHoursForNight(key) {
    const entry = state.sleep.find((s) => dateKey(new Date(s.ts)) === key);
    return entry ? entry.hours : null;
  }

  function last30(arr) {
    const cutoff = Date.now() - 30 * 24 * 3600 * 1000;
    return arr.filter((e) => e.ts >= cutoff).sort((a, b) => a.ts - b.ts);
  }

  function renderStreaks() {
    const keys = lastNDayKeys(60).reverse(); // most recent first
    const g = state.goals;

    function streakFor(pred) {
      let count = 0;
      for (const k of keys) {
        const day = state.days[k];
        if (day && pred(day)) count++;
        else break;
      }
      return count;
    }

    const stepStreak = streakFor((d) => d.steps >= g.steps);
    const waterStreak = streakFor((d) => d.water >= g.water);
    const activeStreak = streakFor((d) => d.active >= g.active);

    const items = [
      { emoji: "👣", count: stepStreak, label: "Step goal" },
      { emoji: "💧", count: waterStreak, label: "Water goal" },
      { emoji: "⏱️", count: activeStreak, label: "Active goal" },
    ];

    $("#streaksRow").innerHTML = items
      .map(
        (it) => `
      <div class="streak-item">
        <div class="streak-emoji">${it.emoji}</div>
        <div class="streak-count">${it.count}d</div>
        <div class="streak-label">${it.label}</div>
      </div>`
      )
      .join("");
  }

  // ---------- Activity ----------
  const ACTIVITY_ICON = { Walk: "🚶", Run: "🏃", Cycle: "🚴", Strength: "🏋️", Yoga: "🧘", Sport: "⚽", Other: "✨" };
  const MET = { Walk: 3.5, Run: 9.8, Cycle: 7.5, Strength: 5, Yoga: 2.5, Sport: 7, Other: 4 };

  function estimateCalories(type, minutes) {
    const weight = latestWeightKg() || 70;
    const met = MET[type] || 4;
    return Math.round(met * 3.5 * weight / 200 * minutes);
  }

  function latestWeightKg() {
    const withWeight = state.body.filter((b) => b.weight != null).sort((a, b) => b.ts - a.ts);
    if (!withWeight.length) return null;
    const last = withWeight[0];
    return state.goals.weightUnit === "lb" ? last.weight * 0.453592 : last.weight;
  }

  $("#formActivity").addEventListener("submit", (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const type = fd.get("type");
    const duration = Number(fd.get("duration"));
    const steps = Number(fd.get("steps")) || 0;
    let calories = Number(fd.get("calories")) || 0;
    if (!calories) calories = estimateCalories(type, duration);

    const entry = {
      id: uid(),
      ts: Date.now(),
      type,
      duration,
      steps,
      calories,
      notes: (fd.get("notes") || "").toString().slice(0, 140),
    };
    state.activities.unshift(entry);

    const key = todayKey();
    const day = getDay(key);
    day.active += duration;
    if (steps) day.steps += steps;

    saveState();
    e.target.reset();
    toast("Activity logged");
    renderAll();
  });

  function renderActivity() {
    const keys = lastNDayKeys(7);
    drawBarChart(
      $("#chartActivityWeek"),
      keys.map(weekdayShort),
      keys.map((k) => (state.days[k] ? state.days[k].steps : 0)),
      "#2563eb",
      { goal: state.goals.steps }
    );

    const byType = {};
    last30(state.activities).forEach((a) => {
      byType[a.type] = (byType[a.type] || 0) + a.duration;
    });
    const typeLabels = Object.keys(byType);
    drawBarChart(
      $("#chartActivityType"),
      typeLabels.length ? typeLabels : ["—"],
      typeLabels.length ? typeLabels.map((t) => byType[t]) : [0],
      "#f59e0b"
    );

    const list = $("#listActivity");
    if (!state.activities.length) {
      list.innerHTML = `<div class="empty-state">No activities logged yet. Add one above!</div>`;
      return;
    }
    list.innerHTML = state.activities
      .slice(0, 25)
      .map(
        (a) => `
      <div class="list-item" data-id="${a.id}" data-kind="activities">
        <div class="li-icon">${ACTIVITY_ICON[a.type] || "✨"}</div>
        <div class="li-main">
          <div class="li-title">${a.type} — ${a.duration} min</div>
          <div class="li-sub">${a.steps ? a.steps + " steps · " : ""}${a.calories} kcal${a.notes ? " · " + escapeHtml(a.notes) : ""}</div>
        </div>
        <div class="li-meta">${fmtTime(a.ts)}<br>${fmtDateShort(dateKey(new Date(a.ts)))}</div>
        <button class="li-del" data-del data-id="${a.id}" data-kind="activities" aria-label="Delete">✕</button>
      </div>`
      )
      .join("");
  }

  // ---------- Water ----------
  function addWater(amount) {
    const day = getDay(todayKey());
    day.water = Math.max(0, day.water + amount);
    saveState();
    toast(`+${amount} ml water`);
    renderAll();
  }

  function undoLastWater() {
    // simplest reliable undo: remove 250ml or the whole day's remainder, whichever smaller
    const day = getDay(todayKey());
    if (day.water <= 0) { toast("Nothing to undo"); return; }
    day.water = Math.max(0, day.water - 250);
    saveState();
    toast("Last water removed");
    renderAll();
  }

  function renderWater() {
    const day = getDay(todayKey());
    const g = state.goals;
    $("#ringWaterBigValue").textContent = day.water;
    $("#ringWaterBigGoal").textContent = g.water;
    drawRing($("#ringWaterBig"), day.water, g.water, "#0ea5e9");

    const keys = lastNDayKeys(7);
    drawBarChart(
      $("#chartWaterWeek"),
      keys.map(weekdayShort),
      keys.map((k) => (state.days[k] ? state.days[k].water : 0)),
      "#0ea5e9",
      { goal: g.water }
    );
  }

  // ---------- Sleep ----------
  function timeToMinutes(t) {
    const [h, m] = t.split(":").map(Number);
    return h * 60 + m;
  }

  $("#formSleep").addEventListener("submit", (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const bedtime = fd.get("bedtime");
    const waketime = fd.get("waketime");
    let bed = timeToMinutes(bedtime);
    let wake = timeToMinutes(waketime);
    if (wake <= bed) wake += 24 * 60;
    const hours = (wake - bed) / 60;

    const entry = {
      id: uid(),
      ts: Date.now(),
      bedtime,
      waketime,
      hours: Math.round(hours * 100) / 100,
      quality: Number(fd.get("quality")),
      notes: (fd.get("notes") || "").toString().slice(0, 140),
    };
    state.sleep.unshift(entry);
    saveState();
    e.target.reset();
    toast("Sleep logged");
    renderAll();
  });

  const QUALITY_EMOJI = { 5: "😴", 4: "🙂", 3: "😐", 2: "😕", 1: "😩" };

  function renderSleep() {
    const keys = lastNDayKeys(7);
    const hoursByKey = keys.map((k) => {
      const entry = state.sleep.find((s) => dateKey(new Date(s.ts)) === k);
      return entry ? entry.hours : 0;
    });
    drawBarChart($("#chartSleepWeek"), keys.map(weekdayShort), hoursByKey, "#8b5cf6", { goal: state.goals.sleep });

    const list = $("#listSleep");
    if (!state.sleep.length) {
      list.innerHTML = `<div class="empty-state">No sleep entries yet.</div>`;
      return;
    }
    list.innerHTML = state.sleep
      .slice(0, 25)
      .map(
        (s) => `
      <div class="list-item" data-id="${s.id}" data-kind="sleep">
        <div class="li-icon">${QUALITY_EMOJI[s.quality] || "😐"}</div>
        <div class="li-main">
          <div class="li-title">${s.hours}h — ${s.bedtime} → ${s.waketime}</div>
          <div class="li-sub">${s.notes ? escapeHtml(s.notes) : "No notes"}</div>
        </div>
        <div class="li-meta">${fmtDateShort(dateKey(new Date(s.ts)))}</div>
        <button class="li-del" data-del data-id="${s.id}" data-kind="sleep" aria-label="Delete">✕</button>
      </div>`
      )
      .join("");
  }

  // ---------- Body ----------
  $("#formBody").addEventListener("submit", (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const weight = fd.get("weight") ? Number(fd.get("weight")) : null;
    const bodyfat = fd.get("bodyfat") ? Number(fd.get("bodyfat")) : null;
    const hr = fd.get("hr") ? Number(fd.get("hr")) : null;
    if (weight == null && bodyfat == null && hr == null) {
      toast("Enter at least one measurement");
      return;
    }
    const entry = {
      id: uid(),
      ts: Date.now(),
      weight,
      bodyfat,
      hr,
      notes: (fd.get("notes") || "").toString().slice(0, 140),
    };
    state.body.unshift(entry);
    saveState();
    e.target.reset();
    toast("Entry added");
    renderAll();
  });

  function renderBody() {
    const unit = state.goals.weightUnit;
    $("#weightUnitLabel").textContent = unit;
    $$(".unitLabelInline").forEach((el) => (el.textContent = unit));

    const series = last30(state.body).filter((b) => b.weight != null);
    drawLineChart(
      $("#chartBodyWeight"),
      series.map((b) => fmtDateShort(dateKey(new Date(b.ts)))),
      series.map((b) => b.weight),
      "#10b981"
    );

    const list = $("#listBody");
    if (!state.body.length) {
      list.innerHTML = `<div class="empty-state">No body measurements logged yet.</div>`;
      return;
    }
    list.innerHTML = state.body
      .slice(0, 25)
      .map((b) => {
        const parts = [];
        if (b.weight != null) parts.push(`${b.weight} ${unit}`);
        if (b.bodyfat != null) parts.push(`${b.bodyfat}% fat`);
        if (b.hr != null) parts.push(`${b.hr} bpm`);
        return `
      <div class="list-item" data-id="${b.id}" data-kind="body">
        <div class="li-icon">⚖️</div>
        <div class="li-main">
          <div class="li-title">${parts.join(" · ") || "Entry"}</div>
          <div class="li-sub">${b.notes ? escapeHtml(b.notes) : "No notes"}</div>
        </div>
        <div class="li-meta">${fmtDateShort(dateKey(new Date(b.ts)))}</div>
        <button class="li-del" data-del data-id="${b.id}" data-kind="body" aria-label="Delete">✕</button>
      </div>`;
      })
      .join("");
  }

  // ---------- Delete handling (event delegation) ----------
  $("#content").addEventListener("click", (e) => {
    const del = e.target.closest("[data-del]");
    if (!del) return;
    const { id, kind } = del.dataset;
    const arr = state[kind];
    const idx = arr.findIndex((x) => x.id === id);
    if (idx === -1) return;
    const [removed] = arr.splice(idx, 1);
    if (kind === "activities") {
      const key = dateKey(new Date(removed.ts));
      const day = state.days[key];
      if (day) {
        day.active = Math.max(0, day.active - removed.duration);
        if (removed.steps) day.steps = Math.max(0, day.steps - removed.steps);
      }
    }
    saveState();
    toast("Deleted");
    renderAll();
  });

  // ---------- Quick actions ----------
  document.addEventListener("click", (e) => {
    const qa = e.target.closest(".qa-btn[data-qa]");
    if (!qa) return;
    const kind = qa.dataset.qa;
    const amount = Number(qa.dataset.amount) || 0;
    if (kind === "steps") {
      getDay(todayKey()).steps += amount;
      saveState();
      toast(`+${amount} steps`);
      renderAll();
    } else if (kind === "water") {
      addWater(amount);
    } else if (kind === "water-undo") {
      undoLastWater();
    } else if (kind === "active") {
      getDay(todayKey()).active += amount;
      saveState();
      toast(`+${amount} active min`);
      renderAll();
    } else if (kind === "workout") {
      showView("activity");
      $("#formActivity input[name=duration]")?.focus();
    }
  });

  // ---------- Settings ----------
  function populateSettingsForms() {
    const gf = $("#formGoals");
    gf.stepsGoal.value = state.goals.steps;
    gf.waterGoal.value = state.goals.water;
    gf.activeGoal.value = state.goals.active;
    gf.sleepGoal.value = state.goals.sleep;
    gf.weightUnit.value = state.goals.weightUnit;

    const pf = $("#formProfile");
    pf.name.value = state.profile.name || "";
    pf.height.value = state.profile.height || "";
  }

  $("#formGoals").addEventListener("submit", (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    state.goals = {
      steps: Number(fd.get("stepsGoal")),
      water: Number(fd.get("waterGoal")),
      active: Number(fd.get("activeGoal")),
      sleep: Number(fd.get("sleepGoal")),
      weightUnit: fd.get("weightUnit"),
    };
    saveState();
    toast("Goals saved");
    renderAll();
  });

  $("#formProfile").addEventListener("submit", (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    state.profile = {
      name: (fd.get("name") || "").toString().slice(0, 40),
      height: fd.get("height") ? Number(fd.get("height")) : null,
    };
    saveState();
    toast("Profile saved");
  });

  $("#btnExport").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `vitals-backup-${todayKey()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast("Exported");
  });

  $("#btnImportTrigger").addEventListener("click", () => $("#fileImport").click());
  $("#fileImport").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result);
        state = { ...defaultState(), ...parsed };
        saveState();
        populateSettingsForms();
        toast("Data imported");
        renderAll();
      } catch (err) {
        toast("Invalid backup file");
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  });

  $("#btnReset").addEventListener("click", () => {
    if (!confirm("Delete ALL data on this device? This cannot be undone.")) return;
    state = defaultState();
    saveState();
    populateSettingsForms();
    toast("All data reset");
    renderAll();
  });

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ---------- Master render ----------
  function renderAll() {
    const active = $(".view.active");
    if (!active) return;
    switch (active.id) {
      case "view-dashboard": renderDashboard(); break;
      case "view-activity": renderActivity(); break;
      case "view-water": renderWater(); break;
      case "view-sleep": renderSleep(); break;
      case "view-body": renderBody(); break;
      case "view-settings": break;
    }
  }

  window.addEventListener("resize", () => renderAll());

  // ---------- Init ----------
  function init() {
    applyTheme();
    $("#todayLabel").textContent = new Date().toLocaleDateString(undefined, {
      weekday: "short", month: "short", day: "numeric",
    });
    populateSettingsForms();
    renderAll();

    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () => {
        navigator.serviceWorker.register("service-worker.js").catch((err) => {
          console.warn("Service worker registration failed", err);
        });
      });
    }

    const installHint = $("#installHint");
    let deferredPrompt = null;
    window.addEventListener("beforeinstallprompt", (e) => {
      e.preventDefault();
      deferredPrompt = e;
      installHint.textContent = "Tap the browser menu and choose \"Install app\" / \"Add to Home Screen\" to install Vitals.";
    });
    window.addEventListener("appinstalled", () => {
      installHint.textContent = "Vitals is installed on this device.";
    });
    if (!installHint.textContent) {
      installHint.textContent = "On iPad: Safari → Share → Add to Home Screen. On Android: Chrome menu (⋮) → Install app.";
    }
  }

  init();
})();
