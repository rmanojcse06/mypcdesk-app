/* MyDesk front end: talks to the local server with the per-launch token. */
"use strict";

const TOKEN = window.MYDESK_TOKEN;
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } },
};

let STATE = null;
let current = { section: null, tool: null };
let osTimer = null;

async function api(path, body) {
  const opts = { headers: { "X-MyDesk-Token": TOKEN } };
  if (body !== undefined) {
    opts.method = "POST";
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function toast(msg) {
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2600);
}

/* ---------- header ---------- */
function renderBrand() {
  const colors = ["--blue", "--pink", "--green", "--amber", "--violet", "--red"];
  $("#brand").innerHTML = [..."MyDesk"].map((ch, i) => `<span style="color:var(${colors[i]})">${ch}</span>`).join("");
}

function ordinal(n) {
  const s = ["th", "st", "nd", "rd"], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function tickClock() {
  const d = new Date();
  const time = d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", hour12: true }).toLowerCase();
  let tz = STATE?.tz;
  if (!tz) {
    try { tz = new Intl.DateTimeFormat("en-IN", { timeZoneName: "short" }).formatToParts(d).find((p) => p.type === "timeZoneName")?.value; } catch { tz = ""; }
  }
  $("#clockTime").textContent = `${time} ${tz || ""}`.trim();
  $("#clockDate").textContent = `${d.toLocaleDateString("en-IN", { weekday: "long" })}, ${ordinal(d.getDate())} ${d.toLocaleDateString("en-IN", { month: "long" })} ${d.getFullYear()}`;
}

/* ---------- health strip ---------- */
async function refreshHealth() {
  try {
    const h = await api("/api/health");
    for (const key of ["cpu", "memory", "storage"]) {
      const g = $(`.gauge[data-key="${key}"]`);
      const pct = Math.max(0, Math.min(100, h[key]));
      $(".val", g).textContent = `${pct}%`;
      $(".arc", g).style.strokeDashoffset = String(113.1 * (1 - pct / 100));
      g.classList.toggle("hot", pct >= 90);
      $(".detail", g).textContent = key === "memory" ? h.memory_detail : key === "storage" ? h.storage_detail : "";
    }
    $("#lastReboot").textContent = h.last_reboot || "–";
    $("#lastSignIn").textContent = h.last_sign_in || "–";
    const up = h.uptime_hours;
    $("#uptime").textContent = up >= 24 ? `${Math.floor(up / 24)} d ${Math.round(up % 24)} h` : `${up} h`;
    if (h.devices) renderDevices(h.devices);
  } catch { /* server busy; try next tick */ }
}

/* ---------- drives + device indicators ---------- */
const USB_ICONS = { storage: "💾", keyboard: "⌨️", mouse: "🖱️", phone: "📱", audio: "🎧", camera: "📷", bluetooth: "🔵", input: "🎮", other: "🔌" };
let seen = null; // previous drives / USB devices, for plug-in toasts

function renderDevices(d) {
  const drives = d.drives || [];
  const usb = d.usb; // null = can't tell on this computer
  const now = { drives: new Set(drives.map((x) => x.mount)), usb: new Set((usb || []).map((x) => x.name)) };
  const fresh = new Set();
  if (seen) {
    for (const x of drives) if (!seen.drives.has(x.mount)) { fresh.add(`d:${x.mount}`); toast(`Drive connected: ${x.name}${x.label ? ` (${x.label})` : ""}`); }
    for (const m of seen.drives) if (!now.drives.has(m)) toast(`Drive removed: ${m}`);
    if (usb && seen.usbKnown) {
      for (const x of usb) if (!seen.usb.has(x.name)) { fresh.add(`u:${x.name}`); toast(`USB connected: ${x.name}`); }
      for (const n of seen.usb) if (!now.usb.has(n)) toast(`USB removed: ${n}`);
    }
  }
  seen = { ...now, usbKnown: !!usb };

  $("#driveChips").innerHTML = drives.map((x) => {
    const isUsb = x.kind === "usb";
    const cls = ["ind", "drive", isUsb ? "usb" : "", x.percent >= 90 ? "full" : "", fresh.has(`d:${x.mount}`) ? "new" : ""].join(" ");
    const tip = `${x.label ? x.label + " · " : ""}${x.free_gb} GB free of ${x.total_gb} GB · ${x.fs}${x.kind === "network" ? " · network" : ""}`;
    return `<span class="${cls}" title="${esc(tip)}">${isUsb ? `<span class="tagx">USB</span>` : `<span class="ic">${x.kind === "network" ? "🌐" : "🖴"}</span>`}${esc(x.name)}
      <span class="bar"><i style="width:${x.percent}%"></i></span><small>${x.percent}%</small></span>`;
  }).join("");

  const chips = [];
  if (usb) {
    const groups = {};
    for (const x of usb) (groups[x.kind] ||= []).push(x.name);
    const list = Object.entries(groups).map(([k, names]) => `<b>${USB_ICONS[k] || "🔌"} ${esc(k)}</b>${names.map((n) => `<div>${esc(n)}</div>`).join("")}`).join("");
    const isNew = usb.some((x) => fresh.has(`u:${x.name}`));
    chips.push(`<span class="ind ${usb.length ? "usb" : "off"} ${isNew ? "new" : ""}"><span class="ic">🔌</span>USB<small>${usb.length || "none"}</small>
      ${usb.length ? `<span class="pop">${list}</span>` : ""}</span>`);
  }
  if (d.audio) {
    const a = d.audio;
    const label = a.jack ? "Headphones" : a.outputs.length ? "Speakers" : "No output";
    const pop = `<b>Playing through</b>${a.outputs.map((n) => `<div>${esc(n)}</div>`).join("") || "<div>Nothing</div>"}
      ${a.unplugged.length ? `<b>Jack unplugged</b>${a.unplugged.map((n) => `<div>${esc(n)}</div>`).join("")}` : ""}`;
    chips.push(`<span class="ind ${a.jack ? "on-green" : a.outputs.length ? "" : "off"}"><span class="ic">${a.jack ? "🎧" : "🔊"}</span>${label}<span class="pop">${pop}</span></span>`);
  }
  if (d.touch) {
    const t = d.touch;
    chips.push(`<span class="ind ${t.present ? "on-green" : "off"}" title="${t.present ? `Touch screen${t.points ? `, ${t.points}-point` : ""}${t.pen ? ", pen supported" : ""}` : "No touch screen"}">
      <span class="ic">👆</span>Touch<small>${t.present ? (t.ready ? "on" : "not ready") : "none"}</small></span>`);
  }
  $("#deviceChips").innerHTML = chips.join("");

  const k = d.locks;
  $("#lockChips").innerHTML = k ? [["caps", "Caps"], ["num", "Num"], ["scroll", "Scroll"]]
    .filter(([key]) => key in k)
    .map(([key, label]) => `<span class="key ${k[key] ? "lit" : ""}" title="${label} Lock is ${k[key] ? "on" : "off"}">${label}</span>`).join("") : "";
}

/* ---------- sidebar ---------- */
const toolsIn = (sid) => STATE.tools.filter((t) => t.section === sid);
const sectionById = (sid) => STATE.sections.find((s) => s.id === sid);

/* Sidebar = one compact row per section. Hovering (or keyboard-focusing) a row
   opens a flyout beside it with that section's tools, so the list stays short
   no matter how many tools you add. Clicking the row opens the section page. */
function sectionItems(s) {
  const live = toolsIn(s.id).slice().sort((a, b) => a.name.localeCompare(b.name));
  const liveNames = new Set(live.map((t) => t.name.toLowerCase()));
  const planned = (s.planned || []).filter((p) => !liveNames.has(p.toLowerCase()));
  return [
    ...(s.builtin ? [{ kind: "builtin", name: "Live monitor" }] : []),
    ...live.map((t) => ({ kind: "tool", id: t.id, name: t.name, desc: t.description || "" })),
    ...planned.map((p) => ({ kind: "soon", name: p })),
  ];
}

function renderSidebar() {
  $("#sidebar").innerHTML = STATE.sections.map((s) => {
    const n = toolsIn(s.id).length;
    return `<div class="nav-section" data-section="${s.id}" style="--sc:${s.color}">
      <button class="nav-btn" aria-haspopup="menu"><span class="dot"></span>
        <span class="nav-text"><span class="nav-name">${esc(s.name)}</span><small class="sub"></small></span>
        <span class="count">${n || ""}</span><span class="chev" aria-hidden="true">›</span></button></div>`;
  }).join("");

  const fly = document.createElement("div");
  fly.id = "flyout";
  fly.className = "flyout";
  fly.setAttribute("role", "menu");
  fly.hidden = true;
  document.body.appendChild(fly);

  let hideTimer = null;
  const cancelHide = () => clearTimeout(hideTimer);
  const scheduleHide = () => { cancelHide(); hideTimer = setTimeout(hideFlyout, 220); };

  $("#sidebar").addEventListener("mouseover", (e) => {
    const sec = e.target.closest(".nav-section");
    if (!sec) return;
    cancelHide();
    if (fly.dataset.section !== sec.dataset.section || fly.hidden) showFlyout(sec);
  });
  $("#sidebar").addEventListener("mouseleave", scheduleHide);
  $("#sidebar").addEventListener("focusin", (e) => {
    const sec = e.target.closest(".nav-section");
    if (sec) { cancelHide(); showFlyout(sec); }
  });
  fly.addEventListener("mouseenter", cancelHide);
  fly.addEventListener("mouseleave", scheduleHide);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") hideFlyout(); });
  $("#stage").addEventListener("scroll", hideFlyout, { passive: true });
  window.addEventListener("resize", hideFlyout);

  $("#sidebar").onclick = (e) => {
    const sec = e.target.closest(".nav-section");
    if (!sec) return;
    openSection(sec.dataset.section);
    if (sec.matches(":hover")) showFlyout(sec); // keep the menu open under the pointer
  };
  fly.onclick = (e) => {
    const b = e.target.closest("button.fly-item");
    if (!b) return;
    hideFlyout();
    if (b.dataset.tool) openTool(b.dataset.tool);
    else openSection(fly.dataset.section);
  };
  fly.addEventListener("keydown", (e) => {
    const items = [...fly.querySelectorAll("button.fly-item:not([hidden])")];
    const i = items.indexOf(document.activeElement);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const next = items[(i + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length];
      next?.focus();
    }
  });
}

function showFlyout(secEl) {
  const fly = $("#flyout");
  const s = sectionById(secEl.dataset.section);
  const items = sectionItems(s);
  const live = items.filter((x) => x.kind !== "soon").length;
  fly.dataset.section = s.id;
  fly.style.setProperty("--sc", s.color);
  const row = (x) => {
    if (x.kind === "soon") return `<div class="fly-item soon" role="menuitem" aria-disabled="true">${esc(x.name)}<em>soon</em></div>`;
    const on = (x.kind === "tool" && current.tool === x.id) || (x.kind === "builtin" && current.section === s.id && !current.tool);
    return `<button class="fly-item ${on ? "on" : ""}" role="menuitem" ${x.id ? `data-tool="${esc(x.id)}"` : ""} title="${esc(x.desc || "")}">${esc(x.name)}</button>`;
  };
  fly.innerHTML = `
    <div class="fly-head"><span class="dot"></span>${esc(s.name)}<small>${live ? `${live} ready` : "nothing yet"}</small></div>
    ${items.length > 8 ? `<input class="fly-filter" type="search" placeholder="Filter ${items.length} tools…" aria-label="Filter tools">` : ""}
    <div class="fly-list">${items.map(row).join("") || `<div class="fly-item soon">No tools yet</div>`}</div>
    <button class="fly-item fly-all" data-section="${s.id}">Open ${esc(s.name)} →</button>`;
  const filter = $(".fly-filter", fly);
  if (filter) {
    filter.addEventListener("input", () => {
      const q = filter.value.trim().toLowerCase();
      fly.querySelectorAll(".fly-list .fly-item").forEach((el) => { el.hidden = !!q && !el.textContent.toLowerCase().includes(q); });
    });
  }
  document.querySelectorAll(".nav-section").forEach((el) => el.classList.toggle("hover", el === secEl));
  fly.hidden = false;
  const r = secEl.getBoundingClientRect();
  const side = $("#sidebar").getBoundingClientRect();
  const h = fly.offsetHeight;
  fly.style.left = `${side.right + 10}px`;
  fly.style.top = `${Math.max(12, Math.min(r.top - 6, window.innerHeight - h - 12))}px`;
}

function hideFlyout() {
  const fly = $("#flyout");
  if (fly) fly.hidden = true;
  document.querySelectorAll(".nav-section.hover").forEach((el) => el.classList.remove("hover"));
}

function markNav() {
  document.querySelectorAll(".nav-section").forEach((el) => {
    const active = el.dataset.section === current.section;
    el.classList.toggle("active", active);
    const tool = active && current.tool ? STATE.tools.find((t) => t.id === current.tool) : null;
    $(".sub", el).textContent = tool ? tool.name : "";
  });
}

function setStageColor(color) {
  $("#stage").style.setProperty("--sc", color);
}

/* ---------- section view ---------- */
function openSection(sid, builtin = false) {
  const s = sectionById(sid);
  if (!s) return;
  clearInterval(osTimer);
  // Sections with a built-in panel (OS Monitor) always open on that panel.
  current = { section: sid, tool: null, builtin: !!s.builtin };
  store.set("mydesk.view", current);
  markNav();
  setStageColor(s.color);
  if (s.builtin) return renderOsMonitor(s);

  const live = toolsIn(sid);
  const liveNames = new Set(live.map((t) => t.name.toLowerCase()));
  const tiles = [
    ...live.map((t) => `<button class="tile" data-tool="${esc(t.id)}"><span class="live">● READY</span><h3>${esc(t.name)}</h3><p>${esc(t.description || "")}</p></button>`),
    ...(s.planned || []).filter((p) => !liveNames.has(p.toLowerCase()))
      .map((p) => `<div class="tile soon"><h3>${esc(p)}</h3><p>Coming soon. Add it as a script in <code>tools/</code>.</p></div>`),
  ].join("");
  $("#stage").innerHTML = `
    <div class="view-head"><div class="badge">${esc(s.name[0])}</div>
      <div><div class="crumb">Section</div><h2>${esc(s.name)}</h2><p>${esc(s.blurb || "")}</p></div></div>
    <div class="grid">${tiles}</div>`;
  $("#stage").onclick = (e) => {
    const t = e.target.closest(".tile[data-tool]");
    if (t) openTool(t.dataset.tool);
  };
}

/* ---------- OS monitor ---------- */
function renderOsMonitor(s) {
  $("#stage").innerHTML = `
    <div class="view-head"><div class="badge">${esc(s.name[0])}</div>
      <div><div class="crumb">${esc(s.name)}</div><h2>Live monitor</h2><p>${esc(s.blurb)}</p></div></div>
    <div class="panel"><div class="stat-row" id="osStats"></div></div>
    <div class="os-grid">
      <div class="panel"><h3>CPU cores <span class="muted">% busy per logical core</span></h3><div class="bars" id="cpuBars"></div></div>
      <div class="panel"><h3>Disks</h3><div id="disks"></div></div>
    </div>
    <div class="panel"><h3>Busiest apps right now</h3>
      <table class="procs"><thead><tr><th>App</th><th class="num">PID</th><th class="num">CPU %</th><th class="num">Memory</th></tr></thead><tbody id="procs"></tbody></table></div>`;
  const tick = async () => {
    if (!$("#procs")) return clearInterval(osTimer);
    try {
      const o = await api("/api/os");
      $("#osStats").innerHTML = `
        <div><b>${o.cpu_cores}</b>logical cores${o.cpu_mhz ? ` · ${o.cpu_mhz} MHz` : ""}</div>
        <div><b>${o.net_kbps.down} KB/s</b>download</div>
        <div><b>${o.net_kbps.up} KB/s</b>upload</div>
        ${o.battery ? `<div><b>${o.battery.percent}%</b>battery${o.battery.plugged ? " · charging" : ""}</div>` : ""}`;
      $("#cpuBars").innerHTML = o.per_cpu.map((v) => `<div title="${v}%"><i style="height:${v}%"></i></div>`).join("");
      $("#disks").innerHTML = o.disks.map((d) => `
        <div class="disk"><b>${esc(d.mount)}</b><div class="meter"><i style="width:${d.percent}%;background:${d.percent > 90 ? "var(--red)" : "var(--amber)"}"></i></div>
        <span>${d.free_gb} GB free of ${d.total_gb}</span></div>`).join("") || `<div class="empty">No disks found</div>`;
      $("#procs").innerHTML = o.processes.map((p) => `
        <tr><td>${esc(p.name)}</td><td class="num">${p.pid}</td><td class="num">${p.cpu}</td><td class="num">${p.mem_mb} MB</td></tr>`).join("")
        || `<tr><td colspan="4">Collecting… first numbers arrive in a few seconds.</td></tr>`;
    } catch { /* retry next tick */ }
  };
  tick();
  osTimer = setInterval(tick, 3000);
}

/* ---------- generic tool view ---------- */
const PLATFORM_COLORS = {
  youtube: ["#ff3b30", "#fff"], instagram: ["#e1306c", "#fff"], facebook: ["#1877f2", "#fff"],
  linkedin: ["#0a66c2", "#fff"], tiktok: ["#111", "#fff"], twitter: ["#111", "#fff"], x: ["#111", "#fff"],
};
function platformChip(p) {
  const key = String(p || "").toLowerCase().replace(/[^a-z]/g, "");
  const [bg, fg] = PLATFORM_COLORS[key] || ["#fff", "#1d2233"];
  return p ? `<span class="chip" style="--pc:${bg};--pt:${fg}">${esc(p)}</span>` : "";
}

function fieldHtml(f) {
  const id = `f_${f.name}`;
  if (f.type === "checkbox") {
    return `<label class="check"><input type="checkbox" id="${id}" name="${esc(f.name)}" ${f.default ? "checked" : ""}> ${esc(f.label || f.name)}</label>`;
  }
  if (f.type === "select") {
    const opts = (f.options || []).map((o) => {
      const [val, label] = Array.isArray(o) ? o : [o, o || "None"];
      return `<option value="${esc(val)}" ${val === f.default ? "selected" : ""}>${esc(label)}</option>`;
    }).join("");
    return `<div class="field"><label for="${id}">${esc(f.label || f.name)}</label><select id="${id}" name="${esc(f.name)}">${opts}</select></div>`;
  }
  return `<div class="field ${f.positional ? "" : ""}"><label for="${id}">${esc(f.label || f.name)}</label>
    <input type="${f.type === "url" ? "url" : "text"}" id="${id}" name="${esc(f.name)}" placeholder="${esc(f.placeholder || "")}" ${f.required ? "required" : ""}></div>`;
}

function openTool(toolId) {
  const tool = STATE.tools.find((t) => t.id === toolId);
  if (!tool) return;
  clearInterval(osTimer);
  const s = sectionById(tool.section) || { name: "Tools", color: "#e5484d" };
  current = { section: tool.section, tool: toolId };
  store.set("mydesk.view", current);
  markNav();
  setStageColor(s.color);

  const main = tool.inputs.filter((f) => f.positional || f.type === "url" || f.type === "text");
  const extra = tool.inputs.filter((f) => !main.includes(f));
  $("#stage").innerHTML = `
    <div class="view-head"><div class="badge">${esc(tool.name[0])}</div>
      <div><div class="crumb">${esc(s.name)}</div><h2>${esc(tool.name)}</h2><p>${esc(tool.description || "")}</p></div></div>
    <div id="toolBody">
      <form class="panel" id="toolForm" autocomplete="off">
        <div class="form">
          <div>${main.map(fieldHtml).join("")}</div>
          <button class="btn" type="submit" id="runBtn">${esc(tool.run_label || "Run")}</button>
          ${extra.length ? `<div class="opts">${extra.map(fieldHtml).join("")}</div>` : ""}
        </div>
        <ul class="steps" id="steps"></ul>
      </form>
      ${tool.outputs ? `<div class="panel"><h3>${esc(tool.outputs.label || "Saved")} <span class="muted" id="libCount"></span></h3><div class="library" id="library"></div></div>` : ""}
    </div>
    <div id="viewer" hidden></div>`;

  $("#toolForm").onsubmit = (e) => { e.preventDefault(); runTool(tool); };
  if (tool.outputs) loadLibrary(tool);
  setTimeout(() => $("#toolForm input")?.focus(), 30);
}

function collectValues(tool) {
  const values = {};
  for (const f of tool.inputs) {
    const el = document.getElementById(`f_${f.name}`);
    if (!el) continue;
    values[f.name] = f.type === "checkbox" ? el.checked : el.value.trim();
  }
  return values;
}

async function runTool(tool) {
  const btn = $("#runBtn");
  const steps = $("#steps");
  btn.disabled = true;
  steps.innerHTML = `<li class="run placeholder">Starting…</li>`;
  try {
    const { job } = await api("/api/run", { tool: tool.id, values: collectValues(tool) });
    let shown = 0;
    while (true) {
      await new Promise((r) => setTimeout(r, 900));
      const j = await api(`/api/job?id=${job}`);
      if (j.events.length || j.status !== "running") steps.querySelector("li.placeholder")?.remove();
      if (j.events.length > shown) {
        steps.querySelector("li.run")?.classList.remove("run");
        for (const ev of j.events.slice(shown)) {
          steps.insertAdjacentHTML("beforeend", `<li class="${ev.level === "warn" ? "err" : ""}">${esc(ev.msg)}</li>`);
        }
        shown = j.events.length;
        steps.lastElementChild?.classList.add("run");
      }
      if (j.status !== "running") {
        steps.querySelector("li.run")?.classList.remove("run");
        if (j.status === "done") {
          steps.insertAdjacentHTML("beforeend", `<li class="ok">${esc(j.result.msg || "Done")}</li>`);
          $("#toolForm").reset();
          if (tool.outputs) await loadLibrary(tool);
          if (j.result.open) openOutput(tool, j.result.open);
        } else {
          steps.insertAdjacentHTML("beforeend", `<li class="err">Failed: ${esc(j.error)}</li>`);
        }
        break;
      }
    }
  } catch (err) {
    steps.insertAdjacentHTML("beforeend", `<li class="err">${esc(err.message)}</li>`);
  } finally {
    btn.disabled = false;
  }
}

async function loadLibrary(tool) {
  const items = await api(`/api/outputs?tool=${encodeURIComponent(tool.id)}`).catch(() => []);
  const lib = $("#library");
  if (!lib) return;
  $("#libCount").textContent = items.length ? `${items.length} saved` : "";
  if (!items.length) {
    lib.innerHTML = `<div class="empty" style="grid-column:1/-1">${esc(tool.outputs.empty || "Nothing saved yet.")}</div>`;
    return;
  }
  const fileUrl = (rel) => `/files/${encodeURIComponent(tool.id)}/${rel.split("/").map(encodeURIComponent).join("/")}?t=${encodeURIComponent(TOKEN)}`;
  lib.innerHTML = items.map((it) => `
    <button class="clip" data-path="${esc(it.path)}">
      <div class="cover" ${it.cover ? `style="background-image:url('${fileUrl(it.cover)}')"` : ""}>${it.cover ? "" : "▶"}</div>
      <div class="meta"><h4>${esc(it.title)}</h4>${platformChip(it.platform)}<small>${esc((it.captured || "").slice(0, 10))}</small></div>
    </button>`).join("");
  lib.onclick = (e) => {
    const c = e.target.closest(".clip");
    if (c) openOutput(tool, c.dataset.path);
  };
}

async function openOutput(tool, path) {
  const r = await api(`/api/render?tool=${encodeURIComponent(tool.id)}&path=${encodeURIComponent(path)}`);
  const doc = `<!doctype html><html><head><meta charset="utf-8"><base target="_blank"><style>
    body{font:15px/1.6 "Segoe UI",system-ui,sans-serif;color:#1d2233;margin:22px 26px;max-width:880px}
    h1,h2,h3{font-family:Cambria,Georgia,serif;line-height:1.2} h1{font-size:26px;margin-top:0}
    h2{font-size:19px;border-bottom:2px solid #1d2233;padding-bottom:4px;margin-top:28px}
    img{max-width:31%;border:2px solid #1d2233;border-radius:10px;margin:0 1% 8px 0;vertical-align:top}
    blockquote{margin:0;padding:10px 16px;background:#fbf6ec;border-left:5px solid ${tool.accent || "#e5484d"};border-radius:6px}
    pre{background:#f3efe5;padding:12px 14px;border-radius:10px;white-space:pre-wrap;font:13px/1.5 Consolas,monospace}
    table{border-collapse:collapse} td,th{border:1px solid #ddd5c4;padding:5px 10px;text-align:left}
    a{color:#2f6fed}
  </style></head><body>${r.html}</body></html>`;
  $("#toolBody").hidden = true;
  const v = $("#viewer");
  v.hidden = false;
  v.innerHTML = `<div class="viewer">
      <div class="viewer-bar"><button class="btn ghost" id="backBtn">← Back</button><span class="grow"></span>
        <button class="btn ghost" id="folderBtn">Open folder</button>
        ${r.meta.url ? `<a class="btn" href="${esc(r.meta.url)}" target="_blank" rel="noopener">Open original</a>` : ""}</div>
      ${r.video_url ? `<video controls preload="metadata" src="${esc(r.video_url)}"></video>` : ""}
      <iframe sandbox="allow-popups allow-popups-to-escape-sandbox" title="Saved note"></iframe>
    </div>`;
  $("iframe", v).srcdoc = doc;
  $("#backBtn").onclick = () => { v.hidden = true; v.innerHTML = ""; $("#toolBody").hidden = false; };
  $("#folderBtn").onclick = () => api("/api/open-folder", { tool: tool.id, path }).catch((e) => toast(e.message));
}

/* ---------- Claude / search bar ---------- */
function searchIndex() {
  const rows = [];
  for (const s of STATE.sections) {
    rows.push({ kind: "section", id: s.id, name: s.name, where: "Section", color: s.color, text: `${s.name} ${s.blurb}` });
    for (const p of s.planned || []) rows.push({ kind: "soon", id: s.id, name: p, where: `${s.name} · soon`, color: s.color, text: p });
  }
  for (const t of STATE.tools) {
    const s = sectionById(t.section);
    rows.push({ kind: "tool", id: t.id, name: t.name, where: s ? s.name : "Tool", color: s?.color, text: `${t.name} ${t.description || ""}` });
  }
  return rows;
}

function setupAsk() {
  const input = $("#ask"), box = $("#results");
  let matches = [], sel = 0;
  const index = searchIndex();
  const show = () => {
    const q = input.value.trim().toLowerCase();
    if (!q) { box.hidden = true; matches = []; return; }
    matches = index.filter((r) => r.text.toLowerCase().includes(q)).slice(0, 8);
    sel = 0;
    const askRow = STATE.claude_enabled ? `<button data-ask="1"><span class="dot" style="--sc:#d97757"></span>Ask Claude: “${esc(input.value.trim())}”<small>Enter</small></button>` : "";
    box.innerHTML = matches.map((m, i) => `<button data-i="${i}" class="${i === 0 ? "sel" : ""}"><span class="dot" style="--sc:${m.color}"></span>${esc(m.name)}<small>${esc(m.where)}</small></button>`).join("") + askRow;
    box.hidden = !box.innerHTML;
  };
  const go = (m) => {
    box.hidden = true;
    input.value = "";
    if (m.kind === "tool") openTool(m.id); else openSection(m.id);
  };
  input.addEventListener("input", show);
  input.addEventListener("keydown", (e) => {
    const btns = [...box.querySelectorAll("button[data-i]")];
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!btns.length) return;
      sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + btns.length) % btns.length;
      btns.forEach((b, i) => b.classList.toggle("sel", i === sel));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (matches.length && !e.ctrlKey) go(matches[sel]); else askClaude();
    } else if (e.key === "Escape") {
      box.hidden = true;
    }
  });
  box.addEventListener("mousedown", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    e.preventDefault();
    if (b.dataset.ask) askClaude(); else go(matches[+b.dataset.i]);
  });
  input.addEventListener("blur", () => setTimeout(() => { box.hidden = true; }, 120));
  $("#askBtn").onclick = askClaude;
  $("#answerClose").onclick = () => { $("#answer").hidden = true; };
}

