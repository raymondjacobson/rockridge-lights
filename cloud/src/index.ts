/**
 * rockridge-lights: the lights' control panel on the internet, at
 * https://rockridge-lights.monophonic.workers.dev.
 *
 * The page is web/index.html, the same file the Pi serves at home, deployed as a static asset.
 * Everything else goes to the one LightsLink Durable Object (link.ts), which passes it to the
 * Pi over the WebSocket the Pi keeps open to /device. The panel's API and sounds need the
 * panel password (a 90-day cookie from /api/login); the Pi needs its device token.
 *
 * Frog's brain (frog-brain, the Grim Reaper next door) reaches the lights through LightsControl,
 * over a service binding: a private Worker-to-Worker link with no URL of its own.
 */
import { WorkerEntrypoint } from "cloudflare:workers";

import { bearerMatches, passwordMatches, sessionCookie, sessionValid, sessionValue } from "./http";
import { type Env, LightsLink } from "./link";

export { LightsLink };

/** The panel's answer: {ok: true, ...}, or {error, refused: true} when the lights are off or
 * asleep, or {error, offline: true} when the Pi isn't connected. `status` is the HTTP status. */
export type LightsAnswer = { status: number; ok?: boolean; error?: string; refused?: boolean; offline?: boolean } & Record<string, unknown>;

/**
 * For Frog's brain: put a look on the lights for a minute (an animation or an effect made to
 * order), set off a moment over whatever's playing, go back to the show, or ask what's on and
 * what there is. The panel's /api/frog routes (panel.py) do the work; the lights keep their own
 * schedule and say no while they're off or asleep.
 */
export class LightsControl extends WorkerEntrypoint<Env> {
  look(body: { program?: string; animation?: string; effect?: unknown; seconds?: number }): Promise<LightsAnswer> {
    return this.#call("POST", "/api/frog/look", body);
  }

  moment(body: { kind: string; colors?: string[]; seconds?: number; envelope?: number[] }): Promise<LightsAnswer> {
    return this.#call("POST", "/api/frog/moment", body);
  }

  back(): Promise<LightsAnswer> {
    return this.#call("POST", "/api/frog/back", {});
  }

  status(): Promise<LightsAnswer> {
    return this.#call("GET", "/api/frog");
  }

  async #call(method: string, path: string, body?: unknown): Promise<LightsAnswer> {
    const link = this.env.LightsLink.get(this.env.LightsLink.idFromName("home"));
    const response = await link.fetch(new Request(`https://lights.internal${path}`, {
      method,
      ...(body === undefined ? {} : { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
    }));
    const data = await response.json<Record<string, unknown>>().catch(() => ({ error: `the panel answered ${response.status}` }));
    return { ...data, status: response.status };
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const link = () => env.LightsLink.get(env.LightsLink.idFromName("home"));
    if (url.pathname === "/health") return new Response("ok");

    if (url.pathname === "/api/login" && request.method === "POST") {
      const { password } = await request.json<{ password?: unknown }>().catch(() => ({ password: undefined }));
      if (!env.LIGHTS_PASSWORD) return Response.json({ error: "No panel password is set up yet." }, { status: 401 });
      if (!passwordMatches(password, env.LIGHTS_PASSWORD)) {
        await new Promise((resolve) => setTimeout(resolve, 500)); // slow down guessing
        return Response.json({ error: "That's not the password." }, { status: 401 });
      }
      const value = await sessionValue(env.LIGHTS_PASSWORD);
      return Response.json({ ok: true }, { headers: { "Set-Cookie": sessionCookie(value, url.protocol === "https:") } });
    }

    if (url.pathname === "/device") {
      if (!bearerMatches(request, env.LIGHTS_DEVICE_TOKEN)) return new Response("unauthorized", { status: 401 });
      return link().fetch(request);
    }

    if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/sounds/")) {
      if (!(await sessionValid(request, env.LIGHTS_PASSWORD))) {
        return Response.json({ error: "Log in first.", login: true }, { status: 401 });
      }
      return link().fetch(request);
    }

    return new Response("not found", { status: 404 });
  },
} satisfies ExportedHandler<Env>;
