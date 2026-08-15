import { memo } from "react";
import clsx from "clsx";

/**
 * Lotus line-art ornaments — the app's decorative vocabulary.
 *
 * Everything here is inline SVG stroked with `currentColor`, never an image
 * file. Three reasons, in order of how much they matter:
 *
 * 1. **Theme.** The app flips between a near-black ground and a paper-cream one.
 *    A PNG of gold linework looks right on exactly one of them. `currentColor`
 *    means the ornament is whatever colour its container says, so one drawing
 *    serves both themes and any future one.
 * 2. **Offline.** The app ships as a packaged desktop build with no network, so
 *    a decorative asset that has to be fetched is a decorative asset that
 *    sometimes is not there.
 * 3. **Scale.** These are drawn at hero size (500px+) and at badge size (24px)
 *    from the same paths, with no second asset and no blur.
 *
 * The motif is the Vietnamese lotus: outline petals with fine parallel veining,
 * lily pads, and a *seigaha* interlocking-circle field for texture. Ornament is
 * always `aria-hidden` and never carries meaning — a screen reader hears the
 * content, and someone with patterns turned down loses nothing but decoration.
 */

/** Angles, in degrees, of the petals in each ring of a bloom. */
const OUTER_PETALS = [0, 40, 80, 120, 160, 200, 240, 280, 320];
const INNER_PETALS = [20, 70, 130, 180, 230, 290, 340];

/** One petal, pointing up from the flower's centre at (100, 118). */
const PETAL =
  "M100 118 C 74 96 60 62 72 34 C 80 14 92 8 100 6 C 108 8 120 14 128 34 C 140 62 126 96 100 118 Z";

/** The fine parallel lines that give a petal its ribbed look. */
const PETAL_VEINS = [
  "M100 114 C 96 88 94 50 100 12",
  "M100 114 C 88 90 80 56 86 24",
  "M100 114 C 112 90 120 56 114 24",
];

function Petal({ angle, scale = 1 }: { angle: number; scale?: number }) {
  return (
    <g transform={`rotate(${angle} 100 118) translate(100 118) scale(${scale}) translate(-100 -118)`}>
      <path d={PETAL} />
      {PETAL_VEINS.map((vein) => (
        <path key={vein} d={vein} strokeWidth={0.6} opacity={0.65} />
      ))}
    </g>
  );
}

/**
 * A full lotus bloom seen face-on: two rings of petals around a seed pod.
 *
 * `detail` drops the inner ring and the veining, which is what keeps the mark
 * readable when it is drawn small — at 32px the full drawing collapses into a
 * grey smudge, so the small version is a different drawing, not a scaled one.
 */
export const LotusBloom = memo(function LotusBloom({
  className,
  detail = "full",
}: {
  className?: string;
  detail?: "full" | "simple";
}) {
  return (
    <svg
      viewBox="0 0 200 200"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.1}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {OUTER_PETALS.map((angle) => (
        <Petal key={angle} angle={angle} />
      ))}
      {detail === "full" &&
        INNER_PETALS.map((angle) => <Petal key={`i${angle}`} angle={angle} scale={0.58} />)}

      {/* Seed pod: the flat-topped receptacle with its ring of seeds. */}
      <ellipse cx={100} cy={112} rx={19} ry={12} strokeWidth={1.3} />
      {detail === "full" &&
        [-12, -6, 0, 6, 12].map((offset) => (
          <circle key={offset} cx={100 + offset} cy={110 + Math.abs(offset) * 0.18} r={2.1} />
        ))}
    </svg>
  );
});

/** A lily pad: one rounded leaf with a notch and radiating veins. */
export const LotusLeaf = memo(function LotusLeaf({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 200 200"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {/* The notch at the bottom is what reads as "lily pad" rather than "circle". */}
      <path d="M100 100 L104 186 A86 86 0 1 1 96 186 Z" />
      {[0, 30, 60, 90, 120, 150, 210, 240, 270, 300, 330].map((angle) => (
        <path
          key={angle}
          d="M100 100 L100 16"
          strokeWidth={0.7}
          opacity={0.6}
          transform={`rotate(${angle} 100 100)`}
        />
      ))}
      <circle cx={100} cy={100} r={54} strokeWidth={0.6} opacity={0.4} />
    </svg>
  );
});

