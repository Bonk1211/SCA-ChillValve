import BranchRow from "./BranchRow";
import SystemSummary from "./SystemSummary";

export default function DashboardGrid() {
  return (
    <div>
      <BranchRow branchId="A" label="CRAH" />
      <BranchRow branchId="B" label="AHU" />
      <SystemSummary />
    </div>
  );
}
