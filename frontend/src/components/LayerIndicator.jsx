import { colors } from "../lib/colors";

export default function LayerIndicator({ layer, active, intensity = 1.0, label }) {
  const colorClass = { L1: colors.layer1, L2: colors.layer2, L3: colors.layer3 }[layer];
  const opacity = active ? Math.max(0.4, intensity) : 0.15;
  return (
    <div className="flex flex-col items-center">
      <div
        data-testid={`indicator-${layer}`}
        className={`w-3 h-3 rounded-full ${colorClass}`}
        style={{ opacity }}
        title={label}
      />
      <span className={`text-[10px] mt-1 ${colors.textSec}`}>{layer}</span>
    </div>
  );
}
