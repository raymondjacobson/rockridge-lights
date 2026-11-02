import { useCallback, useEffect, useRef, useState } from "react";

import { api, heard, type Library, N, type PanelState, recall, store } from "./panel";

// Phones only let a page play sound that starts from a tap, so the player gets going on the first one.
const SILENCE = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=";

export type Where = "lights" | "preview";
export type Frames = Record<Where, { pixels: Uint8Array; seq: number }>;

/** The panel's live state, the two players' frames, and the preview's sound in this browser. */
export function usePanel() {
  const [state, setState] = useState<PanelState | null>(null);
  const [library, setLibrary] = useState<Library | null>(null);
  const [needLogin, setNeedLogin] = useState(false);
  const [online, setOnline] = useState(true);
  const [reconnecting, setReconnecting] = useState(false);
  const [session, setSession] = useState(0); // bumped to start over: after logging in, or the Pi coming back
  const [soundHere, setSoundHere] = useState(() => recall("sound", "on") !== "off");
  const frames = useRef<Frames>({
    lights: { pixels: new Uint8Array(N * 3), seq: 0 },
    preview: { pixels: new Uint8Array(N * 3), seq: 0 },
  });
  const receivedAt = useRef(0);
  const player = useRef<HTMLAudioElement | null>(null);
  const wasOnline = useRef(true);
  const latest = useRef<PanelState | null>(null);

  const showOnline = useCallback((now: boolean) => {
    setOnline(now);
    if (now && !wasOnline.current) setSession((s) => s + 1); // back: catch up on anything that changed
    wasOnline.current = now;
  }, []);

  useEffect(() => {
    heard.login = () => setNeedLogin(true);
    heard.offline = () => showOnline(false);
  }, [showOnline]);

  const loadLibrary = useCallback(() => api<Library>("library").then(setLibrary), []);

  // The shows first: on the internet that's also how the page finds out it needs a login.
  useEffect(() => {
    let events: EventSource | null = null;
    let over = false;
    loadLibrary().catch(() => {}).finally(() => {
      if (over) return;
      events = new EventSource("/api/stream");
      events.addEventListener("link", (e) => showOnline(JSON.parse(e.data).online));
      events.addEventListener("state", (e) => {
        setReconnecting(false);
        receivedAt.current = performance.now();
        latest.current = JSON.parse(e.data);
        setState(latest.current);
      });
      for (const where of ["lights", "preview"] as const) {
        events.addEventListener(where, (e) => {
          const bin = atob(e.data);
          const frame = frames.current[where];
          for (let i = 0; i < bin.length; i++) frame.pixels[i] = bin.charCodeAt(i);
          frame.seq++;
        });
      }
      events.onerror = () => setReconnecting(true);
    });
    return () => {
      over = true;
      events?.close();
    };
  }, [session, loadLibrary, showOnline]);

  // A first try can fail (the Pi just restarted, or was offline): keep trying until there's a list.
  useEffect(() => {
    if (library || needLogin) return;
    const timer = setInterval(() => loadLibrary().catch(() => {}), 5000);
    return () => clearInterval(timer);
  }, [library, needLogin, loadLibrary]);

  // Sound in the browser: follows the preview's track
  const syncSound = useCallback(() => {
    const audio = player.current;
    if (!audio) return;
    const a = latest.current?.preview.audio;
    if (!soundHere || !a || a.output !== "browser") {
      if (!audio.paused) audio.pause();
      return;
    }
    const url = new URL(a.url, location.href).href;
    if (audio.src !== url) {
      audio.src = url; // loadedmetadata calls back here
      return;
    }
    if (audio.readyState < 1) return;
    const expected = a.elapsed + (performance.now() - receivedAt.current) / 1000;
    if (expected >= a.duration) {
      audio.pause();
      return;
    }
    if (Math.abs(audio.currentTime - expected) > 0.3) audio.currentTime = expected;
    if (audio.paused) audio.play().catch(() => {});
  }, [soundHere]);

  useEffect(() => {
    const audio = new Audio();
    audio.preload = "auto";
    player.current = audio;
    const unlock = () => {
      if (!audio.src) {
        audio.src = SILENCE;
        audio.play().catch(() => {});
      }
    };
    document.addEventListener("pointerdown", unlock, { capture: true, once: true });
    return () => {
      document.removeEventListener("pointerdown", unlock, { capture: true });
      audio.pause();
      player.current = null;
    };
  }, []);

  useEffect(() => {
    const audio = player.current;
    audio?.addEventListener("loadedmetadata", syncSound);
    const timer = setInterval(syncSound, 2000);
    syncSound();
    return () => {
      audio?.removeEventListener("loadedmetadata", syncSound);
      clearInterval(timer);
    };
  }, [syncSound, state?.preview.audio?.track]);

  return {
    state,
    library,
    needLogin,
    online,
    reconnecting,
    frames,
    receivedAt,
    soundHere,
    setSoundHere: (on: boolean) => {
      store("sound", on ? "on" : "off");
      setSoundHere(on);
    },
    loadLibrary,
    loggedIn: () => {
      setNeedLogin(false);
      setSession((s) => s + 1);
    },
  };
}
