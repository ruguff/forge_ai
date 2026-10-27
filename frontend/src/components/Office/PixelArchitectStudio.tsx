import React from 'react';
import { motion } from 'framer-motion';
import { PixelCharacter } from './PixelCharacter';
import { useOffice } from '../../context/OfficeContext';
import { Compass, FileText, CheckCircle2, Layers } from 'lucide-react';

interface PixelArchitectStudioProps {
  onOpenBlueprint: () => void;
}

export const PixelArchitectStudio: React.FC<PixelArchitectStudioProps> = ({ onOpenBlueprint }) => {
  const { agents, finalBlueprintMarkdown, pipelineStage } = useOffice();

  const isSynthesizing =
    pipelineStage === 'FINAL_SYNTHESIS' ||
    pipelineStage === 'ARCHITECTURE' ||
    agents.blueprint_architect.status === 'WORKING';

  const isReady =
    Boolean(finalBlueprintMarkdown) ||
    pipelineStage === 'BUILD' ||
    pipelineStage === 'TEST' ||
    pipelineStage === 'SHIP' ||
    pipelineStage === 'COMPLETED';

  return (
    <div className="w-[185px] select-none flex flex-col items-center relative">
      {/* 1. Studio Signpost */}
      <div
        className="pixel-signpost px-2 py-0.5 rounded shadow flex items-center gap-1 -mb-1 z-20 cursor-pointer"
        onClick={onOpenBlueprint}
        style={{ borderTopColor: '#6366F1' }}
      >
        <Compass className="w-3 h-3 text-indigo-400" />
        <span className="text-[7.5px] font-pixel font-bold text-yellow-100 uppercase tracking-tight">
          FINAL ARCHITECT
        </span>
      </div>

      {/* 2. Architect Studio Container */}
      <div className="w-full bg-[#1e293b]/85 border-2 border-[#334155] rounded-xl shadow-lg p-2 flex flex-col justify-between relative backdrop-blur-sm">
        {/* Character Standing / Working at Blueprint Desk */}
        <div className="h-[68px] flex items-center justify-center relative">
          <PixelCharacter
            role="blueprint_architect"
            name="Prime"
            status={isSynthesizing ? 'WORKING' : 'IDLE'}
            bubbleType={isReady ? 'document' : isSynthesizing ? 'lightbulb' : undefined}
            currentTask={
              isReady
                ? 'Master Blueprint generated'
                : isSynthesizing
                ? 'Synthesizing 27-section Blueprint'
                : 'Architecture orchestration'
            }
            onClick={onOpenBlueprint}
            scale={0.92}
          />
        </div>

        {/* Blueprint Board Display */}
        <div className="w-full bg-[#1e1b4b]/90 border border-indigo-500/60 rounded p-1 shadow-inner my-1">
          <div className="flex items-center justify-between">
            <span className="text-[6px] font-pixel text-indigo-300 font-bold uppercase">
              MASTER BLUEPRINT
            </span>
            {isReady && (
              <span className="text-[5.5px] font-pixel text-emerald-400 font-bold flex items-center gap-0.5">
                <CheckCircle2 className="w-2.5 h-2.5" /> READY
              </span>
            )}
          </div>
          <div className="text-[5.5px] font-mono text-slate-300 grid grid-cols-2 gap-0.5 mt-0.5">
            <span>• Arch Spec</span>
            <span>• Data Model</span>
            <span>• API Matrix</span>
            <span>• Security</span>
          </div>
        </div>

        {/* Clickable Artifact Badge */}
        <motion.div
          whileHover={{ scale: 1.02 }}
          onClick={onOpenBlueprint}
          className={`w-full border rounded px-1.5 py-0.5 flex items-center justify-between cursor-pointer transition-colors shadow-sm ${
            isReady
              ? 'bg-indigo-950/90 border-indigo-500/80 hover:bg-indigo-900/90 text-indigo-200'
              : 'bg-slate-900/90 border-slate-700/80 text-slate-400'
          }`}
          title="Open Master Blueprint Viewer"
        >
          <div className="flex items-center gap-1 truncate">
            <FileText className="w-3 h-3 text-indigo-400 shrink-0" />
            <span className="text-[7px] font-pixel truncate">blueprint.md</span>
          </div>
          <span className="text-[6px] font-mono text-indigo-300 bg-indigo-950/80 px-1 py-0.2 rounded border border-indigo-700/60">
            27-SEC
          </span>
        </motion.div>
      </div>
    </div>
  );
};
