/**
 * rockridge-lights: the lights' control panel on the internet, at
 * https://rockridge-lights.monophonic.workers.dev.
 *
 * The page is web/index.html, the same file the Pi serves at home, deployed as a static asset.
 * Everything else goes to the one LightsLink Durable Object (link.ts), which passes it to the
 * Pi over the WebSocket the Pi keeps open to /device. The panel's API and sounds need the
 * panel password (a 90-day cookie from /api/login); the Pi needs its device token.
 */
import { bearerMatches, passwordMatches, sessionCookie, sessionValid, sessionValue } from "./http";
import { type Env, LightsLink } from "./link";

export { LightsLink };

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
