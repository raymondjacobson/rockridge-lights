import { type RefObject, useEffect, useMemo, useRef } from "react";

import { N } from "@/lib/panel";
import type { Frames, Where } from "@/lib/use-panel";

export interface HouseLayout {
  across: number; // lights along the top
  corner: string; // where light 1 is: bl, tl, tr or br
  direction: string; // cw or ccw
}

export const SIZES = {
  large: { width: 1000, pad: 28, dot: 3, glow: 9 },
  small: { width: 300, pad: 10, dot: 1.2, glow: 3.5 },
};

export function houseHeight({ across }: HouseLayout, width: number, pad: number) {
  return Math.round(((N - 2 * across) / 2) * ((width - 2 * pad) / across) + 2 * pad);
}

/** Where each light is on a canvas this wide, walking the strip around the house. */
function place({ across, corner, direction }: HouseLayout, width: number, pad: number) {
  const down = (N - 2 * across) / 2;
  const step = (width - 2 * pad) / across;
  const height = houseHeight({ across, corner, direction }, width, pad);
  // Walk clockwise from the bottom-left corner, then rotate/flip to match the strip.
  const loop: [number, number][] = [];
  for (let i = 0; i < down; i++) loop.push([pad, height - pad - i * step]);
  for (let i = 0; i < across; i++) loop.push([pad + i * step, pad]);
  for (let i = 0; i < down; i++) loop.push([width - pad, pad + i * step]);
  for (let i = 0; i < across; i++) loop.push([width - pad - i * step, height - pad]);
  const startAt = ({ bl: 0, tl: down, tr: down + across, br: 2 * down + across } as Record<string, number>)[corner] ?? 0;
  const points: [number, number][] = [];
  for (let i = 0; i < N; i++) {
    const k = direction === "cw" ? startAt + i : startAt - i;
    points.push(loop[((k % N) + N) % N]);
  }
  return { height, points };
}

/** The lights around the house, drawn live from a player's frames. */
export function House(props: { frames: RefObject<Frames>; where: Where; layout: HouseLayout; size?: keyof typeof SIZES; className?: string }) {
  const { frames, where, layout, size = "large", className } = props;
  const canvas = useRef<HTMLCanvasElement>(null);
  const { width, pad, dot, glow } = SIZES[size];
  const { height, points } = useMemo(() => place(layout, width, pad), [layout, width, pad]);

  useEffect(() => {
    const ctx = canvas.current?.getContext("2d");
    if (!ctx) return;
    let drawn = -1;
    let request = 0;
    const draw = () => {
      request = requestAnimationFrame(draw);
      const { pixels, seq } = frames.current[where];
      if (seq === drawn) return;
      drawn = seq;
      ctx.globalCompositeOperation = "source-over";
      ctx.fillStyle = "#050407";
      ctx.fillRect(0, 0, width, height);
      // A faint facade inside the lights.
      ctx.fillStyle = "#0c0a11";
      ctx.fillRect(pad, pad, width - 2 * pad, height - 2 * pad);
      ctx.fillStyle = "#100d16";
      const doorW = Math.min(70, width * 0.08);
      const doorH = (height - 2 * pad) * 0.55;
      ctx.fillRect(width / 2 - doorW / 2, height - pad - doorH, doorW, doorH);
      const winW = width * 0.13;
      const winH = (height - 2 * pad) * 0.32;
      const winY = pad + (height - 2 * pad) * 0.22;
      for (const x of [width * 0.2, width * 0.8 - winW]) ctx.fillRect(x, winY, winW, winH);

      ctx.globalCompositeOperation = "lighter";
      for (let i = 0; i < N; i++) {
        const [x, y] = points[i];
        if (pixels[i * 3] + pixels[i * 3 + 1] + pixels[i * 3 + 2] === 0) {
          ctx.fillStyle = "#1b1722";
          ctx.beginPath();
          ctx.arc(x, y, dot * 0.66, 0, 7);
          ctx.fill();
          continue;
        }
        // Screens show dim values darker than LEDs look, so lift them a little.
        const [r, g, b] = [0, 1, 2].map((c) => (255 * Math.pow(pixels[i * 3 + c] / 255, 0.5)) | 0);
        ctx.fillStyle = `rgba(${r},${g},${b},0.22)`;
        ctx.beginPath();
        ctx.arc(x, y, glow, 0, 7);
        ctx.fill();
        ctx.fillStyle = `rgb(${r},${g},${b})`;
        ctx.beginPath();
        ctx.arc(x, y, dot, 0, 7);
        ctx.fill();
      }
    };
    draw();
    return () => cancelAnimationFrame(request);
  }, [frames, where, width, height, pad, dot, glow, points]);

  return <canvas ref={canvas} width={width} height={height} className={className} aria-label={where === "lights" ? "What the real lights are showing" : "Preview of the lights around the house"} />;
}
