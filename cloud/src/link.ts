/**
 * LightsLink: the one Durable Object ("home") between the browsers and the Pi.
 *
 * The Pi's control panel (panel.py, through cloud.py) keeps a WebSocket open to /device. On it:
 *
 *   to the Pi    {"type": "request-body", "id", "data": base64} ...  the body of an API call, if any
 *                {"type": "request", "id", "method", "path", "contentType"}
 *                {"type": "watch", "on": true | false}   start or stop sending the live stream
 *   from the Pi  {"type": "response", "id", "status", "contentType"}
 *                {"type": "response-body", "id", "data": base64} ...
 *                {"type": "response-end", "id"}
 *                {"type": "event", "data": "event: state\ndata: {...}\n\n"}   the panel's stream, as is
 *
 * Every browser's /api/stream shares one stream from the Pi, which runs only while someone is
 * watching. A sound file is copied here (SQLite, 1 MB rows) the first time it's played, so
 * replays and seeking don't go back to the Pi. Its URL carries the file's version (?v=).
 */
import { DurableObject } from "cloudflare:workers";

import { byteRange } from "./http";

export interface Env {
  LightsLink: DurableObjectNamespace<LightsLink>;
  LIGHTS_PASSWORD?: string;
  LIGHTS_DEVICE_TOKEN?: string;
}

const CHUNK = 256 * 1024; // body bytes per WebSocket message, both ways
const PART = 1024 * 1024; // bytes per stored row of a sound file
const REPLY_MS = 60_000; // give up on a request this long after the Pi last said anything about it
const HEARTBEAT_MS = 15_000;
const BACKLOG = 32; // skip frames for a browser that's this many messages behind
const OFFLINE = "The lights Pi isn't connected right now. Check that it's plugged in and on Wi-Fi.";

const encoder = new TextEncoder();

interface Reply {
  status: number;
  contentType: string;
  body: Uint8Array;
}

interface Pending extends Reply {
  parts: Uint8Array[];
  resolve(reply: Reply): void;
  reject(error: Error): void;
  timer: ReturnType<typeof setTimeout> | null;
}

type Viewer = WritableStreamDefaultWriter<Uint8Array>;

