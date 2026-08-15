import { memo, useId, type ReactNode } from "react";
import clsx from "clsx";

/**
 * The app's ornamental vocabulary: classical Chinese motifs as inline SVG.
 *
 * Everything is stroked with `currentColor` and never loaded as an image. The
 * app flips between a near-black ground and a paper-cream one, so a raster of
 * gold linework would be right on exactly one of them; it also ships as a
 * packaged offline build, where an asset that must be fetched is an asset that
 * is sometimes missing.
 *
 * ## The rule that keeps this from becoming a mess
 *
 * Ornament turns into noise the moment two motifs compete, so each one here has
 * **exactly one role** and is used nowhere else:
 *
 * | Role                      | Motif                        | Why that one              |
 * | ------------------------- | ---------------------------- | ------------------------- |
 * | Ground, whole page        | 冰裂 băng liệt               | No readable repeat        |
 * | Ground, side panel        | 步步锦 bộ bộ cẩm             | Straight lines, vertical  |
 * | Ground, wide surface      | 七宝 thất bảo / 龟背 quy bối | Quiet, even texture       |
 * | Edge band                 | 回纹 hồi văn                 | Built to be cut           |
 * | Section divider           | 莲瓣 liên biện               | Keeps the lotus identity  |
 * | Progress /水 band         | 水波 thủy ba                 | Reads as movement         |
 * | Card corner               | 如意 như ý                   | A corner by construction  |
 * | One focal point per screen| 宝相花 bảo tương hoa         | Symmetric, never cropped  |
 * | Celebration only          | 海水江崖 + 祥云              | Imperial, so kept rare    |
 * | Exam screens only         | 夔龙 quỳ long                | Strongest mark in the set |
 *
 * ## Two construction rules
 *
 * 1. **A tiling pattern must be seamless.** Every arc leaving a tile edge is
 *    continued by the neighbouring tile, so the field never shows the flat cut
 *    that a half-drawn circle leaves behind.
 * 2. **A centred motif is never clipped.** Radially symmetric ornament — a
 *    lotus, a 宝相花 — is ruined by cropping, because the eye reads the missing
 *    half as damage. Anything that bleeds off an edge is a band or a corner
 *    piece, both of which are *designed* to be cut.
 *
 * All ornament is `aria-hidden`; nothing here carries meaning.
 */

/* ==========================================================================
   Tiling grounds
   ========================================================================== */

/** Wraps one `<pattern>` tile into a full-bleed field with a unique id. */
function PatternField({
  className,
  tile,
  width,
  height,
  opacity,
  rotate,
}: {
  className?: string;
  tile: ReactNode;
  width: number;
  height: number;
  opacity?: number;
  /**
   * Turns the whole field. A running band such as 回纹 is drawn horizontally;
   * put that same tile in a narrow vertical strip without rotating it and all
   * you see is a lengthwise slice of the meander, which reads as noise.
   */
  rotate?: number;
}) {
  // Two fields of the same motif on one page would otherwise share an id and
  // the second would render the first's tile.
  const id = useId().replace(/:/g, "");
  return (
    <svg aria-hidden="true" className={className} style={{ opacity }}>
      <defs>
        <pattern
          id={id}
          width={width}
          height={height}
          patternUnits="userSpaceOnUse"
          patternTransform={rotate ? `rotate(${rotate})` : undefined}
        >
          {tile}
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  );
}

/**
 * 七宝纹 — interlocking circles.
 *
 * Circles sit on the corners *and* the centre of a 40×40 tile. That is what
 * makes it seamless: the quarter of the corner circle that this tile clips away
 * is drawn by the three tiles that share the corner, so the ring closes across
 * the seam instead of stopping dead at it.
 */
export const ThatBaoField = memo(function ThatBaoField({
  className,
  opacity,
}: {
  className?: string;
  opacity?: number;
}) {
  const rings = [20, 13.5, 7];
  const centres = [
    [0, 0],
    [40, 0],
    [0, 40],
    [40, 40],
    [20, 20],
  ];
  return (
    <PatternField
      className={className}
      opacity={opacity}
      width={40}
      height={40}
      tile={
        <g fill="none" stroke="currentColor" strokeWidth={0.7}>
          {centres.map(([cx, cy]) =>
            rings.map((r) => <circle key={`${cx}-${cy}-${r}`} cx={cx} cy={cy} r={r} />)
          )}
        </g>
      }
    />
  );
});

