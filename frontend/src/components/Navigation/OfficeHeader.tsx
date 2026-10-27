import React, { useEffect, useState } from 'react';
import { useOffice } from '../../context/OfficeContext';
import { openInEditor } from '../../services/api';
import {
  Sparkles,
  Scale,
  FileText,
  Compass,
  PlusCircle,
  Play,
  Pause,
  Clock,
  RotateCcw,
  Code2,
} from 'lucide-react';

interface OfficeHeaderProps {
  onStartNewProject: () => void;
  onOpenBlueprint: () => void;
  onOpenConflict: () => void;
  onOpenRequirements: () => void;
}

export const OfficeHeader: React.FC<OfficeHeaderProps> = ({
  onStartNewProject,
  onOpenBlueprint,
  onOpenConflict,
  onOpenRequirements,
}) => {
  const {
    projectId,
    projectIdea,
    pipelineStage,
    isPaused,
    pausePipeline,
    resumePipeline,
    resetCameraOverview,
    finalBlueprintMarkdown,
    activeConflict,
    activeClarification,
    projectContext,
    executionMode,
  } = useOffice();

  // Elapsed timer tracking
  const [secondsElapsed, setSecondsElapsed] = useState<number>(0);

  useEffect(() => {
    if (pipelineStage === 'NOT_STARTED' || pipelineStage === 'COMPLETED' || pipelineStage === 'FAILED' || isPaused) return;
    const interval = setInterval(() => setSecondsElapsed((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, [pipelineStage, isPaused]);

  const formatTimer = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleOpenVSCode = async () => {
    if (!projectId) {
      alert('Please start or select a project first.');
      return;
    }
    const res = await openInEditor(projectId);
    if (!res.success) {
      alert(res.message || 'Unable to open Visual Studio Code.');
    }
  };


  const dagStages = [
    { key: 'UNDERSTANDING', label: 'Understanding' },
    { key: 'REQUIREMENTS', label: 'Requirements' },
    { key: 'ANALYSIS', label: 'Analysis' },
    { key: 'DISCUSSION', label: 'Discussion' },
    { key: 'CONFLICT_RESOLUTION', label: 'Arbitration' },
    { key: 'ARCHITECTURE', label: 'Architecture' },
    { key: 'BUILD', label: 'Build' },
    { key: 'TEST', label: 'Test' },
    { key: 'COMPLETED', label: 'Verified' },
  ];

  const stageOrder = [
    'NOT_STARTED',
    'INTAKE',
    'UNDERSTANDING',
    'REQUIREMENTS',
    'ANALYSIS',
    'CORE_ANALYSIS',
    'ENGINEERING_ANALYSIS',
    'DISCUSSION',
    'CONFLICT_RESOLUTION',
    'ARBITRATION',
    'ARCHITECTURE',
    'FINAL_SYNTHESIS',
    'BUILD',
    'TEST',
    'VERIFICATION',
    'SHIP',
    'COMPLETED',
  ];

  const getStageStatus = (stageKey: string) => {
    if (pipelineStage === 'COMPLETED') return 'completed';
    if (pipelineStage === stageKey) return 'active';

    const currentIndex = stageOrder.indexOf(pipelineStage);
    const stageIndex = stageOrder.indexOf(stageKey);

    if (stageIndex < currentIndex) return 'completed';
    return 'pending';
  };

  const projectName =
    projectContext?.project_name ||
    (projectIdea
      ? projectIdea.length > 28
        ? projectIdea.substring(0, 28) + '...'
        : projectIdea
      : 'Your next project');

  const isRunning =
    pipelineStage !== 'NOT_STARTED' && pipelineStage !== 'COMPLETED' && pipelineStage !== 'FAILED' && pipelineStage !== 'REQUIREMENTS' && !isPaused;

  return (
    <header className="h-[58px] bg-slate-950/95 border-b border-slate-800/80 px-4 flex items-center justify-between backdrop-blur-xl z-30 relative select-none">
      {/* Left: Brand & Project Name */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 cursor-pointer" onClick={resetCameraOverview}>
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-purple-600 p-0.5 flex items-center justify-center shadow-lg">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center text-cyan-400">
              <Sparkles className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-xs font-black tracking-wider bg-gradient-to-r from-slate-100 via-slate-200 to-cyan-300 bg-clip-text text-transparent uppercase">
              PROJECTFORGE AI
            </div>
            <div className="text-[9px] text-slate-400 font-mono flex items-center gap-1.5">
              <span>{projectName}</span>
              <span className="text-slate-600">•</span>
              <span className="text-cyan-400 font-bold">{projectId}</span>
            </div>
          </div>
        </div>

        {/* Autonomous Mode Pill */}
        <div className="hidden sm:flex items-center gap-1.5 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-xl text-[10px] font-mono">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span className="text-slate-300 font-bold">{executionMode}</span>
        </div>

        {/* Running / Status indicator */}
        <div className="flex items-center gap-1.5 text-[10px] font-mono">
          {pipelineStage === 'FAILED' ? (<span className="text-red-300 font-bold">● STOPPED</span>) : isRunning ? (
            <span className="text-emerald-400 font-bold flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" /> RUNNING
            </span>
          ) : pipelineStage === 'COMPLETED' ? (
            <span className="text-indigo-400 font-bold">● SHIPPED</span>
          ) : isPaused ? (
            <span className="text-amber-400 font-bold">● PAUSED</span>
          ) : (
            <span className="text-slate-500">● STANDBY</span>
          )}
        </div>
      </div>

      {/* Center: Stage Progress Pipeline */}
      <div className="hidden 2xl:flex items-center gap-1 bg-slate-900/90 border border-slate-800 px-3 py-1 rounded-2xl">
        {dagStages.map((stg, idx) => {
          const status = getStageStatus(stg.key);
          return (
            <React.Fragment key={stg.key}>
              <div
                className={`flex items-center gap-1 text-[10px] font-mono transition-colors ${
                  status === 'active'
                    ? 'text-cyan-300 font-bold'
                    : status === 'completed'
                    ? 'text-emerald-400'
                    : 'text-slate-600'
                }`}
              >
                <div
                  className={`w-1.5 h-1.5 rounded-full ${
                    status === 'active'
                      ? 'bg-cyan-400 shadow-[0_0_8px_#38bdf8]'
                      : status === 'completed'
                      ? 'bg-emerald-400'
                      : 'bg-slate-700'
                  }`}
                />
                <span>{stg.label}</span>
              </div>
              {idx < dagStages.length - 1 && <span className="text-slate-700 text-[9px]">→</span>}
            </React.Fragment>
          );
        })}
      </div>

      {/* Right: Quick Action Controls */}
      <div className="flex items-center gap-2">
        {/* Elapsed Timer */}
        <div className="hidden md:flex items-center gap-1 text-slate-400 text-xs font-mono bg-slate-900/80 border border-slate-800 px-2.5 py-1 rounded-xl">
          <Clock className="w-3.5 h-3.5 text-cyan-400" />
          <span>{formatTimer(secondsElapsed)}</span>
        </div>

        {/* Requirements Drawer Button */}
        <button
          onClick={onOpenRequirements}
          className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-xl border transition-all cursor-pointer font-medium ${
            activeClarification
              ? 'bg-amber-950/80 border-amber-600 text-amber-300 animate-pulse font-bold'
              : 'bg-slate-900 border-slate-800 text-slate-300 hover:text-cyan-400'
          }`}
        >
          <Compass className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Requirements</span>
        </button>

        {/* Blueprint Viewer Button */}
        <button
          onClick={onOpenBlueprint}
          className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-xl border transition-all cursor-pointer font-medium ${
            finalBlueprintMarkdown
              ? 'bg-indigo-950/80 border-indigo-600 text-indigo-300 font-bold'
              : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Blueprint</span>
        </button>

        {/* Conflict Button */}
        {activeConflict && (
          <button
            onClick={onOpenConflict}
            className="flex items-center gap-1 text-xs bg-amber-950/80 border border-amber-600 text-amber-300 px-2.5 py-1 rounded-xl animate-pulse font-bold cursor-pointer"
          >
            <Scale className="w-3.5 h-3.5 text-amber-400" />
            <span>Dispute</span>
          </button>
        )}

        {/* Open in VS Code Button */}
        <button
          disabled={pipelineStage !== 'COMPLETED'}
          onClick={handleOpenVSCode}
          title="Open generated project in Visual Studio Code"
          className="disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 text-xs bg-slate-900 border border-blue-500/50 hover:bg-blue-950/60 text-blue-400 font-semibold px-2.5 py-1 rounded-xl transition-all cursor-pointer"
        >
          <Code2 className="w-3.5 h-3.5 text-blue-400" />
          <span className="hidden sm:inline">VS Code</span>
        </button>

        {/* New Project CTA */}
        <button
          onClick={onStartNewProject}
          className="flex items-center gap-1.5 text-xs bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-extrabold px-3 py-1.5 rounded-xl transition-all shadow-md cursor-pointer"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">New project</span>
        </button>
      </div>
    </header>
  );
};
