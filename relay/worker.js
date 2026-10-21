// MyDesk WhatsApp relay — a Cloudflare Worker (free plan is plenty).
//
// WhatsApp (Meta) needs a public HTTPS webhook. This tiny relay is that webhook,
// so your PC never has to be reachable from the internet:
//
//   WhatsApp ──webhook──▶ relay (stores your messages) ◀──polls── MyDesk on your PC
//   MyDesk ──replies directly──▶ WhatsApp Cloud API
//
// Secrets (set with `wrangler secret put NAME`):
//   VERIFY_TOKEN     any random string; also typed into Meta's webhook settings
//   APP_SECRET       your Meta app's secret, used to check every webhook is really from Meta
//   RELAY_KEY        long random string MyDesk uses to collect messages
//   ALLOWED_NUMBERS  your WhatsApp number(s), digits only with country code, comma-separated (e.g. 9198xxxxxxxx)
// Database: a D1 database bound as DB (see schema.sql).

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json" } });

async function hmacHex(secret, body) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 1) Meta's one-time webhook verification
    if (request.method === "GET" && url.pathname === "/webhook") {
      const ok = url.searchParams.get("hub.mode") === "subscribe" &&
        safeEqual(url.searchParams.get("hub.verify_token") || "", env.VERIFY_TOKEN || "");
      return ok ? new Response(url.searchParams.get("hub.challenge") || "") : new Response("forbidden", { status: 403 });
    }

    // 2) Incoming WhatsApp messages
    if (request.method === "POST" && url.pathname === "/webhook") {
      const raw = await request.text();
      const given = (request.headers.get("x-hub-signature-256") || "").replace(/^sha256=/, "");
      if (!env.APP_SECRET || !safeEqual(given, await hmacHex(env.APP_SECRET, raw))) {
        return new Response("bad signature", { status: 401 });
      }
      const allowed = new Set((env.ALLOWED_NUMBERS || "").split(",").map((s) => s.replace(/\D/g, "")).filter(Boolean));
      let body;
      try { body = JSON.parse(raw); } catch { return new Response("ok"); }
      const rows = [];
      for (const entry of body.entry || []) {
        for (const change of entry.changes || []) {
          for (const m of (change.value && change.value.messages) || []) {
            const from = String(m.from || "").replace(/\D/g, "");
            if (!allowed.has(from)) continue;                 // ignore everyone else, silently
            const text = m.type === "text" ? (m.text && m.text.body) || "" : `[${m.type}]`;
            rows.push(env.DB.prepare("INSERT OR IGNORE INTO messages (id, from_number, body, ts) VALUES (?, ?, ?, ?)")
              .bind(String(m.id), from, text.slice(0, 2000), Number(m.timestamp || Date.now() / 1000)));
          }
        }
      }
      if (rows.length) await env.DB.batch(rows);
      return new Response("ok");                              // always 200 so Meta doesn't retry forever
    }

    // 3) MyDesk collects waiting messages (outgoing request from your PC)
    if (request.method === "POST" && url.pathname === "/pull") {
      const auth = (request.headers.get("authorization") || "").replace(/^Bearer /, "");
      if (!env.RELAY_KEY || !safeEqual(auth, env.RELAY_KEY)) return json({ error: "forbidden" }, 403);
      const { results } = await env.DB.prepare(
        "SELECT id, from_number, body, ts FROM messages WHERE taken = 0 ORDER BY ts LIMIT 20").all();
      if (results.length) {
        await env.DB.batch(results.map((r) => env.DB.prepare("UPDATE messages SET taken = 1 WHERE id = ?").bind(r.id)));
      }
      // keep the table small: forget collected messages after 7 days
      await env.DB.prepare("DELETE FROM messages WHERE taken = 1 AND ts < ?").bind(Date.now() / 1000 - 7 * 86400).run();
      return json({ messages: results });
    }

    if (url.pathname === "/") return new Response("MyDesk relay is running.");
    return new Response("not found", { status: 404 });
  },
};