/** 龟背纹 — tortoise-shell hexagons. The quietest ground in the set. */
export const QuyBoiField = memo(function QuyBoiField({
  className,
  opacity,
}: {
  className?: string;
  opacity?: number;
}) {
  // Flat-top hexagon of side 12, drawn around its own centre.
  const hex = "M12 0 L6 10.392 L-6 10.392 L-12 0 L-6 -10.392 L6 -10.392 Z";
  // A flat-top grid steps 1.5·s across and s·√3 down, with every other column
  // dropped by half a row. That makes 36 × 20.784 the smallest rectangle the
  // grid repeats on; the centres outside it are the neighbours' hexagons
  // reaching in, and drawing them is what closes the shape across the seam.
  const centres = [
    [0, 0],
    [36, 0],
    [0, 20.784],
    [36, 20.784],
    [18, 10.392],
    [18, -10.392],
    [-18, 10.392],
    [54, 10.392],
  ];
  return (
    <PatternField
      className={className}
      opacity={opacity}
      width={36}
      height={20.784}
      tile={
        <g fill="none" stroke="currentColor" strokeWidth={0.7}>
          {centres.map(([x, y]) => (
            <path key={`${x}-${y}`} d={hex} transform={`translate(${x} ${y})`} />
          ))}
        </g>
      }
    />
  );
});

/**
 * 步步锦 — the stepped lattice of a window frame.
 *
 * Straight lines only, which is why it suits a narrow vertical panel: curves in
 * a 288px column read as clutter, a lattice reads as joinery.
 */
export const BoBoCamField = memo(function BoBoCamField({
  className,
  opacity,
}: {
  className?: string;
  opacity?: number;
}) {
  return (
    <PatternField
      className={className}
      opacity={opacity}
      width={48}
      height={48}
      tile={
        <g fill="none" stroke="currentColor" strokeWidth={0.75}>
          {/* Frame: shared with the neighbouring tiles, so the grid is unbroken. */}
          <path d="M0 0 H48 M0 48 H48 M0 0 V48 M48 0 V48" />
          {/* The stepped return that gives the motif its name. */}
          <path d="M10 0 V14 H0 M38 0 V14 H48 M10 48 V34 H0 M38 48 V34 H48" />
          <rect x={18} y={18} width={12} height={12} />
        </g>
      }
    />
  );
});

/**
 * 冰裂纹 — cracked ice.
 *
 * The ground for the whole page, chosen because the eye cannot find the repeat:
 * a regular grid behind a whole application starts to read as a table. The tile
 * is seamless because every crack meets an edge at a coordinate that is
 * mirrored on the opposite edge.
 */
export const BangLietField = memo(function BangLietField({
  className,
  opacity,
}: {
  className?: string;
  opacity?: number;
}) {
  return (
    <PatternField
      className={className}
      opacity={opacity}
      width={120}
      height={120}
      tile={
        <g fill="none" stroke="currentColor" strokeWidth={0.7} strokeLinecap="round">
          {/* Every crossing has a partner at the same coordinate on the
              opposite edge — top x∈{28,74} ↔ bottom x∈{28,74}, left y∈{44,108}
              ↔ right y∈{44,108} — so a crack always continues into the next
              tile instead of stopping dead at the seam. A crack that changes
              angle as it crosses is not a defect here; real ice does that. */}
          <path d="M28 0 L44 30" />
          <path d="M44 30 L18 52" />
          <path d="M0 44 L18 52" />
          <path d="M44 30 L84 46" />
          <path d="M74 0 L84 46" />
          <path d="M120 44 L84 46" />
          <path d="M18 52 L38 84" />
          <path d="M84 46 L74 92" />
          <path d="M38 84 L74 92" />
          <path d="M38 84 L28 120" />
          <path d="M74 92 L74 120" />
          <path d="M0 108 L14 96" />
          <path d="M14 96 L38 84" />
          <path d="M120 108 L74 92" />
        </g>
      }
    />
  );
});

/* ==========================================================================
   Bands — the only motifs allowed to run off an edge
   ========================================================================== */

/**
 * 回纹 — the key-fret meander, for the edge of a header or a footer.
 *
 * A band is the right answer wherever ornament has to be cut: a meander has no
 * centre, so a reader sees a border continuing past the frame rather than a
 * broken drawing.
 */
