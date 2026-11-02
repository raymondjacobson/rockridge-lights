/** The control panel's API (panel.py), the shapes it returns, and small helpers. */

export const N = 400; // lights.py NUM_PIXELS

export interface Pick {
  program: string | null;
  animation: string | null;
  track: string | null;
}

export interface Sounding {
  track: string;
  kind: string;
  title: string;
  started: number;
  duration: number;
  output: string;
  url: string;
  elapsed: number;
}

export interface Player extends Pick {
  playing: string | null;
  error: string | null;
  audio: Sounding | null;
}

export interface PanelState {
  schedule: boolean;
  brightness: number;
  volume: number;
  latency: number;
  lights: Player;
  preview: Player;
  has_leds: boolean;
  other_shows: string[];
  speaker: string | null;
  show_time: boolean;
  frog: { seconds_left: number } | null;
  window: [string, string];
}

export interface Animation {
  name: string;
  title: string;
  doc: string;
}

export interface Program {
  id: string;
  name: string;
  animations: Animation[];
}

export interface Track {
  name: string;
  title: string;
  duration: number | null;
  scene: string | null;
}

export interface Credit {
  file?: string;
  title?: string;
  author?: string;
  license?: string;
  source?: string;
}

export interface Library {
  programs: Program[];
  tracks: { music: Track[]; ambience: Track[] };
  credits: Credit[];
}

export interface Speaker {
  address: string;
  name: string;
  paired: boolean;
  connected: boolean;
  audio: boolean;
}

export interface Bluetooth {
  devices: Speaker[];
  speaker: string | null;
}

// On the internet (the rockridge-lights Worker) a call can also need a login (401) or find the Pi
// offline (503). usePanel listens for those.
export const heard: { login?: () => void; offline?: () => void } = {};

export async function api<T = { ok: boolean }>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api/${path}`, body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && data.login) heard.login?.();
  else if (res.status === 503 && data.offline) heard.offline?.();
  if (!res.ok) throw new Error(data.error || "Something went wrong");
  return data as T;
}

export const pretty = (name: string | null | undefined) => (name ?? "").replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

export const clock = (s: number | null | undefined) =>
  s == null ? "" : `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export function recall(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

export function store(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // fine: it just won't be remembered
  }
}

export const samePick = (a: Pick, b: Pick) => a.program === b.program && a.animation === b.animation && a.track === b.track;

/** [title, subtitle] for what a player is playing. */
export function describe(p: Player, library: Library | null): [string, string] {
  if (!p.program) return ["", ""];
  const program = library?.programs.find((x) => x.id === p.program);
  return [pretty(p.playing || p.animation) || program?.name || "", p.audio ? `♪ ${p.audio.title}` : program?.name ?? ""];
}
