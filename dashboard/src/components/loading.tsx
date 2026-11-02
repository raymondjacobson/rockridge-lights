import { Card } from "@/components/ui/card";

import { type HouseLayout, houseHeight, SIZES } from "./house";

function Bar({ className }: { className: string }) {
  return <div className={`rounded-md bg-muted motion-safe:animate-pulse ${className}`} />;
}

/** The panel's shape while it waits for the Pi: an unlit house, its lights slowly coming and going. */
export function Loading({ layout }: { layout: HouseLayout }) {
  const { width, pad } = SIZES.large;
  const height = houseHeight(layout, width, pad);
  const lights = { x: pad, y: pad, width: width - 2 * pad, height: height - 2 * pad, fill: "none", stroke: "#f5cf8e", strokeWidth: 7, strokeLinecap: "round" as const };
  return (
    <main aria-busy="true" aria-label="Loading the lights" className="mx-auto grid w-full max-w-7xl min-h-0 flex-1 grid-cols-1 content-start gap-3 px-3 pb-3 pt-3 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] lg:content-stretch lg:gap-4 lg:p-4">
      <div>
        <Card className="gap-2 p-3">
          <div className="flex items-center justify-between">
            <Bar className="h-8 w-36" />
            <Bar className="h-8 w-24" />
          </div>
          <svg viewBox={`0 0 ${width} ${height}`} className="block w-full rounded-lg bg-[#050407]" aria-hidden>
            <rect {...lights} strokeDasharray="0 32" className="motion-safe:animate-pulse" />
            <rect {...lights} strokeDasharray="0 32" strokeDashoffset={16} opacity={0.45} className="motion-safe:animate-pulse [animation-delay:1s]" />
          </svg>
          <Bar className="h-5 w-40" />
          <Bar className="h-4 w-full" />
        </Card>
      </div>
      <div className="space-y-3">
        <Bar className="h-8 w-full" />
        <div className="flex gap-1.5 overflow-hidden">
          <Bar className="h-8 w-20 shrink-0 rounded-full" />
          <Bar className="h-8 w-40 shrink-0 rounded-full" />
          <Bar className="h-8 w-32 shrink-0 rounded-full" />
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {[0, 1, 2, 3].map((i) => <Bar key={i} className="h-16" />)}
        </div>
      </div>
    </main>
  );
}