export const HoiVanBand = memo(function HoiVanBand({
  className,
  opacity,
  rotate,
}: {
  className?: string;
  opacity?: number;
  rotate?: number;
}) {
  return (
    <PatternField
      className={className}
      opacity={opacity}
      rotate={rotate}
      width={32}
      height={16}
      tile={
        <g fill="none" stroke="currentColor" strokeWidth={1} strokeLinejoin="miter">
          {/* Hooks are inset from x=0 and x=32 so no stroke ever begins exactly
              on a seam, where it would read as a line that had been cut off.
              The baseline is the only thing crossing, and a continuous straight
              line crosses invisibly. */}
          <path d="M2 13 H6 V4 H15 V10 H10 V8" />
          <path d="M18 13 H22 V4 H31 V10 H26 V8" />
          <path d="M0 15.5 H32" strokeWidth={0.6} opacity={0.55} />
        </g>
      }
    />
  );
});

/** 水波纹 — running ripples, for anything that shows movement or progress. */
export const ThuyBaBand = memo(function ThuyBaBand({
  className,
  opacity,
  rotate,
}: {
  className?: string;
  opacity?: number;
  rotate?: number;
}) {
  return (
    <PatternField
      className={className}
      opacity={opacity}
      rotate={rotate}
      width={32}
      height={12}
      tile={
        <g fill="none" stroke="currentColor" strokeWidth={0.8} strokeLinecap="round">
          <path d="M0 4 Q8 -2 16 4 T32 4" />
          <path d="M0 8 Q8 2 16 8 T32 8" />
          <path d="M0 12 Q8 6 16 12 T32 12" opacity={0.6} />
        </g>
      }
    />
  );
});

/** 莲瓣纹 — a band of lotus petals, used to separate blocks within a page. */
export const LienBienBand = memo(function LienBienBand({
  className,
  opacity,
  rotate,
}: {
  className?: string;
  opacity?: number;
  rotate?: number;
}) {
  return (
    <PatternField
      className={className}
      opacity={opacity}
      rotate={rotate}
      width={28}
      height={18}
      tile={
        <g fill="none" stroke="currentColor" strokeWidth={0.85} strokeLinejoin="round">
          <path d="M14 17 C 5 12 4 5 14 1 C 24 5 23 12 14 17 Z" />
          <path d="M14 15 C 10 11 10 6 14 3" strokeWidth={0.5} opacity={0.7} />
          {/* Half petals at both edges, completed by the neighbouring tile. */}
          <path d="M0 17 C 8 13 8 6 0 2" opacity={0.8} />
          <path d="M28 17 C 20 13 20 6 28 2" opacity={0.8} />
        </g>
      }
    />
  );
});

/**
 * 海水江崖 — standing water over cliffs, the hem of a court robe.
 *
 * The most formal thing in the set, so it appears on one screen only: the one
 * shown when a learner finishes something.
 */
export const HaiThuyBand = memo(function HaiThuyBand({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 240 60"
      fill="none"
      stroke="currentColor"
      strokeWidth={1}
      strokeLinecap="round"
      preserveAspectRatio="none"
      aria-hidden="true"
      className={className}
    >
      {/* Slanting water lines rising to the cliffs. */}
      {Array.from({ length: 13 }).map((_, index) => (
        <path
          key={index}
          d={`M${index * 20} 60 C ${index * 20 + 6} 42 ${index * 20 + 14} 34 ${index * 20 + 20} 22`}
          opacity={0.55}
        />
      ))}
      {/* Cliffs. */}
      <path d="M20 60 C 34 30 46 18 60 6 C 74 18 86 30 100 60" />
      <path d="M100 60 C 118 26 134 12 150 2 C 166 12 182 26 200 60" />
      <path d="M0 60 C 8 40 16 30 24 22" opacity={0.7} />
      <path d="M200 60 C 214 36 226 26 240 18" opacity={0.7} />
      {/* Crested waves along the foot. */}
      {[0, 60, 120, 180].map((x) => (
        <path key={x} d={`M${x} 56 q15 -12 30 0 q15 12 30 0`} opacity={0.5} />
      ))}
    </svg>
  );
});

/**
 * 夔龙纹 — the flattened bronze-age dragon, reduced to a running band.
 *
 * The heaviest motif here, so it is reserved for the exam screens where a bit
 * of ceremony is the point.
 */
