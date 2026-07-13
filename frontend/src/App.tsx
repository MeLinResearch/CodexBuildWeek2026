import { ModelActionsPanel } from './components/ModelActionsPanel';
import { TraceabilityMatrix } from './screens/TraceabilityMatrix';
import { RecordDrilldown } from './screens/RecordDrilldown';
import { ApprovalGate } from './screens/ApprovalGate';
import { RunComparison } from './screens/RunComparison';

export default function App() {
  return <main><ModelActionsPanel /><TraceabilityMatrix /><RecordDrilldown /><ApprovalGate /><RunComparison /></main>;
}