async function askClaude() {
  const q = $("#ask").value.trim();
  $("#results").hidden = true;
  if (!q) return $("#ask").focus();
  const panel = $("#answer"), text = $("#answerText");
  panel.hidden = false;
  if (!STATE.claude_enabled) {
    text.textContent = "Claude chat is off. To turn it on, set your API key once in PowerShell:\n\nsetx ANTHROPIC_API_KEY \"sk-ant-...\"\n\nthen restart MyDesk. Typing still searches your sections and tools.";
    return;
  }
  text.textContent = "Thinking…";
  try {
    const { answer } = await api("/api/claude", { q });
    text.textContent = answer;
  } catch (err) {
    text.textContent = err.message;
  }
}

/* ---------- boot ---------- */
async function boot() {
  renderBrand();
  STATE = await api("/api/state");
  $("#userName").textContent = STATE.name;
  $("#avatar").textContent = (STATE.name || "M")[0].toUpperCase();
  document.title = `MyDesk · ${STATE.name}`;
  tickClock();
  setInterval(tickClock, 15000);
  refreshHealth();
  setInterval(refreshHealth, 1500); // fast enough for lock keys and plug-in alerts
  renderSidebar();
  setupAsk();
  const last = store.get("mydesk.view", null);
  if (last?.tool && STATE.tools.some((t) => t.id === last.tool)) openTool(last.tool);
  else if (last?.section && sectionById(last.section)) openSection(last.section, !!last.builtin);
  else openSection("junkyard");
}

boot().catch((err) => {
  document.body.innerHTML = `<pre style="padding:30px">MyDesk could not start: ${esc(err.message)}</pre>`;
});
