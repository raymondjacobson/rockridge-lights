import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { type Library, type PanelState, type Pick, recall, samePick, store } from "@/lib/panel";
import { cn } from "@/lib/utils";


/** One thing to preview: a tile that says if it's previewing or on the lights. */
export function Tile(props: { title: string; about?: string; right?: string; previewing: boolean; onLights: boolean; onPick: () => void }) {
  return (
    <button
      type="button"
      onClick={props.onPick}
      className={cn(
        "flex min-h-14 flex-col justify-center gap-0.5 rounded-lg border px-3 py-2 text-left text-sm transition-colors hover:bg-accent",
        props.previewing && "border-primary bg-accent",
      )}
    >
      <span className="flex items-center gap-2 font-medium">
        <span className="min-w-0 flex-1 truncate">{props.title}</span>
        {props.onLights && <Badge className="shrink-0">On lights</Badge>}
        {props.right && <span className="shrink-0 text-xs font-normal tabular-nums text-muted-foreground">{props.right}</span>}
      </span>
      {props.about && <span className="line-clamp-2 text-xs text-muted-foreground">{props.about}</span>}
    </button>
  );
}

/** The shows and their animations. A tap previews; the display's button sends it to the lights. */
export function LooksTab(props: { state: PanelState; library: Library; onPreview: (pick: Pick) => void }) {
  const { state, library, onPreview } = props;
  const [chosen, setChosen] = useState(() => recall("tab", library.programs[0].id));
  const program = library.programs.find((p) => p.id === chosen) ?? library.programs[0];
  const pick = (animation: string | null): Pick => ({ program: program.id, animation, track: null });

  return (
    <div className="space-y-3">
      <div className="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1 [scrollbar-width:none] lg:flex-wrap">
        {library.programs.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => {
              setChosen(p.id);
              store("tab", p.id);
            }}
            className={cn(
              "shrink-0 rounded-full border px-3 py-1.5 text-sm whitespace-nowrap transition-colors hover:bg-accent",
              p.id === program.id && "border-primary bg-primary text-primary-foreground hover:bg-primary",
            )}
          >
            {p.name}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {program.animations.length > 1 && (
          <Tile
            title="The whole show"
            about="Everything in this show, in turn."
            previewing={samePick(state.preview, pick(null))}
            onLights={samePick(state.lights, pick(null))}
            onPick={() => onPreview(pick(null))}
          />
        )}
        {program.animations.map((a) => (
          <Tile
            key={a.name}
            title={a.title}
            about={a.doc}
            previewing={samePick(state.preview, pick(a.name))}
            onLights={samePick(state.lights, pick(a.name)) || (program.animations.length === 1 && samePick(state.lights, pick(null)))}
            onPick={() => onPreview(pick(a.name))}
          />
        ))}
      </div>
    </div>
  );
}

