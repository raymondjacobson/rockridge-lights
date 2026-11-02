import { Bluetooth as BluetoothIcon, Search } from "lucide-react";
import { type ReactNode, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { api, type Bluetooth, type Library, type PanelState, type Speaker } from "@/lib/panel";
import { cn } from "@/lib/utils";

import type { HouseLayout } from "./house";

function report(e: Error) {
  toast.error(e.message);
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3 rounded-lg border p-3">
      <h3 className="text-sm font-medium">{title}</h3>
      {children}
    </section>
  );
}

/** A slider that only tells the panel when it's let go. */
function Setting(props: { label: string; value: number; min: number; max: number; step: number; format: (v: number) => string; onCommit: (v: number) => void }) {
  const [moving, setMoving] = useState<number | null>(null);
  const shown = moving ?? props.value;
  return (
    <label className="grid grid-cols-[6.5rem_1fr_2.75rem] items-center gap-2 text-sm">
      {props.label}
      <Slider
        aria-label={props.label}
        min={props.min}
        max={props.max}
        step={props.step}
        value={[shown]}
        onValueChange={([v]) => setMoving(v)}
        onValueCommit={([v]) => {
          props.onCommit(v);
          setMoving(null);
        }}
      />
      <span className="text-right text-xs tabular-nums text-muted-foreground">{props.format(shown)}</span>
    </label>
  );
}

function SpeakerRow({ speaker, onChange }: { speaker: Speaker; onChange: (b: Bluetooth) => void }) {
  const [busy, setBusy] = useState(false);
  return (
    <button
      type="button"
      disabled={busy}
      className="flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors hover:bg-accent disabled:opacity-60"
      onClick={() => {
        setBusy(true);
        api<Bluetooth>(`bluetooth/${speaker.connected ? "disconnect" : "connect"}`, { address: speaker.address })
          .then(onChange)
          .catch(report)
          .finally(() => setBusy(false));
      }}
    >
      <span className={cn("size-2 shrink-0 rounded-full", speaker.connected ? "bg-emerald-500" : "bg-muted-foreground/40")} />
      <span className="min-w-0 flex-1 truncate font-medium">{speaker.name}</span>
      <span className="shrink-0 text-xs text-muted-foreground">
        {busy ? (speaker.connected ? "Disconnecting..." : "Connecting...") : speaker.connected ? "Connected" : speaker.paired ? "Paired" : "Not paired"}
      </span>
    </button>
  );
}

/** The schedule, the sound, the speaker, and how the display maps to the house. */
export function SettingsTab(props: { state: PanelState; library: Library; layout: HouseLayout; onLayout: (layout: HouseLayout) => void }) {
  const { state, library, layout, onLayout } = props;
  const [bluetooth, setBluetooth] = useState<Bluetooth | null>(null);
  const [scanning, setScanning] = useState(false);

  const refresh = useCallback(() => {
    api<Bluetooth>("bluetooth").then(setBluetooth).catch(() => {});
  }, []);
  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 30_000);
    return () => clearInterval(timer);
  }, [refresh]);

  const speakers = bluetooth?.devices.filter((d) => d.audio || d.connected) ?? [];

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
      <Section title="Schedule">
        <label className="flex items-center justify-between gap-3 text-sm">
          <span>
            Evenings only
            <span className="block text-xs text-muted-foreground">
              {state.window[0]} to {state.window[1]}, following the sunset
            </span>
          </span>
          <Switch checked={state.schedule} onCheckedChange={(schedule) => api("settings", { schedule }).catch(report)} />
        </label>
      </Section>

      <Section title="Sound">
        <Setting label="Speaker volume" value={state.volume} min={0} max={100} step={5} format={(v) => `${v}%`} onCommit={(volume) => api("settings", { volume }).catch(report)} />
        <Setting label="Sound delay" value={state.latency} min={0} max={1} step={0.05} format={(v) => `${v.toFixed(2)} s`} onCommit={(latency) => api("settings", { latency }).catch(report)} />
        <p className="text-xs text-muted-foreground">Bluetooth speakers play a little late. If the lights run ahead of the sound, raise the delay.</p>
      </Section>

      <Section title="Bluetooth speaker">
        {speakers.length ? (
          <div className="space-y-2">
            {speakers.map((s) => <SpeakerRow key={s.address} speaker={s} onChange={setBluetooth} />)}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">No speakers yet. Put yours in pairing mode and look for it.</p>
        )}
        <Button
          size="sm"
          variant="outline"
          disabled={scanning}
          onClick={() => {
            setScanning(true);
            api<Bluetooth>("bluetooth/scan", {}).then(setBluetooth).catch(report).finally(() => setScanning(false));
          }}
        >
          {scanning ? <><BluetoothIcon /> Looking for 12 seconds...</> : <><Search /> Look for speakers</>}
        </Button>
      </Section>

      <Section title="Display layout">
        <Setting label="Lights across" value={layout.across} min={40} max={190} step={2} format={String} onCommit={(across) => onLayout({ ...layout, across })} />
        <div className="grid grid-cols-2 gap-2">
          <Select value={layout.corner} onValueChange={(corner) => onLayout({ ...layout, corner })}>
            <SelectTrigger size="sm" className="w-full" aria-label="Where light 1 is">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="bl">Starts bottom left</SelectItem>
              <SelectItem value="tl">Starts top left</SelectItem>
              <SelectItem value="tr">Starts top right</SelectItem>
              <SelectItem value="br">Starts bottom right</SelectItem>
            </SelectContent>
          </Select>
          <Select value={layout.direction} onValueChange={(direction) => onLayout({ ...layout, direction })}>
            <SelectTrigger size="sm" className="w-full" aria-label="Which way the strip runs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="cw">Clockwise</SelectItem>
              <SelectItem value="ccw">Counterclockwise</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Section>

      {library.credits.length > 0 && (
        <details className="rounded-lg border p-3 text-sm sm:col-span-2 lg:col-span-1 xl:col-span-2">
          <summary className="cursor-pointer font-medium">Sound credits</summary>
          <div className="mt-2 space-y-1 text-xs text-muted-foreground">
            {library.credits.map((c) => (
              <p key={c.source ?? c.file}>
                <a className="underline" href={c.source} target="_blank" rel="noopener noreferrer">{c.title || c.file}</a> by {c.author || "unknown"} ({c.license})
              </p>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