export class LightsLink extends DurableObject<Env> {
  private viewers = new Set<Viewer>();
  private pending = new Map<number, Pending>();
  private nextId = 1;
  private watching = false;
  private lastState: string | null = null;
  private heartbeat: ReturnType<typeof setInterval> | null = null;

  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    ctx.storage.sql.exec("CREATE TABLE IF NOT EXISTS sounds (key TEXT PRIMARY KEY, path TEXT, type TEXT, size INTEGER)");
    ctx.storage.sql.exec("CREATE TABLE IF NOT EXISTS sound_parts (key TEXT, part INTEGER, data BLOB, PRIMARY KEY (key, part))");
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/device") return this.connectDevice(request);
    if (url.pathname === "/api/stream") return this.watch();
    if (url.pathname.startsWith("/sounds/") && request.method === "GET") return this.sound(url, request.headers.get("Range"));
    return this.relay(request, url);
  }

  // ---- The Pi ----

  private device(): WebSocket | undefined {
    return this.ctx.getWebSockets("device").find((ws) => ws.readyState === WebSocket.OPEN);
  }

  private connectDevice(request: Request): Response {
    if (request.headers.get("Upgrade") !== "websocket") return new Response("expected a WebSocket", { status: 426 });
    const old = this.ctx.getWebSockets("device");
    const [client, server] = Object.values(new WebSocketPair());
    this.ctx.acceptWebSocket(server, ["device"]);
    for (const ws of old) ws.close(1000, "replaced by a newer connection from the Pi");
    console.log(`the Pi connected${old.length ? ` (replacing ${old.length} older connection)` : ""}`);
    this.watching = false;
    this.updateWatch();
    this.broadcast(linkEvent(true));
    return new Response(null, { status: 101, webSocket: client });
  }

  async webSocketMessage(_ws: WebSocket, message: string | ArrayBuffer): Promise<void> {
    if (typeof message !== "string") return;
    let m: { type?: string; id?: number; data?: string; status?: number; contentType?: string };
    try {
      m = JSON.parse(message);
    } catch {
      console.log("the Pi sent something that isn't JSON");
      return;
    }
    if (m.type === "event" && typeof m.data === "string") {
      if (m.data.startsWith("event: state")) this.lastState = m.data;
      this.broadcast(m.data);
      return;
    }
    const pending = this.pending.get(m.id ?? -1);
    if (!pending) return; // timed out, or from before a restart
    if (m.type === "response") {
      pending.status = m.status ?? 502;
      pending.contentType = m.contentType ?? "application/octet-stream";
    } else if (m.type === "response-body" && m.data) {
      pending.parts.push(fromBase64(m.data));
    } else if (m.type === "response-end") {
      this.settle(m.id!);
      pending.resolve({ status: pending.status, contentType: pending.contentType, body: concat(pending.parts) });
      return;
    }
    this.waitFor(m.id!, pending);
  }

  async webSocketClose(ws: WebSocket, code: number, reason: string): Promise<void> {
    try {
      ws.close(code, reason);
    } catch {
      // already closed, or a code we can't echo back
    }
    this.lostDevice(`the Pi disconnected (${code}${reason ? ` ${reason}` : ""})`);
  }

  async webSocketError(_ws: WebSocket, error: unknown): Promise<void> {
    this.lostDevice(`the Pi's connection failed: ${error}`);
  }

  private lostDevice(why: string): void {
    console.log(why);
    for (const [id, pending] of this.pending) {
      this.settle(id);
      pending.reject(new Error(OFFLINE));
    }
    if (!this.device()) {
      this.watching = false;
      this.broadcast(linkEvent(false));
    }
  }

  /** Pass one API call to the Pi and wait for its whole answer. */
  private ask(method: string, path: string, contentType: string | null, body: Uint8Array | null): Promise<Reply> {
    const device = this.device();
    if (!device) return Promise.reject(new Error(OFFLINE));
    const id = this.nextId++;
    return new Promise<Reply>((resolve, reject) => {
      const pending: Pending = { status: 502, contentType: "application/octet-stream", body: new Uint8Array(), parts: [], resolve, reject, timer: null };
      this.pending.set(id, pending);
      this.waitFor(id, pending);
      try {
        for (let at = 0; body && at < body.length; at += CHUNK) {
          device.send(JSON.stringify({ type: "request-body", id, data: toBase64(body.subarray(at, at + CHUNK)) }));
        }
        device.send(JSON.stringify({ type: "request", id, method, path, contentType }));
      } catch (e) {
        console.log(`couldn't send ${method} ${path} to the Pi: ${e}`);
        this.settle(id);
        reject(new Error(OFFLINE));
      }
    });
  }

  private waitFor(id: number, pending: Pending): void {
    if (pending.timer) clearTimeout(pending.timer);
    pending.timer = setTimeout(() => {
      console.log(`the Pi didn't answer request ${id} in time`);
      this.settle(id);
      pending.reject(new Error("The lights Pi didn't answer in time."));
    }, REPLY_MS);
  }

  private settle(id: number): void {
    const timer = this.pending.get(id)?.timer;
    if (timer) clearTimeout(timer);
    this.pending.delete(id);
  }

  private async relay(request: Request, url: URL): Promise<Response> {
    const body = request.method === "GET" || request.method === "HEAD" ? null : new Uint8Array(await request.arrayBuffer());
    try {
      const reply = await this.ask(request.method, url.pathname + url.search, request.headers.get("Content-Type"), body);
      return new Response(reply.body, { status: reply.status, headers: { "Content-Type": reply.contentType, "Cache-Control": "no-store" } });
    } catch (e) {
      return Response.json({ error: (e as Error).message, offline: !this.device() }, { status: 503 });
    }
  }

  // ---- Browsers watching the live stream ----

  private watch(): Response {
    const { readable, writable } = new TransformStream<Uint8Array, Uint8Array>();
    const viewer = writable.getWriter();
    this.viewers.add(viewer);
    const online = Boolean(this.device());
    this.send(viewer, linkEvent(online));
    if (online && this.lastState) this.send(viewer, this.lastState);
    this.heartbeat ??= setInterval(() => this.broadcast(": still here\n\n"), HEARTBEAT_MS);
    this.updateWatch();
    return new Response(readable, { headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-store" } });
  }

  private send(viewer: Viewer, text: string, droppable = false): void {
    if (droppable && (viewer.desiredSize ?? 0) < -BACKLOG) return;
    viewer.write(encoder.encode(text)).catch(() => this.leave(viewer));
  }

  private broadcast(text: string): void {
    const frame = text.startsWith("event: preview") || text.startsWith("event: lights");
    for (const viewer of [...this.viewers]) this.send(viewer, text, frame);
  }

  private leave(viewer: Viewer): void {
    if (!this.viewers.delete(viewer)) return;
    viewer.abort().catch(() => {});
    if (!this.viewers.size && this.heartbeat) {
      clearInterval(this.heartbeat);
      this.heartbeat = null;
    }
    this.updateWatch();
  }

  /** Have the Pi stream while anyone's watching, and stop when nobody is. */
  private updateWatch(): void {
    const want = this.viewers.size > 0;
    const device = this.device();
    if (!device || want === this.watching) return;
    try {
      device.send(JSON.stringify({ type: "watch", on: want }));
      this.watching = want;
      console.log(want ? "someone's watching: the Pi starts streaming" : "nobody's watching: the Pi stops streaming");
    } catch (e) {
      console.log(`couldn't tell the Pi to ${want ? "start" : "stop"} streaming: ${e}`);
    }
  }

  // ---- Sound files ----

  private async sound(url: URL, range: string | null): Promise<Response> {
    const key = url.pathname + url.search;
    const sql = this.ctx.storage.sql;
    let file = sql.exec<{ type: string; size: number }>("SELECT type, size FROM sounds WHERE key = ?", key).toArray()[0];
    if (!file) {
      let reply: Reply;
      try {
        reply = await this.ask("GET", key, null, null);
      } catch (e) {
        return new Response((e as Error).message, { status: 503 });
      }
      if (reply.status !== 200) return new Response(reply.body, { status: reply.status, headers: { "Content-Type": reply.contentType } });
      this.keep(key, url.pathname, reply.contentType, reply.body);
      file = { type: reply.contentType, size: reply.body.length };
    }
    const wanted = byteRange(range, file.size);
    if (wanted === "unsatisfiable") return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${file.size}` } });
    const [start, end] = wanted ?? [0, file.size - 1];
    const body = this.readSound(key, start, end);
    const headers: Record<string, string> = {
      "Content-Type": file.type,
      "Accept-Ranges": "bytes",
      "Cache-Control": "private, max-age=86400",
    };
    if (wanted) headers["Content-Range"] = `bytes ${start}-${end}/${file.size}`;
    return new Response(body, { status: wanted ? 206 : 200, headers });
  }

  /** Store a sound file, replacing older versions of it. */
  private keep(key: string, path: string, type: string, body: Uint8Array): void {
    const sql = this.ctx.storage.sql;
    this.ctx.storage.transactionSync(() => {
      for (const old of sql.exec<{ key: string }>("SELECT key FROM sounds WHERE path = ? OR key = ?", path, key).toArray()) {
        sql.exec("DELETE FROM sound_parts WHERE key = ?", old.key);
        sql.exec("DELETE FROM sounds WHERE key = ?", old.key);
      }
      for (let part = 0; part * PART < body.length; part++) {
        const bytes = body.slice(part * PART, (part + 1) * PART);
        sql.exec("INSERT INTO sound_parts (key, part, data) VALUES (?, ?, ?)", key, part, bytes.buffer);
      }
      sql.exec("INSERT INTO sounds (key, path, type, size) VALUES (?, ?, ?, ?)", key, path, type, body.length);
    });
    console.log(`kept a copy of ${key} (${(body.length / 1e6).toFixed(1)} MB)`);
  }

  private readSound(key: string, start: number, end: number): Uint8Array {
    const first = Math.floor(start / PART);
    const rows = this.ctx.storage.sql.exec<{ data: ArrayBuffer }>(
      "SELECT data FROM sound_parts WHERE key = ? AND part BETWEEN ? AND ? ORDER BY part", key, first, Math.floor(end / PART),
    ).toArray();
    const bytes = concat(rows.map((row) => new Uint8Array(row.data)));
    const offset = first * PART;
    return bytes.slice(start - offset, end - offset + 1);
  }
}

function linkEvent(online: boolean): string {
  return `event: link\ndata: ${JSON.stringify({ online })}\n\n`;
}

function concat(parts: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(parts.reduce((n, part) => n + part.length, 0));
  let at = 0;
  for (const part of parts) {
    out.set(part, at);
    at += part.length;
  }
  return out;
}

function toBase64(bytes: Uint8Array): string {
  let text = "";
  for (let i = 0; i < bytes.length; i += 0x8000) text += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(text);
}

function fromBase64(data: string): Uint8Array {
  const text = atob(data);
  const bytes = new Uint8Array(text.length);
  for (let i = 0; i < text.length; i++) bytes[i] = text.charCodeAt(i);
  return bytes;
}
