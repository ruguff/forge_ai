import React from 'react';
import { motion } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import { WORKSPACE_COORDINATES } from '../../services/initialData';
import { Compass, CheckCircle2, AlertCircle, FileSearch, Sparkles } from 'lucide-react';

interface UnderstandingWorkspaceProps {
  onOpenRequirements: () => void;
  onOpenClarification: () => void;
}

export const UnderstandingWorkspace: React.FC<UnderstandingWorkspaceProps> = ({
  onOpenRequirements,
  onOpenClarification,
}) => {
  const { projectContext, activeClarification, pipelineStage } = useOffice();
  const coord = WORKSPACE_COORDINATES.understanding_workspace;

  const isAnalyzing = pipelineStage === 'UNDERSTANDING' || pipelineStage === 'REQUIREMENTS';
  const hasContext = Boolean(projectContext);
  const reqCount = projectContext?.requirements?.length || 0;
  const unknownCount = projectContext?.unknowns?.length || 0;

  return (
    <div
      className="absolute bg-slate-900/95 border border-cyan-500/50 rounded-3xl p-4 shadow-2xl backdrop-blur-xl transition-all flex flex-col justify-between select-none"
      style={{
        left: coord.x,
        top: coord.y,
        width: coord.width,
        height: coord.height,
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_10px_#22d3ee]" />
          <span className="text-xs font-extrabold tracking-wider uppercase text-slate-100 flex items-center gap-1.5">
            <Compass className="w-3.5 h-3.5 text-cyan-400" />
            Project Understanding
          </span>
        </div>
        <button
          onClick={onOpenRequirements}
          className="text-[10px] text-cyan-400 hover:text-cyan-300 bg-slate-950 hover:bg-slate-800 border border-slate-800 px-2 py-0.5 rounded-lg transition-colors font-mono flex items-center gap-1"
        >
          <FileSearch className="w-3 h-3" />
          <span>Inspect 17D</span>
        </button>
      </div>

      {/* Monitor Display Screen */}
      <div className="bg-slate-950/90 border border-slate-800/90 rounded-2xl p-2.5 my-2 flex-1 flex flex-col justify-between min-h-0">
        <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
          <span className="flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-cyan-400" /> 17 Dimensions Engine
          </span>
          <span
            className={`font-bold ${
              isAnalyzing ? 'text-amber-400 animate-pulse' : hasContext ? 'text-emerald-400' : 'text-slate-500'
            }`}
          >
            {isAnalyzing ? 'ANALYZING...' : hasContext ? 'EXTRACTED' : 'STANDBY'}
          </span>
        </div>

        {/* Dynamic Project Name or Placeholder */}
        <div className="mt-1">
          <div className="text-xs font-bold text-slate-100 truncate">
            {projectContext?.project_name || 'Awaiting Project Idea...'}
          </div>
          <p className="text-[10px] text-slate-400 line-clamp-2 mt-0.5">
            {projectContext?.problem_statement ||
              'Natural language prompt is ingested and parsed across 17 architectural dimensions with strict inference labeling.'}
          </p>
        </div>

        {/* 17D Mini Stat Badges */}
        <div className="grid grid-cols-3 gap-1 pt-1.5 border-t border-slate-800/80 text-[10px] font-mono">
          <div className="bg-slate-900 px-1.5 py-0.5 rounded text-center border border-slate-800">
            <span className="text-slate-500">Reqs: </span>
            <span className="font-bold text-cyan-400">{reqCount}</span>
          </div>
          <div className="bg-slate-900 px-1.5 py-0.5 rounded text-center border border-slate-800">
            <span className="text-slate-500">Unknowns: </span>
            <span className="font-bold text-amber-400">{unknownCount}</span>
          </div>
          <div className="bg-slate-900 px-1.5 py-0.5 rounded text-center border border-slate-800">
            <span className="text-slate-500">Status: </span>
            <span className="font-bold text-emerald-400">V1</span>
          </div>
        </div>
      </div>

      {/* Decision Needed Banner or Ready Status */}
      {activeClarification ? (
        <motion.div
          initial={{ scale: 0.95 }}
          animate={{ scale: [1, 1.02, 1] }}
          transition={{ repeat: Infinity, duration: 2 }}
          onClick={onOpenClarification}
          className="bg-amber-950/80 border border-amber-500/80 hover:bg-amber-900/80 text-amber-200 text-[10px] font-bold p-1.5 rounded-xl cursor-pointer flex items-center justify-between"
        >
          <span className="flex items-center gap-1.5 truncate">
            <AlertCircle className="w-3 h-3 text-amber-400 shrink-0" />
            Decision Required: {activeClarification.question.substring(0, 30)}...
          </span>
          <span className="underline shrink-0">Resolve</span>
        </motion.div>
      ) : (
        <div className="text-[10px] text-slate-500 font-mono flex items-center justify-between">
          <span className="flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            {hasContext ? 'No material blockers' : 'Awaiting input prompt'}
          </span>
          <span className="text-slate-600">Phase 1</span>
        </div>
      )}
    </div>
  );
};