export const QuyLongBand = memo(function QuyLongBand({
  className,
  opacity,
  rotate,
}: {
  className?: string;
  opacity?: number;
  rotate?: number;
}) {
  return (
    <PatternField
      className={className}
      opacity={opacity}
      rotate={rotate}
      width={72}
      height={24}
      tile={
        <g fill="none" stroke="currentColor" strokeWidth={0.9} strokeLinejoin="round">
          {/* Head: squared snout with a spiral eye, the bronze convention. */}
          <path d="M4 18 V8 H16 V4 H26 V18 Z" />
          <path d="M10 12 a2.5 2.5 0 1 0 0.01 0" strokeWidth={0.7} />
          {/* Body: a meander spine with a curled tail. */}
          <path d="M26 11 H40 V6 H52 V16 H62 V10 H68" />
          <path d="M40 16 H50" strokeWidth={0.6} opacity={0.75} />
          {/* Legs, stylised into hooks. */}
          <path d="M30 18 V22 M46 18 V22 M58 16 V22" strokeWidth={0.7} opacity={0.8} />
          {/* Tail curl stops short of x=72 for the same reason the 回纹 hooks
              do: nothing should terminate on the seam. */}
          <path d="M68 10 a3 3 0 0 1 2 5" />
        </g>
      }
    />
  );
});

/* ==========================================================================
   Placed motifs — always drawn whole
   ========================================================================== */

/**
 * 宝相花 — the eight-fold treasure flower.
 *
 * The one focal ornament, and the reason the earlier lotus was replaced: a
 * radially symmetric flower is destroyed by cropping, so this is always placed
 * inside its container rather than bled off a corner.
 */
export const BaoTuongHoa = memo(function BaoTuongHoa({ className }: { className?: string }) {
  const petal =
    "M100 100 C 78 88 66 62 78 40 C 88 22 100 18 100 18 C 100 18 112 22 122 40 C 134 62 122 88 100 100 Z";
  const innerPetal =
    "M100 100 C 88 92 82 78 88 64 C 93 54 100 50 100 50 C 100 50 107 54 112 64 C 118 78 112 92 100 100 Z";
  return (
    <svg
      viewBox="0 0 200 200"
      fill="none"
      stroke="currentColor"
      strokeWidth={1}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {[0, 45, 90, 135, 180, 225, 270, 315].map((angle) => (
        <g key={angle} transform={`rotate(${angle} 100 100)`}>
          <path d={petal} />
          <path d="M100 96 C 94 74 94 50 100 30" strokeWidth={0.5} opacity={0.6} />
        </g>
      ))}
      {[22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5].map((angle) => (
        <path key={angle} d={innerPetal} transform={`rotate(${angle} 100 100)`} opacity={0.85} />
      ))}
      <circle cx={100} cy={100} r={13} strokeWidth={1.2} />
      <circle cx={100} cy={100} r={6} />
      <circle cx={100} cy={100} r={62} strokeWidth={0.5} opacity={0.45} />
    </svg>
  );
});

/**
 * 如意 — the ruyi head, drawn as a corner piece.
 *
 * Where the old design bled a lotus off the corner and cut it in half, this is
 * shaped to *be* a corner: it reads as finished at any size and never looks
 * broken. `corner` rotates the same drawing to whichever one it sits in.
 */
export const NhuYCorner = memo(function NhuYCorner({
  className,
  corner = "tr",
}: {
  className?: string;
  corner?: "tl" | "tr" | "bl" | "br";
}) {
  const rotation = { tl: 270, tr: 0, br: 90, bl: 180 }[corner];
  return (
    <svg
      viewBox="0 0 100 100"
      fill="none"
      stroke="currentColor"
      strokeWidth={1}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <g transform={`rotate(${rotation} 50 50)`}>
        {/* The ruyi head: a lobed cloud curl tucked against the corner. */}
        <path d="M96 4 H60 C 60 20 74 20 74 32 C 74 44 58 44 52 32 C 46 20 58 8 72 12" />
        <path d="M96 4 V40 C 80 40 80 54 68 54 C 56 54 56 38 68 32 C 80 26 92 38 88 52" />
        <path d="M96 20 H76 C 76 30 84 30 84 38" strokeWidth={0.6} opacity={0.7} />
        {/* Two beads trailing away from the head. */}
        <circle cx={44} cy={56} r={3.5} opacity={0.8} />
        <circle cx={34} cy={66} r={2.2} opacity={0.6} />
      </g>
    </svg>
  );
});

