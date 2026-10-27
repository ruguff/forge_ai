import React from 'react';
import { motion } from 'framer-motion';
import { PixelCharacter } from './PixelCharacter';
import { useOffice } from '../../context/OfficeContext';
import { Scale, AlertTriangle, FileText, CheckCircle2 } from 'lucide-react';

interface PixelConflictRoomProps {
  onOpenConflict: () => void;
}

export const PixelConflictRoom: React.FC<PixelConflictRoomProps> = ({ onOpenConflict }) => {
  const { agents, activeConflict, conflictsHistory, pipelineStage } = useOffice();

  const isConflictActive = Boolean(activeConflict);

  const agentAName =
    activeConflict?.participatingAgents[0] === 'aiml_architect'
      ? 'AI/ML'
      : activeConflict?.participatingAgents[0] === 'product_manager'
      ? 'PRODUCT'
      : 'ENGINEERING';

  const agentBName =
    activeConflict?.participatingAgents[1] === 'aiml_architect'
      ? 'AI/ML'
      : activeConflict?.participatingAgents[1] === 'security_auditor'
      ? 'SECURITY'
      : 'ENGINEERING';

  const optionAText =
    (activeConflict?.participatingAgents[0] &&
      activeConflict?.recommendations?.[activeConflict.participatingAgents[0]]) ||
    'PostgreSQL Relational';

  const optionBText =
    (activeConflict?.participatingAgents[1] &&
      activeConflict?.recommendations?.[activeConflict.participatingAgents[1]]) ||
    'Vector Embeddings DB';

  return (
    <div className="flex flex-col items-center select-none z-15 w-[460px]">
      {/* 1. Carved Wooden Signpost */}
      <div
        className={`pixel-signpost px-3 py-0.5 rounded shadow flex items-center gap-1.5 -mb-2 z-25 cursor-pointer ${
          isConflictActive ? 'border-amber-500 animate-pulse' : ''
        }`}
        onClick={onOpenConflict}
      >
        <Scale className="w-3 h-3 text-cyan-400" />
        <span className="text-[7.5px] font-pixel text-yellow-100 font-bold uppercase tracking-wider">
          CONFLICT ARBITRATION ROOM
        </span>
        {isConflictActive && (
          <span className="text-[6.5px] font-pixel text-amber-400 bg-amber-950 px-1 py-0.2 rounded border border-amber-600">
            DISPUTE DETECTED
          </span>
        )}
      </div>

      {/* 2. Room Box Container with Lex & Arbitration Desk */}
      <div
        onClick={onOpenConflict}
        className={`w-full rounded-xl border-2 p-2 relative flex items-center justify-between cursor-pointer transition-all ${
          isConflictActive
            ? 'bg-amber-950/40 border-amber-500/80 shadow-[0_0_20px_rgba(245,158,11,0.3)]'
            : 'bg-[#1e293b]/85 border-[#334155] shadow-lg backdrop-blur-sm'
        }`}
      >
        {/* Left: Conflicting Agent Position A (or Security Advisor) */}
        <div className="flex flex-col items-center min-w-[70px]">
          {isConflictActive ? (
            <div className="text-center">
              <span className="text-[6.5px] font-pixel text-blue-400 font-bold uppercase">
                {agentAName}
              </span>
              <div className="w-16 bg-blue-950/80 border border-blue-600 rounded p-1 text-[6px] font-mono text-blue-200 mt-1 truncate">
                "{optionAText}"
              </div>
            </div>
          ) : (
            <div className="opacity-40 text-center text-[7px] font-mono text-slate-400">
              Station A
            </div>
          )}
        </div>

        {/* Center: Conflict Arbiter (Lex) with Scales of Justice Desk */}
        <div className="flex flex-col items-center relative z-20">
          <PixelCharacter
            role="conflict_resolver"
            name="Lex"
            status={isConflictActive ? 'CONFLICT' : agents.conflict_resolver.status}
            bubbleType="scale"
            currentTask={isConflictActive ? 'Evaluating trade-offs...' : 'ADR & conflict monitoring'}
            scale={0.95}
          />

          {/* Lex's Desk & Scales */}
          <div className="w-28 bg-[#334155] border border-[#475569] rounded p-1 flex items-center justify-between mt-1 shadow">
            <span className="text-xs">⚖️</span>
            <div className="flex flex-col text-right">
              <span className="text-[6px] font-pixel text-cyan-300 font-bold">
                {isConflictActive ? 'EVALUATING...' : 'READY'}
              </span>
              <span className="text-[5.5px] font-mono text-slate-400">
                {conflictsHistory.length} ADRs resolved
              </span>
            </div>
          </div>
        </div>

        {/* Right: Conflicting Agent Position B */}
        <div className="flex flex-col items-center min-w-[70px]">
          {isConflictActive ? (
            <div className="text-center">
              <span className="text-[6.5px] font-pixel text-purple-400 font-bold uppercase">
                {agentBName}
              </span>
              <div className="w-16 bg-purple-950/80 border border-purple-600 rounded p-1 text-[6px] font-mono text-purple-200 mt-1 truncate">
                "{optionBText}"
              </div>
            </div>
          ) : (
            <div className="opacity-40 text-center text-[7px] font-mono text-slate-400">
              Station B
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
