import { Power, Square, Sun, Volume2, VolumeX } from "lucide-react";
import { type RefObject, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, clock, describe, type Library, type PanelState, type Pick, recall, samePick, store } from "@/lib/panel";
import type { Frames, Where } from "@/lib/use-panel";

import { House, type HouseLayout } from "./house";

const TAP = "max-lg:h-9 max-lg:px-3"; // bigger for fingers
const EVENING: Pick = { program: "evening", animation: null, track: null };

function report(e: Error) {
  toast.error(e.message);
}

/** How far the preview's track has got. */
function Progress(props: { state: PanelState; receivedAt: RefObject<number> }) {
  const audio = props.state.preview.audio;
  const [, tick] = useState(0);
  useEffect(() => {
    if (!audio) return;
    const timer = setInterval(() => tick((n) => n + 1), 500);
    return () => clearInterval(timer);
  }, [audio]);
  if (!audio) return null;
  const t = Math.min(audio.duration, audio.elapsed + (performance.now() - props.receivedAt.current) / 1000);
  return <span className="shrink-0 text-xs tabular-nums text-muted-foreground">{clock(t)} / {clock(audio.duration)}</span>;
}

/**
 * The display: the real lights or the preview, what's playing, turning them on or off, sending the
 * preview to them, and the brightness. On a phone it stays at the top while the lists scroll.
 */
export function DisplayCard(props: {
  state: PanelState;
  library: Library | null;
  frames: RefObject<Frames>;
  receivedAt: RefObject<number>;
  layout: HouseLayout;
  view: Where;
  onView: (view: Where) => void;
  soundHere: boolean;
  onSoundHere: (on: boolean) => void;
}) {
  const { state, library, frames, layout, view, onView } = props;
  const L = state.lights;
  const P = state.preview;
  const lightsOn = Boolean(L.program);
  const [brightness, setBrightness] = useState<number | null>(null);
  const shown = brightness ?? state.brightness;

  useEffect(() => {
    if (L.program) store("last-lights", JSON.stringify({ program: L.program, animation: L.animation, track: L.track }));
  }, [L.program, L.animation, L.track]);

  const turnOn = () => {
    let pick = EVENING;
    try {
      pick = JSON.parse(recall("last-lights", "")) as Pick;
    } catch {
      // nothing remembered: the evening glow
    }
    api("play", { where: "lights", ...pick }).catch(report);
  };
  const same = Boolean(P.program) && samePick(P, L);
  const send = () => {
    api("play", { where: "lights", program: P.program, animation: P.animation, track: P.track })
      .then(() => {
        toast(`On the lights: ${describe({ ...P, playing: null }, library)[0]}`);
        onView("lights");
      })
      .catch(report);
  };

  const [title, sub] = view === "lights"
    ? lightsOn ? describe(L, library) : [state.other_shows.join(", ") || "Off", state.other_shows.length ? "Started by hand, outside the panel" : "Pick a look to preview, then send it here"]
    : P.program ? describe(P, library) : ["Nothing previewing", "Pick a look to try it here first"];

  return (
    <Card className="gap-2 p-3">
      <div className="flex items-center gap-2">
        <Tabs value={view} onValueChange={(v) => onView(v as Where)}>
          <TabsList>
            <TabsTrigger value="lights">Lights</TabsTrigger>
            <TabsTrigger value="preview">Preview</TabsTrigger>
          </TabsList>
        </Tabs>
        <div className="ml-auto flex items-center gap-1.5">
          {view === "lights" ? (
            lightsOn ? (
              <Button size="sm" variant="outline" className={TAP} onClick={() => api("stop", { where: "lights" }).catch(report)}>
                <Power /> Turn off
              </Button>
            ) : (
              <Button size="sm" className={TAP} disabled={!state.has_leds} onClick={turnOn}>
                <Power /> Turn on
              </Button>
            )
          ) : (
            <>
              {P.program === "halloween_audio" && (
                <Button size="icon-sm" variant="ghost" className="max-lg:size-9" aria-label={props.soundHere ? "Turn the preview's sound off" : "Turn the preview's sound on"} onClick={() => props.onSoundHere(!props.soundHere)}>
                  {props.soundHere ? <Volume2 /> : <VolumeX />}
                </Button>
              )}
              <Button size="icon-sm" variant="ghost" className="max-lg:size-9" aria-label="Stop the preview" disabled={!P.program} onClick={() => api("stop", { where: "preview" }).catch(report)}>
                <Square />
              </Button>
              <Button size="sm" className={TAP} disabled={!state.has_leds || !P.program || same} onClick={send}>
                {same ? "On the lights" : "Send to lights"}
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="relative">
        <House frames={frames} where={view} layout={layout} className="block w-full rounded-lg bg-[#050407]" />
        {view === "preview" && (
          <button
            type="button"
            className="absolute right-2 bottom-2 w-1/4 overflow-hidden rounded-md border border-white/20"
            aria-label="Show the real lights"
            onClick={() => onView("lights")}
          >
            <House frames={frames} where="lights" layout={layout} size="small" className="block w-full bg-[#050407]" />
          </button>
        )}
      </div>

      <div className="flex min-h-5 items-baseline gap-2 text-sm">
        <span className="truncate font-medium">{title}</span>
        <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
          {view === "lights" && state.frog ? `The Grim Reaper's pick, ${Math.ceil(state.frog.seconds_left)} s left` : sub}
        </span>
        {view === "preview" && <Progress state={state} receivedAt={props.receivedAt} />}
      </div>

      <label className="flex items-center gap-3 text-sm">
        <Sun className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        <Slider
          aria-label="Brightness"
          min={0.05}
          max={1}
          step={0.05}
          value={[shown]}
          onValueChange={([v]) => setBrightness(v)}
          onValueCommit={([v]) => {
            api("settings", { brightness: v }).catch(report).finally(() => setBrightness(null));
          }}
        />
        <span className="w-9 text-right text-xs tabular-nums text-muted-foreground">{Math.round(shown * 100)}%</span>
      </label>
    </Card>
  );
}

/** Anything about the lights that needs saying. */
export function warnings(state: PanelState): string[] {
  const L = state.lights;
  const lightsOn = Boolean(L.program);
  const said: string[] = [];
  if (!lightsOn && state.other_shows.length) said.push(`${state.other_shows.join(", ")} was started by hand, so the panel can't show it. Sending something to the lights replaces it.`);
  if (lightsOn && state.schedule && !state.show_time) said.push(`It's outside the schedule, so the lights stay dark until ${state.window[0]}. Turn the schedule off in Settings to play now.`);
  if (lightsOn && L.audio && !state.speaker) said.push("No Bluetooth speaker is connected, so the sound isn't going anywhere. Turn the speaker on, or connect it in Settings.");
  if (L.error) said.push(`The show on the lights stopped with an error: ${L.error}`);
  if (state.preview.error) said.push(`The preview stopped with an error: ${state.preview.error}`);
  if (!state.has_leds) said.push("This computer has no lights, so it only previews.");
  return said;
}