/** 祥云 — a scroll of auspicious cloud, for a hero or a banner. */
export const TuongVan = memo(function TuongVan({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 200 120"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.1}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M20 88 C 4 88 4 66 20 66 C 20 48 44 44 52 58 C 62 40 92 44 94 66 C 112 62 122 78 112 90 Z" />
      <path d="M20 66 a11 11 0 0 1 16 8" strokeWidth={0.7} opacity={0.7} />
      <path d="M52 58 a13 13 0 0 1 18 10" strokeWidth={0.7} opacity={0.7} />
      <path d="M94 66 a12 12 0 0 1 14 12" strokeWidth={0.7} opacity={0.7} />
      {/* The tail that makes it a cloud scroll rather than a blob. */}
      <path d="M112 90 C 140 90 150 74 166 74 C 182 74 186 92 172 96" />
      <path d="M166 74 a9 9 0 0 1 10 10" strokeWidth={0.7} opacity={0.7} />
    </svg>
  );
});

/** 梅花 — five-petal plum blossom, scattered as a small accent. */
export const MaiHoa = memo(function MaiHoa({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 40 40"
      fill="none"
      stroke="currentColor"
      strokeWidth={1}
      aria-hidden="true"
      className={className}
    >
      {[0, 72, 144, 216, 288].map((angle) => (
        <ellipse
          key={angle}
          cx={20}
          cy={11}
          rx={6}
          ry={8}
          transform={`rotate(${angle} 20 20)`}
        />
      ))}
      <circle cx={20} cy={20} r={2.4} />
    </svg>
  );
});

/* ==========================================================================
   Compositions
   ========================================================================== */

/**
 * The layer behind the whole application.
 *
 * One ground (冰裂), one focal flower, and two pools of warm light — no more
 * than that, because everything added here is added behind *every* screen.
 * The flower drifts on a ~44s loop: long enough that it is never caught moving
 * while you read, present enough that the page feels alive when you look up.
 */
export function AmbientOrnament() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden text-gold"
    >
      <BangLietField className="absolute inset-0 h-full w-full" opacity={0.05} />
      {/* Placed so the flower sits whole in the empty right margin on wide
          screens, and is simply absent on narrow ones rather than half-cropped. */}
      <BaoTuongHoa className="animate-drift-slower absolute -right-24 top-[12%] hidden h-[36rem] w-[36rem] opacity-[0.06] xl:block" />
      <TuongVan className="animate-drift-slow absolute -left-16 bottom-[8%] hidden h-72 w-[30rem] opacity-[0.05] lg:block" />
      <div className="absolute -left-1/4 top-0 h-[42rem] w-[42rem] rounded-full bg-gold/[0.05] blur-[120px]" />
      <div className="absolute -right-1/4 bottom-0 h-[38rem] w-[38rem] rounded-full bg-accent/[0.05] blur-[120px]" />
    </div>
  );
}

/**
 * A card's corner mark.
 *
 * Replaces the cropped lotus. The ruyi head is inset rather than bled, so it is
 * whole at every card size, and the lattice ground gives the card a texture the
 * single mark cannot.
 */
export function CardOrnament({
  motif = "nhuy",
  className,
}: {
  motif?: "nhuy" | "thatbao" | "quyboi";
  className?: string;
}) {
  if (motif === "thatbao" || motif === "quyboi") {
    const Field = motif === "thatbao" ? ThatBaoField : QuyBoiField;
    return (
      <Field
        className={clsx(
          "pointer-events-none absolute inset-0 -z-10 h-full w-full text-gold",
          className
        )}
        opacity={0.05}
      />
    );
  }
  return (
    <NhuYCorner
      className={clsx(
        // Inset, not bled: `-z-10` keeps it under the text, and the offsets keep
        // the whole drawing inside the card so nothing is ever cut.
        "pointer-events-none absolute right-1 top-1 -z-10 h-20 w-20 text-gold opacity-[0.14] transition-[opacity,transform] duration-500 group-hover:scale-105 group-hover:opacity-[0.28]",
        className
      )}
    />
  );
}
