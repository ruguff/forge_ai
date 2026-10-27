import React from 'react';
import { motion } from 'framer-motion';
import { PixelCharacter, AGENT_PERSONALITIES } from './PixelCharacter';
import { AgentRole, AgentStatus } from '../../types/office';
import { FileText, CheckCircle2, Monitor } from 'lucide-react';

interface PixelWorkspaceDeskProps {
  role: AgentRole;
  labName: string;
  status: AgentStatus;
  currentTask?: string;
  artifactName: string;
  artifactDocType?: string;
  progressPercent?: number;
  onSelectAgent?: () => void;
  onOpenArtifact?: () => void;
  isAgentPresent?: boolean; // false if agent has physically moved to Collaboration Table / Conflict Room
}

export const PixelWorkspaceDesk: React.FC<PixelWorkspaceDeskProps> = ({
  role,
  labName,
  status,
  currentTask,
  artifactName,
  artifactDocType,
  progressPercent = 75,
  onSelectAgent,
  onOpenArtifact,
  isAgentPresent = true,
}) => {
  const personality = AGENT_PERSONALITIES[role];
  const isWorking = status === 'WORKING';

  return (
    <div className="w-[185px] select-none flex flex-col items-center relative">
      {/* 1. Wooden/Metal Lab Signpost */}
      <div
        className="pixel-signpost px-2 py-0.5 rounded shadow flex items-center gap-1 -mb-1 z-20 cursor-pointer"
        onClick={onSelectAgent}
        style={{ borderTopColor: personality.accentColor }}
      >
        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: personality.accentColor }} />
        <span className="text-[7.5px] font-pixel font-bold text-yellow-100 uppercase tracking-tight truncate max-w-[150px]">
          {labName}
        </span>
      </div>

      {/* 2. Physical Desk Station Box */}
      <div className="w-full bg-[#1e293b]/85 border-2 border-[#334155] rounded-xl shadow-lg p-2 flex flex-col justify-between relative backdrop-blur-sm">
        {/* Top Area: Character standing/sitting at desk (if present) */}
        <div className="h-[68px] flex items-center justify-center relative">
          {isAgentPresent ? (
            <PixelCharacter
              role={role}
              name={personality.shortName}
              status={status}
              currentTask={currentTask || personality.defaultTask}
              onClick={onSelectAgent}
              scale={0.92}
            />
          ) : (
            /* Empty Chair with "In Meeting" note */
            <div className="flex flex-col items-center justify-center opacity-60 text-center py-2">
              <div className="w-8 h-8 rounded-full border-2 border-dashed border-slate-500 flex items-center justify-center text-xs">
                🪑
              </div>
              <span className="text-[6.5px] font-mono text-cyan-300 mt-1">In Collaboration</span>
            </div>
          )}
        </div>

        {/* Middle: Physical Desk with Monitor & Keyboard */}
        <div className="w-full bg-[#334155] border border-[#475569] rounded-md p-1 flex items-center justify-between shadow-inner my-1">
          {/* Monitor Screen with live activity */}
          <div className="flex items-center gap-1.5">
            <div className="w-7 h-5 bg-[#0f172a] border border-[#0ea5e9] rounded-sm flex items-center justify-center p-0.5 shadow">
              <span
                className={`text-[5px] font-mono font-bold leading-none ${
                  isWorking ? 'text-emerald-400 animate-pulse' : 'text-slate-400'
                }`}
              >
                {isWorking ? 'RUN' : 'IDLE'}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-[6.5px] font-mono text-slate-300 font-semibold truncate max-w-[80px]">
                {currentTask || personality.defaultTask}
              </span>
              {isWorking && (
                <div className="w-16 h-1 bg-slate-800 rounded-full overflow-hidden mt-0.5">
                  <div
                    className="h-full bg-emerald-400 rounded-full"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Bottom: Clickable Generated Physical Artifact Badge */}
        <motion.div
          whileHover={{ scale: 1.02 }}
          onClick={onOpenArtifact}
          className="w-full bg-slate-900/90 hover:bg-slate-800/90 border border-slate-700/80 rounded px-1.5 py-0.5 flex items-center justify-between cursor-pointer transition-colors shadow-sm"
          title={`Open ${artifactName}`}
        >
          <div className="flex items-center gap-1 truncate">
            <FileText className="w-3 h-3 text-cyan-400 shrink-0" />
            <span className="text-[7px] font-pixel text-slate-200 truncate">{artifactName}</span>
          </div>
          <span className="text-[6px] font-mono text-emerald-400 bg-emerald-950/70 px-1 py-0.2 rounded border border-emerald-800/50">
            {artifactDocType || 'DOC'}
          </span>
        </motion.div>
      </div>
    </div>
  );
};
