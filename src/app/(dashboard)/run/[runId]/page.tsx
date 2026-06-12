"use client";

import { useState, useEffect } from "react";
import { useRunState } from "@/hooks/useRunState";
import { useParams } from "next/navigation";

// Official shell components
import { TopNav, TabType } from "@/components/shell/TopNav";
import { LayerProgress } from "@/components/shell/LayerProgress";

// Official graph components
import { GraphPane } from "@/components/graph/GraphPane";

// Official layer2 components — Agent Canvas
import { AgentStatusPanel } from "@/components/layer2/AgentStatusPanel";

// Official layer3 components
import { BridgeResultsPanel } from "@/components/layer3/BridgeResultsPanel";
import { SearchStatusPanel } from "@/components/layer3/SearchStatusPanel";

// Official layer4 components (report is composed from layer4 sub-components)
import { ReportNav } from "@/components/layer4/ReportNav";
import { StreamingReport } from "@/components/layer4/StreamingReport";
import { ActionsPanel } from "@/components/layer4/ActionsPanel";

export default function RunPage() {
  const params = useParams();
  const runId = Array.isArray(params.runId) ? params.runId[0] : (params.runId || 'nexus-active-run');
  
  const [activeTab, setActiveTab] = useState<TabType>("graph");
  const { runState } = useRunState(runId);

  // Automatically advance tabs as the backend transitions layers,
  // but still allow manual override via the UI clicks on the TopNav.
  useEffect(() => {
    if (!runState) return;

    switch (runState.currentLayer) {
      case 1:
        setActiveTab('graph');
        break;
      case 2:
        setActiveTab('canvas');
        break;
      case 3:
        setActiveTab('search');
        break;
      case 4:
        setActiveTab('report');
        break;
    }
  }, [runState?.currentLayer]);

  return (
    <main className="relative w-full h-screen flex flex-col overflow-hidden bg-white">
      {/* Global Shell Navigation */}
      <TopNav activeTab={activeTab} onTabChange={setActiveTab} />
      
      {/* Global Pipeline Progress Bar */}
      <div className="w-full border-b border-[#E5E5E5] px-10 py-3 bg-gray-50 flex items-center shadow-sm z-40 relative">
        <LayerProgress />
      </div>

      <div className="relative w-full flex-1 overflow-hidden bg-gray-50">

        {/* TAB 1: GRAPH */}
        <div className={`w-full h-full animate-fade-in flex flex-col ${activeTab === "graph" ? "flex" : "hidden"}`}>
          <GraphPane />
        </div>

        {/* TAB 2: AGENT CANVAS */}
        <div className={`w-full h-full animate-fade-in ${activeTab === "canvas" ? "block" : "hidden"}`}>
          <AgentStatusPanel />
        </div>

        {/* TAB 3: ABSTRACTION — Layer 3 bridge results */}
        <div className={`w-full h-full animate-fade-in flex flex-col items-center justify-center bg-[#F9FAFB] tab-pane-bg ${activeTab === "abstraction" ? "flex" : "hidden"}`}>
          <BridgeResultsPanel />
        </div>

        {/* TAB 4: SEARCH — Layer 3 domain-blind query uplink */}
        <div className={`w-full h-full animate-fade-in flex flex-col items-center bg-[#F9FAFB] tab-pane-bg ${activeTab === "search" ? "flex" : "hidden"}`}>
          <SearchStatusPanel />
        </div>

        {/* TAB 5: REPORT — Layer 4 streaming report */}
        <div className={`w-full h-full animate-fade-in flex flex-col bg-[#F3F4F6] ${activeTab === "report" ? "flex" : "hidden"}`}>
          <div className="w-full h-full max-w-4xl mx-auto pt-16 bg-white border-x border-[#E5E5E5] px-16 overflow-y-auto relative flex flex-col items-start shadow-sm">
            <StreamingReport />
            <ActionsPanel />
          </div>
        </div>

      </div>
    </main>
  );
}
