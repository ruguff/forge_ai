import React, { useState } from 'react';
import { OfficeProvider, useOffice } from './context/OfficeContext';
import { OfficeHeader } from './components/Navigation/OfficeHeader';
import { OfficeCanvas } from './components/Office/OfficeCanvas';
import { ActivityTimeline } from './components/Activity/ActivityTimeline';
import { AgentInspectorDrawer } from './components/Agents/AgentInspectorDrawer';
import { RequirementsInspector } from './components/Inspector/RequirementsInspector';
import { DiscussionPanel } from './components/Discussions/DiscussionPanel';
import { ConflictRoomPanel } from './components/Conflicts/ConflictRoomPanel';
import { BlueprintViewer } from './components/Blueprint/BlueprintViewer';
import { AdaptiveClarificationModal } from './components/Intake/AdaptiveClarificationModal';
import { Sparkles, Zap, Compass, Building, CheckCircle2 } from 'lucide-react';

const MainOfficeLayout: React.FC = () => {
  const {
    pipelineStage,
    startAutonomousProject,
    activeClarification,
    answerClarification,
    selectedAgentId,
    selectAgent,
    activeDiscussion,
    activeConflict,
    finalBlueprintMarkdown,
    executionMode,
    setExecutionMode,
    isRequirementsOpen,
    setIsRequirementsOpen,
    isBlueprintOpen,
    setIsBlueprintOpen,
    isConflictOpen,
    setIsConflictOpen,
    isDiscussionOpen,
    setIsDiscussionOpen,
    isActivityExpanded,
    setIsActivityExpanded,
  } = useOffice();

  const [newIdeaText, setNewIdeaText] = useState('');
  const [showStartModal, setShowStartModal] = useState(false);

  const handleLaunchAutonomous = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newIdeaText.trim()) return;
    setShowStartModal(false);
    await startAutonomousProject(newIdeaText.trim(), executionMode);
  };

  const handleOpenClarification = () => {
    if (activeClarification) {
      // Clarification modal is always rendered when activeClarification exists
    }
  };

  return (
    <div className="w-screen h-screen flex flex-col bg-[#090D16] text-slate-100 overflow-hidden select-none">
      {/* 1. Header Navigation Bar (58px) */}
      <OfficeHeader
        onStartNewProject={() => setShowStartModal(true)}
        onOpenBlueprint={() => setIsBlueprintOpen(true)}
        onOpenConflict={() => setIsConflictOpen(true)}
        onOpenRequirements={() => setIsRequirementsOpen(true)}
      />

      {/* 2. Main Middle Virtual Office Canvas Area */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Spatial Virtual Office Canvas */}
        <main className="flex-1 relative">
          <OfficeCanvas
            onOpenDiscussion={() => setIsDiscussionOpen(true)}
            onOpenConflict={() => setIsConflictOpen(true)}
            onOpenBlueprint={() => setIsBlueprintOpen(true)}
            onOpenRequirements={() => setIsRequirementsOpen(true)}
            onOpenClarification={handleOpenClarification}
          />
        </main>

        {/* Slide-Over Right Agent Inspector Drawer */}
        <AgentInspectorDrawer
          agentRole={selectedAgentId}
          onClose={() => selectAgent(null)}
        />
      </div>

      {/* 3. Real-Time Activity Timeline Stream (Collapsible Bottom Bar) */}
      <ActivityTimeline
        isExpanded={isActivityExpanded}
        onToggleExpand={() => setIsActivityExpanded(!isActivityExpanded)}
      />

      {/* 4. Inspectors & Modals */}
      {/* 17 Architectural Dimensions Inspector Drawer */}
      <RequirementsInspector
        isOpen={isRequirementsOpen}
        onClose={() => setIsRequirementsOpen(false)}
        onOpenClarification={handleOpenClarification}
      />

      {/* Cross-Agent Discussion Transcript Panel */}
      <DiscussionPanel
        isOpen={isDiscussionOpen}
        onClose={() => setIsDiscussionOpen(false)}
      />

      {/* Conflict Resolution Matrix Panel */}
      <ConflictRoomPanel
        isOpen={isConflictOpen}
        onClose={() => setIsConflictOpen(false)}
      />

      {/* 27-Section Master Blueprint Viewer */}
      <BlueprintViewer
        isOpen={isBlueprintOpen}
        onClose={() => setIsBlueprintOpen(false)}
      />

      {/* Minimal Adaptive Clarification Modal (When Material Decision is needed) */}
      {activeClarification && (
        <AdaptiveClarificationModal
          question={activeClarification}
          onAnswer={answerClarification}
        />
      )}

      {/* Launch New Architecture Project Modal */}
      {showStartModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-slate-950/85 backdrop-blur-md">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl w-full max-w-lg p-6 space-y-5 shadow-2xl">
            <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
              <div className="w-10 h-10 rounded-xl bg-cyan-950 border border-cyan-500/50 flex items-center justify-center text-cyan-400 shadow-md">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-100">Start a new project</h3>
                <p className="text-[11px] text-slate-400 font-mono">Autonomous Multi-Agent Software Company</p>
              </div>
            </div>

            <form onSubmit={handleLaunchAutonomous} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Describe Your Software Project Idea:
                </label>
                <textarea
                  value={newIdeaText}
                  onChange={(e) => setNewIdeaText(e.target.value)}
                  placeholder="E.g. I want to build a website called Cake and Joy..."
                  rows={4}
                  className="w-full bg-slate-950 border border-slate-700 rounded-2xl p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400 leading-relaxed font-sans"
                  autoFocus
                />
              </div>

              {/* Mode Selection Toggle */}
              <div className="bg-slate-950/70 p-3 rounded-2xl border border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  {executionMode === 'AUTONOMOUS' ? (
                    <Zap className="w-4 h-4 text-cyan-400" />
                  ) : (
                    <Compass className="w-4 h-4 text-purple-400" />
                  )}
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block">
                      {executionMode === 'AUTONOMOUS' ? 'Autonomous Mode' : 'Guided Mode'}
                    </span>
                    <span className="text-[10px] text-slate-400 block">
                      {executionMode === 'AUTONOMOUS'
                        ? 'Proceeds automatically; clarifies only material architectural unknowns'
                        : 'Prompts review at each major architectural milestone'}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setExecutionMode(executionMode === 'AUTONOMOUS' ? 'GUIDED' : 'AUTONOMOUS')
                  }
                  className="px-3 py-1 text-[11px] font-mono rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors cursor-pointer font-bold"
                >
                  Switch
                </button>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => setShowStartModal(false)}
                  className="text-xs text-slate-400 hover:text-slate-200 px-3 py-2 rounded-xl transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newIdeaText.trim()}
                  className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-slate-950 font-black text-xs px-5 py-2.5 rounded-xl transition-all shadow-md flex items-center gap-2 cursor-pointer"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Start project</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <OfficeProvider>
      <MainOfficeLayout />
    </OfficeProvider>
  );
};
