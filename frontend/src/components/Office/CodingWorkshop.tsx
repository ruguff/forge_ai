import React from 'react';
import { motion } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import { WORKSPACE_COORDINATES } from '../../services/initialData';
import { Code2, Terminal, FileCode2, CheckCircle, Loader2 } from 'lucide-react';

export const CodingWorkshop: React.FC = () => {
  const { pipelineStage, agents, buildTestState } = useOffice();
  const coord = WORKSPACE_COORDINATES.coding_workshop;
  const codingAgent = agents.coding_agent;

  const isBuilding =
    pipelineStage === 'BUILD' ||
    pipelineStage === 'TEST' ||
    pipelineStage === 'SHIP' ||
    buildTestState.status === 'BUILDING' ||
    buildTestState.status === 'FIXING';

  return (
    <div
      className={`absolute bg-slate-900/95 border rounded-3xl p-4 shadow-2xl backdrop-blur-xl transition-all flex flex-col justify-between select-none ${
        isBuilding
          ? 'border-green-500/80 shadow-[0_0_25px_rgba(34,197,94,0.3)]'
          : 'border-slate-800/80 shadow-lg opacity-85'
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
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              isBuilding ? 'bg-green-400 shadow-[0_0_10px_#22c55e]' : 'bg-slate-600'
            }`}
          />
          <span className="text-xs font-extrabold tracking-wider uppercase text-slate-100 flex items-center gap-1.5">
            <Code2 className="w-3.5 h-3.5 text-green-400" />
            Coding Workshop
          </span>
        </div>
        <span
          className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
            isBuilding
              ? 'bg-green-950/80 text-green-300 border-green-700/60 font-bold'
              : 'bg-slate-950 text-slate-500 border-slate-800'
          }`}
        >
          {isBuilding ? 'BUILDING' : 'STANDBY'}
        </span>
      </div>

      {/* Terminal Screen Display */}
      <div className="bg-slate-950 border border-slate-800 rounded-2xl p-2.5 my-2 flex-1 flex flex-col justify-between min-h-0 font-mono text-[10px]">
        <div className="flex items-center justify-between text-slate-400 border-b border-slate-800/80 pb-1 mb-1">
          <span className="flex items-center gap-1 text-green-400">
            <Terminal className="w-3 h-3" /> Qwen3-Coder Agent
          </span>
          <span className="text-slate-500 text-[9px]">Open-Weight / In-Repo</span>
        </div>

        {/* Current File Activity */}
        <div className="flex-1 flex flex-col justify-center space-y-1 py-1">
          {isBuilding ? (
            <>
              <div className="flex items-center gap-1.5 text-slate-200">
                <Loader2 className="w-3 h-3 text-green-400 animate-spin shrink-0" />
                <span className="truncate">
                  {buildTestState.currentFile ? (
                    <>Writing <span className="text-green-300 font-bold">{buildTestState.currentFile}</span></>
                  ) : (
                    'Generating verified source modules...'
                  )}
                </span>
              </div>
              <div className="text-[9px] text-slate-400 truncate">
                {codingAgent?.currentTask || 'Synthesizing typed endpoints & schemas...'}
              </div>
            </>
          ) : (
            <div className="text-slate-500 italic text-center py-2">
              Awaiting Master Blueprint approval before code generation starts.
            </div>
          )}
        </div>

        {/* File Changes Stream Count */}
        <div className="pt-1 border-t border-slate-800/80 flex items-center justify-between text-[9px] text-slate-400">
          <span className="flex items-center gap-1">
            <FileCode2 className="w-3 h-3 text-cyan-400" /> Files Created:
          </span>
          <span className="text-green-400 font-bold">
            {buildTestState.filesChanged.length || (isBuilding ? '8 modules' : '0')}
          </span>
        </div>
      </div>

      {/* Footer Info */}
      <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
        <span className="truncate">{codingAgent?.name || 'Byte (Qwen3-Coder)'}</span>
        <span className="text-slate-500 text-[9px]">Strict Contract Adherence</span>
      </div>
    </div>
  );
};
