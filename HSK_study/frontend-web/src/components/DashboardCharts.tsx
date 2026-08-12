import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/**
 * Recharts is the single heaviest dependency in the bundle, so both charts live
 * here behind one lazy import. The dashboard paints its numbers immediately and
 * the charts stream in a moment later.
 */

const AXIS = {
  stroke: "var(--color-ink-faint)",
  fontSize: 11,
  tickLine: false,
  axisLine: false,
};

const TOOLTIP_STYLE = {
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: 12,
  fontSize: 12,
  color: "var(--color-ink)",
};

export function ForecastChart({ data }: { data: Array<{ label: string; count: number }> }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -22 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-soft)" vertical={false} />
        <XAxis dataKey="label" {...AXIS} />
        <YAxis {...AXIS} allowDecimals={false} width={34} />
        <Tooltip
          cursor={{ fill: "var(--color-surface-2)" }}
          contentStyle={TOOLTIP_STYLE}
          formatter={(value) => [`${Number(value ?? 0)} từ`, "Đến hạn"]}
        />
        <Bar dataKey="count" fill="var(--color-accent)" radius={[4, 4, 0, 0]} maxBarSize={28} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ActivityChart({ data }: { data: Array<{ label: string; reviews: number }> }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -22 }}>
        <defs>
          <linearGradient id="activityFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-jade)" stopOpacity={0.45} />
            <stop offset="100%" stopColor="var(--color-jade)" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-soft)" vertical={false} />
        <XAxis dataKey="label" {...AXIS} />
        <YAxis {...AXIS} allowDecimals={false} width={34} />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value) => [`${Number(value ?? 0)} lượt`, "Đã ôn"]}
        />
        <Area
          type="monotone"
          dataKey="reviews"
          stroke="var(--color-jade)"
          strokeWidth={2}
          fill="url(#activityFill)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
