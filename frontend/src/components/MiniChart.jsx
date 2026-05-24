import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";

export default function MiniChart({ data, dataKey = "flow_gpm", color = "#38bdf8" }) {
  return (
    <div className="h-12 w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <YAxis hide domain={["auto", "auto"]} />
          <Line
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            dot={false}
            strokeWidth={1.5}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
