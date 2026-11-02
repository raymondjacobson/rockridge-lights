import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { DisplayCard, warnings } from "@/components/display-card";
import type { HouseLayout } from "@/components/house";
import { Loading } from "@/components/loading";
import { LooksTab } from "@/components/looks-tab";
import { SettingsTab } from "@/components/settings-tab";
import { SoundsTab } from "@/components/sounds-tab";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, type PanelState, type Pick, recall, store } from "@/lib/panel";
import { usePanel, type Where } from "@/lib/use-panel";
import { cn } from "@/lib/utils";

function Login({ onDone }: { onDone: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const res = await fetch("/api/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) });
    const data = await res.json().catch(() => ({}));
    if (res.ok) onDone();
    else setError(data.error || "That didn't work.");
  };
  return (
    <div className="flex min-h-svh items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Rockridge Lights</CardTitle>
          <CardDescription>The panel password.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={submit}>
            <Input type="password" autoComplete="current-password" placeholder="Password" aria-label="Panel password" required value={password} onChange={(e) => setPassword(e.target.value)} />
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full">Log in</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function StatusBar(props: { state: PanelState | null; online: boolean; reconnecting: boolean }) {
  const { state, online, reconnecting } = props;
  const { resolvedTheme, setTheme } = useTheme();
  const lightsOn = Boolean(state?.lights.program);
  const asleep = lightsOn && state?.schedule && !state.show_time;
  const [tone, text] = !online
    ? ["bg-red-500", "Pi offline"]
    : reconnecting || !state
      ? ["bg-muted-foreground/40", "Connecting..."]
      : !lightsOn
        ? state.other_shows.length ? ["bg-amber-500", "Started by hand"] : ["bg-muted-foreground/40", "Lights off"]
        : asleep
          ? ["bg-sky-500", `Asleep until ${state.window[0]}`]
          : ["bg-emerald-500", "Lights on"];
  return (
    <header className="flex h-12 items-center gap-3 border-b px-4 lg:h-14">
      <h1 className="font-semibold">Rockridge Lights</h1>
      <span className="ml-auto flex items-center gap-1.5 text-xs whitespace-nowrap text-muted-foreground sm:text-sm">
        <span className={cn("inline-block size-2 shrink-0 rounded-full", tone)} />
        {text}
      </span>
      <Button variant="ghost" size="icon" aria-label="Toggle dark mode" onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}>
        {resolvedTheme === "dark" ? <Sun /> : <Moon />}
      </Button>
    </header>
  );
}

export default function App() {
  const panel = usePanel();
  const { state, library } = panel;
  const [view, setView] = useState<Where>("lights");
  const [tab, setTab] = useState(() => recall("panel-tab", "looks"));
  const [layout, setLayout] = useState<HouseLayout>(() => ({
    across: Number(recall("across", "140")),
    corner: recall("corner", "bl"),
    direction: recall("direction", "cw"),
  }));

  if (panel.needLogin) return <Login onDone={panel.loggedIn} />;

  const preview = (pick: Pick) => {
    setView("preview");
    api("play", { where: "preview", ...pick }).catch((e: Error) => toast.error(e.message));
  };
  const said = state ? warnings(state) : [];

  return (
    <div className="flex min-h-svh flex-col lg:h-svh">
      <StatusBar state={state} online={panel.online} reconnecting={panel.reconnecting} />
      {!panel.online && (
        <p className="border-b bg-amber-500/10 px-4 py-2 text-sm text-amber-700 dark:text-amber-300">
          The lights Pi isn't connected right now, so nothing here can change. It reconnects by itself once it's plugged in and on Wi-Fi.
        </p>
      )}
      {!state || !library ? (
        <Loading layout={layout} />
      ) : (
        <main className="mx-auto grid w-full max-w-7xl min-h-0 flex-1 grid-cols-1 content-start gap-3 lg:content-stretch px-3 pb-3 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] lg:gap-4 lg:p-4">
          {/* On a phone the display stays put while the lists scroll under it (if there's room). */}
          <div className="z-20 -mx-3 space-y-2 bg-background px-3 pt-3 max-lg:[@media(min-height:640px)]:sticky max-lg:[@media(min-height:640px)]:top-0 lg:mx-0 lg:overflow-y-auto lg:p-0">
            <DisplayCard
              state={state}
              library={library}
              frames={panel.frames}
              receivedAt={panel.receivedAt}
              layout={layout}
              view={view}
              onView={setView}
              soundHere={panel.soundHere}
              onSoundHere={panel.setSoundHere}
            />
            {said.map((text) => (
              <p key={text} className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-300">{text}</p>
            ))}
          </div>

          <Tabs
            value={tab}
            onValueChange={(t) => {
              setTab(t);
              store("panel-tab", t);
            }}
            className="min-h-0"
          >
            <TabsList className="w-full">
              <TabsTrigger value="looks">Looks</TabsTrigger>
              <TabsTrigger value="sounds">Sounds</TabsTrigger>
              <TabsTrigger value="settings">Settings</TabsTrigger>
            </TabsList>
            <TabsContent value="looks" className="min-h-0 lg:overflow-y-auto">
              <LooksTab state={state} library={library} onPreview={preview} />
            </TabsContent>
            <TabsContent value="sounds" className="min-h-0 lg:overflow-y-auto">
              <SoundsTab state={state} library={library} onPreview={preview} reload={() => void panel.loadLibrary()} />
            </TabsContent>
            <TabsContent value="settings" className="min-h-0 lg:overflow-y-auto">
              <SettingsTab
                state={state}
                library={library}
                layout={layout}
                onLayout={(next) => {
                  store("across", String(next.across));
                  store("corner", next.corner);
                  store("direction", next.direction);
                  setLayout(next);
                }}
              />
            </TabsContent>
          </Tabs>
        </main>
      )}
    </div>
  );
}
