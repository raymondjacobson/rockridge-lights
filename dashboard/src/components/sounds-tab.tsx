import { Upload } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { clock, type Library, type PanelState, type Pick, pretty, type Track } from "@/lib/panel";

import { Tile } from "./looks-tab";

type Kind = "music" | "ambience";
const SHOW = "halloween_audio"; // the one show with sound (programs.py)

/** Songs and soundscapes (each comes with its own lights), and adding more. */
export function SoundsTab(props: { state: PanelState; library: Library; onPreview: (pick: Pick) => void; reload: () => void }) {
  const { state, library, onPreview, reload } = props;
  const [kind, setKind] = useState<Kind>("music");
  const [uploadKind, setUploadKind] = useState<Kind>("music");
  const [uploading, setUploading] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const P = state.preview;
  const L = state.lights;
  const tracks = library.tracks[kind];
  const previewing = (t: Track) => P.track === t.name || P.audio?.track === t.name;
  const onLights = (t: Track) => L.track === t.name || L.audio?.track === t.name;

  const upload = async (picked: File) => {
    const form = new FormData();
    form.set("kind", uploadKind);
    form.set("file", picked);
    setUploading(true);
    try {
      const res = await fetch("/api/upload", { method: "POST", body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || "The upload failed");
      toast(`Added ${pretty(data.name)}. It takes a minute to analyze before it plays.`);
      setTimeout(reload, 1500);
      setTimeout(reload, 30_000);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setUploading(false);
      if (file.current) file.current.value = "";
    }
  };

  return (
    <div className="space-y-3">
      <Tabs value={kind} onValueChange={(k) => setKind(k as Kind)}>
        <TabsList className="w-full sm:w-fit">
          <TabsTrigger value="music">Songs</TabsTrigger>
          <TabsTrigger value="ambience">Soundscapes</TabsTrigger>
        </TabsList>
      </Tabs>
      {tracks.length ? (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {tracks.map((t) => (
            <Tile
              key={t.name}
              title={t.title}
              about={t.scene ? `Lights: ${pretty(t.scene)}` : undefined}
              right={clock(t.duration)}
              previewing={previewing(t)}
              onLights={onLights(t)}
              onPick={() => onPreview({ program: SHOW, animation: null, track: t.name })}
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">None yet.</p>
      )}
      <div className="flex items-center gap-2 border-t pt-3">
        <Select value={uploadKind} onValueChange={(k) => setUploadKind(k as Kind)}>
          <SelectTrigger size="sm" className="w-36" aria-label="What kind of track to add">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="music">Song</SelectItem>
            <SelectItem value="ambience">Soundscape</SelectItem>
          </SelectContent>
        </Select>
        <input
          ref={file}
          type="file"
          accept="audio/*"
          className="hidden"
          aria-label="Audio file to add"
          onChange={(e) => {
            const picked = e.target.files?.[0];
            if (picked) void upload(picked);
          }}
        />
        <Button size="sm" variant="outline" disabled={uploading} onClick={() => file.current?.click()}>
          <Upload /> {uploading ? "Uploading..." : "Add a track"}
        </Button>
      </div>
    </div>
  );
}