/** A closed bud on its stem — the quieter mark, for tight corners. */
export const LotusBud = memo(function LotusBud({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 120 200"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M60 120 C 34 96 30 52 60 12 C 90 52 86 96 60 120 Z" />
      <path d="M60 118 C 46 96 44 56 60 20" strokeWidth={0.6} opacity={0.7} />
      <path d="M60 118 C 74 96 76 56 60 20" strokeWidth={0.6} opacity={0.7} />
      <path d="M60 120 C 44 108 34 92 30 70 C 44 82 54 100 60 120 Z" opacity={0.85} />
      <path d="M60 120 C 76 108 86 92 90 70 C 76 82 66 100 60 120 Z" opacity={0.85} />
      <path d="M60 120 L60 192" strokeWidth={1.4} />
    </svg>
  );
});

/**
 * Seigaiha — interlocking circles, the texture in the reference artwork.
 *
 * Rendered as an SVG `<pattern>` rather than a CSS background so it inherits
 * `currentColor` like everything else here.
 */
export const SeigaihaField = memo(function SeigaihaField({
  className,
  id = "seigaiha",
}: {
  className?: string;
  id?: string;
}) {
  return (
    <svg aria-hidden="true" className={className}>
      <defs>
        <pattern id={id} width={40} height={20} patternUnits="userSpaceOnUse">
          {[0, 40].map((x) => (
            <g key={x} transform={`translate(${x - 20} 0)`}>
              {[20, 15, 10, 5].map((r) => (
                <circle
                  key={r}
                  cx={20}
                  cy={20}
                  r={r}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={0.7}
                />
              ))}
            </g>
          ))}
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  );
});

/**
 * The ambient layer behind the whole app.
 *
 * Sits at the very back, drifts slowly, and is deliberately faint enough that
 * you notice it only once you stop reading — decoration that competes with the
 * content is decoration that has to go. `pointer-events-none` throughout so
 * nothing here can ever intercept a click.
 */
export function AmbientOrnament() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden text-gold"
    >
      <SeigaihaField className="absolute inset-0 h-full w-full opacity-[0.035]" />
      <LotusLeaf className="animate-drift-slow absolute -left-40 -top-32 h-[34rem] w-[34rem] opacity-[0.07]" />
      <LotusBloom className="animate-drift-slower absolute -right-48 top-1/4 h-[42rem] w-[42rem] opacity-[0.055]" />
      <LotusBud className="animate-drift-slow absolute -bottom-24 left-1/3 h-[26rem] w-[16rem] opacity-[0.05]" />
      {/* A warm pool of light under the ornament stops the corners going flat. */}
      <div className="absolute -left-1/4 top-0 h-[42rem] w-[42rem] rounded-full bg-gold/[0.05] blur-[120px]" />
      <div className="absolute -right-1/4 bottom-0 h-[38rem] w-[38rem] rounded-full bg-accent/[0.05] blur-[120px]" />
    </div>
  );
}

/**
 * A watermark tucked into a card's corner.
 *
 * Clipped by the card's own `overflow-hidden`, so most of the flower is off the
 * edge and only a suggestion of linework shows — the "hoa văn ẩn" idea: present
 * when looked for, invisible when reading.
 */
export function CardOrnament({
  motif = "bloom",
  className,
}: {
  motif?: "bloom" | "leaf" | "bud";
  className?: string;
}) {
  const Motif = motif === "leaf" ? LotusLeaf : motif === "bud" ? LotusBud : LotusBloom;
  return (
    <Motif
      className={clsx(
        // Negative z-index, which only behaves because `Card` isolates itself:
        // above the card's background, below the card's content.
        "pointer-events-none absolute -right-10 -top-12 -z-10 h-40 w-40 text-gold opacity-[0.10] transition-[opacity,transform] duration-500 group-hover:scale-110 group-hover:opacity-[0.20]",
        className
      )}
    />
  );
}
