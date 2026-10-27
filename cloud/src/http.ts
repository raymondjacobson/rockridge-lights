/**
 * Small pieces of the Worker that don't need Cloudflare's runtime: the panel's login cookie,
 * the Pi's device token, and byte ranges for sound files (browsers ask for these to seek).
 */

const encoder = new TextEncoder();

export const SESSION_COOKIE = "lights_session";
export const SESSION_DAYS = 90;

/** Compares in the same time wherever they differ, so the time taken doesn't give a secret away. */
function sameText(a: string, b: string): boolean {
  const x = encoder.encode(a), y = encoder.encode(b);
  if (x.length !== y.length) return false;
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];
  return diff === 0;
}

async function hmac(secret: string, text: string): Promise<string> {
  const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(`lights-session:${text}`));
  return btoa(String.fromCharCode(...new Uint8Array(sig))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function passwordMatches(given: unknown, password: string | undefined): boolean {
  return Boolean(password) && typeof given === "string" && sameText(given, password!);
}

/** A cookie value that says "logged in until `expires`", signed with the panel password. */
export async function sessionValue(password: string, expires = Date.now() + SESSION_DAYS * 86_400_000): Promise<string> {
  return `${expires}.${await hmac(password, String(expires))}`;
}

export async function sessionValid(request: Request, password: string | undefined, now = Date.now()): Promise<boolean> {
  if (!password) return false;
  const value = cookie(request, SESSION_COOKIE);
  const [expires, mac] = (value ?? "").split(".");
  if (!expires || !mac || Number(expires) < now) return false;
  return sameText(mac, await hmac(password, expires));
}

export function sessionCookie(value: string, secure: boolean): string {
  return `${SESSION_COOKIE}=${value}; Path=/; Max-Age=${SESSION_DAYS * 86_400}; HttpOnly; SameSite=Lax${secure ? "; Secure" : ""}`;
}

export function cookie(request: Request, name: string): string | null {
  for (const part of (request.headers.get("Cookie") ?? "").split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return rest.join("=");
  }
  return null;
}

export function bearerMatches(request: Request, secret: string | undefined): boolean {
  return Boolean(secret) && sameText(request.headers.get("Authorization") ?? "", `Bearer ${secret}`);
}

/**
 * The bytes a Range header asks for in a file of `size` bytes: [start, end] inclusive, null for
 * the whole file (no header, or one we don't handle, like several ranges), or "unsatisfiable".
 */
export function byteRange(header: string | null, size: number): [number, number] | null | "unsatisfiable" {
  const match = /^bytes=(\d*)-(\d*)$/.exec((header ?? "").trim());
  if (!match || (!match[1] && !match[2])) return null;
  let start: number, end: number;
  if (!match[1]) {
    const suffix = Number(match[2]);
    if (suffix === 0) return "unsatisfiable";
    start = Math.max(0, size - suffix);
    end = size - 1;
  } else {
    start = Number(match[1]);
    end = match[2] ? Math.min(Number(match[2]), size - 1) : size - 1;
  }
  if (start >= size || start > end) return "unsatisfiable";
  return [start, end];
}
