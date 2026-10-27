import React from 'react';
import { motion } from 'framer-motion';
import { PixelCharacter } from './PixelCharacter';
import { useOffice } from '../../context/OfficeContext';
import { Terminal, Code2, FileCode, CheckCircle2, AlertCircle } from 'lucide-react';

interface PixelCodingWorkshopProps {
  onOpenCodeStream: () => void;
}

export const PixelCodingWorkshop: React.FC<PixelCodingWorkshopProps> = ({ onOpenCodeStream }) => {
  const { pipelineStage, buildTestState, agents } = useOffice();

  const isBuilding =
    pipelineStage === 'BUILD' ||
    pipelineStage === 'TEST' ||
    pipelineStage === 'SHIP' ||
    pipelineStage === 'COMPLETED' ||
    buildTestState.status === 'BUILDING' ||
    buildTestState.status === 'FIXING';

  const currentFile = buildTestState.currentFile || 'src/services/api.ts';
  const filesModifiedCount = buildTestState.filesChanged.length || (isBuilding ? 7 : 0);
  const totalFilesCount = 12;

  const terminalLine =
    buildTestState.terminalLogs[0] ||
    (isBuilding
      ? 'fastapi.routing: mounted /api/v1/auth, /api/v1/projects'
      : 'standby for architecture approval...');

  return (
    <div className="flex flex-col items-center select-none z-15 w-[820px]">
      {/* 1. Wooden/Metal Workshop Signpost */}
      <div
        className="pixel-signpost px-4 py-0.5 rounded shadow flex items-center gap-1.5 -mb-2 z-25 cursor-pointer"
        onClick={onOpenCodeStream}
        style={{ borderTopColor: '#22C55E' }}
      >
        <Code2 className="w-3 h-3 text-emerald-400" />
        <span className="text-[8px] font-pixel text-yellow-100 font-bold uppercase tracking-wider">
          CODING WORKSHOP
        </span>
        {isBuilding && (
          <span className="text-[6.5px] font-pixel text-emerald-400 bg-emerald-950 px-1 py-0.2 rounded border border-emerald-600 animate-pulse">
            COMPILING
          </span>
        )}
      </div>

      {/* 2. Coding Workshop Floor Area */}
      <div
        onClick={onOpenCodeStream}
        className="w-full bg-[#1e293b]/90 border-2 border-[#334155] rounded-xl shadow-2xl p-2.5 flex items-center justify-between cursor-pointer group backdrop-blur-md"
      >
        {/* Left: 3 Physical Computer Desks with CRT Monitors & Coders */}
        <div className="flex items-end gap-3">
          {/* Station 1: Left Station */}
          <div className="flex flex-col items-center">
            <div className="w-12 h-10 bg-[#cbd5e1] border border-[#64748b] rounded-t shadow p-0.5 flex flex-col items-center justify-between">
              <div className="w-9 h-6 bg-[#0f172a] border border-emerald-400 rounded-sm p-0.5 overflow-hidden">
                <span className="text-[4.5px] font-mono text-emerald-400 font-bold block leading-none">
                  {isBuilding ? 'import torch\nimport api' : 'idle'}
                </span>
              </div>
              <div className="w-7 h-1 bg-slate-400 rounded-sm" />
            </div>
            {/* Seated Coder */}
            <div className="relative -top-2 z-20">
              <PixelCharacter
                role="aiml_architect"
                name="Aris"
                status={isBuilding ? 'WORKING' : 'IDLE'}
                facingBack
                isSeated
                scale={0.8}
              />
            </div>
          </div>

          {/* Station 2: Center Primary Coding Agent (Qwen3-Coder) */}
          <div className="flex flex-col items-center">
            <div className="w-14 h-12 bg-[#cbd5e1] border-2 border-[#16a34a] rounded-t shadow p-1 flex flex-col items-center justify-between">
              <div className="w-11 h-7 bg-[#0f172a] border border-[#22c55e] rounded-sm p-0.5 overflow-hidden">
                <span className="text-[5px] font-mono text-cyan-300 font-bold block leading-tight">
                  {isBuilding ? 'FastAPI()\nStripe.v1' : 'standby'}
                </span>
              </div>
              <div className="w-9 h-1.5 bg-slate-400 rounded-sm" />
            </div>
            {/* Primary Coder Facing Front with main() bubble */}
            <div className="relative -top-3 z-20">
              <PixelCharacter
                role="coding_agent"
                name="Qwen3"
                status={isBuilding ? 'WORKING' : 'IDLE'}
                bubbleType={isBuilding ? 'code' : undefined}
                bubbleText={isBuilding ? 'main()' : undefined}
                scale={0.95}
              />
            </div>
          </div>

          {/* Station 3: Right Station */}
          <div className="flex flex-col items-center">
            <div className="w-12 h-10 bg-[#cbd5e1] border border-[#64748b] rounded-t shadow p-0.5 flex flex-col items-center justify-between">
              <div className="w-9 h-6 bg-[#0f172a] border border-cyan-400 rounded-sm p-0.5 overflow-hidden">
                <span className="text-[4.5px] font-mono text-cyan-300 font-bold block leading-none">
                  {isBuilding ? 'npm build\nvite.config' : 'ready'}
                </span>
              </div>
              <div className="w-7 h-1 bg-slate-400 rounded-sm" />
            </div>
            {/* Seated Coder */}
            <div className="relative -top-2 z-20">
              <PixelCharacter
                role="engineering_lead"
                name="Marcus"
                status={isBuilding ? 'WORKING' : 'IDLE'}
                facingBack
                isSeated
                scale={0.8}
              />
            </div>
          </div>
        </div>

        {/* Right: Live File Artifacts & Terminal Log Console */}
        <div className="flex-1 ml-4 flex flex-col gap-1.5">
          {/* File Status Bar */}
          <div className="bg-slate-900/90 border border-slate-700 rounded p-1.5 flex items-center justify-between">
            <div className="flex items-center gap-1.5 truncate max-w-[340px]">
              <FileCode className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <div className="flex flex-col truncate">
                <span className="text-[6px] font-mono text-slate-400">ACTIVE COMPILATION FILE:</span>
                <span className="text-[7.5px] font-mono font-bold text-white truncate">
                  {currentFile}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2 text-[6.5px] font-mono text-slate-300">
              <span className="bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700">
                FILES: <strong className="text-emerald-400">{filesModifiedCount}</strong>/{totalFilesCount}
              </span>
              <span className="bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700">
                TESTS: <strong className="text-amber-400">PENDING</strong>
              </span>
            </div>
          </div>

          {/* Mini Live Terminal Stream */}
          <div className="bg-black/90 border border-emerald-500/40 rounded p-1.5 shadow-inner">
            <div className="flex items-center gap-1 text-[6px] font-mono text-emerald-400 mb-0.5">
              <Terminal className="w-2.5 h-2.5" />
              <span>TERMINAL STREAM</span>
            </div>
            <div className="text-[6.5px] font-mono text-slate-300 truncate">
              &gt; {terminalLine}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
