import React from 'react';
import { motion } from 'framer-motion';
import { AgentCharacter } from '../../types/office';
import { WORKSPACE_COORDINATES } from '../../services/initialData';
import { Building, Sparkles, CheckCircle2, ChevronRight, FileText } from 'lucide-react';

interface ArchitectOfficeProps {
  architectAgent: AgentCharacter;
  finalBlueprintMarkdown: string | null;
  onOpenBlueprint: () => void;
}

export const ArchitectOffice: React.FC<ArchitectOfficeProps> = ({
  architectAgent,
  finalBlueprintMarkdown,
  onOpenBlueprint,
}) => {
  const coord = WORKSPACE_COORDINATES.architect_office;
  const isComplete = Boolean(finalBlueprintMarkdown);

  return (
    <div
      className={`absolute bg-slate-900/95 border rounded-3xl p-4 shadow-2xl backdrop-blur-xl flex flex-col justify-between transition-all select-none ${
        isComplete
          ? 'border-indigo-500/90 shadow-[0_0_30px_rgba(99,102,241,0.35)]'
          : 'border-indigo-500/50 shadow-lg'
      }`}
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
          <Building className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-xs font-extrabold uppercase tracking-wider text-slate-100">
            Final Architect
          </span>
        </div>
        {isComplete ? (
          <span className="flex items-center gap-1 text-[9px] bg-indigo-950 text-indigo-300 border border-indigo-600/50 px-2 py-0.2 rounded-full font-bold">
            <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" /> 27 Sections
          </span>
        ) : (
          <span className="text-[9px] bg-slate-800 text-slate-400 px-2 py-0.2 rounded-full font-mono">
            Compiling
          </span>
        )}
      </div>

      {/* Screen Monitor Area */}
      <div className="bg-slate-950/90 border border-slate-800 rounded-2xl p-2.5 my-1.5 flex-1 flex flex-col justify-between min-h-0 text-[10px]">
        {isComplete ? (
          <div>
            <div className="text-[9px] font-mono text-indigo-300 font-bold uppercase tracking-wider flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-amber-400" /> Blueprint Ready
            </div>
            <div className="text-xs font-bold text-slate-100 mt-0.5 line-clamp-2">
              FINAL_PROJECT_BLUEPRINT.md
            </div>
            <div className="text-[9px] text-slate-400 mt-1 font-mono">
              100% Traceability Matrix Synthesized
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center py-1">
            <FileText className="w-5 h-5 text-indigo-400 mb-1 opacity-80" />
            <div className="text-xs font-bold text-slate-200">Synthesis Engine</div>
            <div className="text-[9px] text-slate-500 mt-0.5">
              {architectAgent?.currentTask || 'Awaiting specialist convergence...'}
            </div>
          </div>
        )}

        {/* Open Blueprint Button */}
        {isComplete && (
          <button
            onClick={onOpenBlueprint}
            className="w-full mt-1.5 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white text-[10px] font-extrabold py-1.5 rounded-xl transition-all shadow-md flex items-center justify-center gap-1"
          >
            <span>Open Final Blueprint</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Footer Info */}
      <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
        <span>Prime (Architect)</span>
        <span className="text-indigo-400 font-bold">27 Sections</span>
      </div>
    </div>
  );
};
