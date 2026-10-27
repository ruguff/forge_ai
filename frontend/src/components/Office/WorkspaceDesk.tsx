import React from 'react';
import { motion } from 'framer-motion';
import { AgentCharacter, ArtifactItem } from '../../types/office';
import { AGENT_COLOR_MAP, WORKSPACE_COORDINATES } from '../../services/initialData';
import { FileCode, Monitor, ShieldCheck, ExternalLink, Cpu } from 'lucide-react';

interface WorkspaceDeskProps {
  agent: AgentCharacter;
  artifacts: ArtifactItem[];
  onSelectAgent: () => void;
  onSelectArtifact: (artifact: ArtifactItem) => void;
}

export const WorkspaceDesk: React.FC<WorkspaceDeskProps> = ({
  agent,
  artifacts,
  onSelectAgent,
  onSelectArtifact,
}) => {
  const coord = WORKSPACE_COORDINATES[agent.workspaceId];
  if (!coord) return null;

  const agentArtifacts = artifacts.filter((a) => a.producedBy === agent.id);
  const colorTheme = AGENT_COLOR_MAP[agent.id] || {
    hex: '#06B6D4',
    bg: 'bg-cyan-950/80',
    border: 'border-cyan-500/80',
    text: 'text-cyan-400',
    shadow: 'shadow-[0_0_25px_rgba(6,182,212,0.35)]',
  };

  const isWorking = agent.status === 'WORKING';
  const isCompleted = agent.status === 'COMPLETED';
  const isConflict = agent.status === 'CONFLICT';

  return (
    <div
      className={`absolute bg-slate-900/95 border rounded-3xl p-4 shadow-2xl backdrop-blur-xl transition-all select-none flex flex-col justify-between ${
        isConflict
          ? 'border-red-500/80 shadow-[0_0_30px_rgba(239,68,68,0.35)] animate-pulse'
          : isWorking
          ? `${colorTheme.border} ${colorTheme.shadow}`
          : isCompleted
          ? 'border-emerald-500/80 shadow-[0_0_20px_rgba(16,185,129,0.25)]'
          : 'border-slate-800/80 shadow-lg'
      }`}
      style={{
        left: coord.x,
        top: coord.y,
        width: coord.width,
        height: coord.height,
      }}
    >
      {/* Workspace Header Label */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className="w-2.5 h-2.5 rounded-full shrink-0 shadow-md"
            style={{ backgroundColor: agent.accentColor }}
          />
          <span className="text-xs font-extrabold tracking-wider uppercase text-slate-100 truncate">
            {agent.roleTitle}
          </span>
        </div>
        <button
          onClick={onSelectAgent}
          className="text-[10px] text-cyan-400 hover:text-cyan-300 bg-slate-950 hover:bg-slate-800 border border-slate-800 px-2 py-0.5 rounded-lg transition-colors flex items-center gap-1 font-mono shrink-0"
        >
          <span>Inspect</span>
          <ExternalLink className="w-2.5 h-2.5" />
        </button>
      </div>

      {/* Workstation Inner Monitor Screen */}
      <div className="bg-slate-950/90 border border-slate-800 rounded-2xl p-2.5 my-1.5 flex-1 flex flex-col justify-between min-h-0">
        <div>
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono mb-1">
            <span className="flex items-center gap-1">
              <Monitor className="w-3 h-3 text-cyan-400" /> Workstation Screen
            </span>
            <span
              className="font-bold uppercase text-[9px] px-1.5 py-0.2 rounded border"
              style={{
                color: agent.accentColor,
                borderColor: `${agent.accentColor}40`,
                backgroundColor: `${agent.accentColor}10`,
              }}
            >
              {agent.status}
            </span>
          </div>
          <div className="text-[11px] text-slate-200 font-semibold truncate" title={agent.currentTask}>
            {agent.currentTask}
          </div>
          <div className="text-[10px] text-slate-400 truncate mt-0.5" title={agent.activityMessage}>
            {agent.activityMessage}
          </div>
        </div>

        {/* Calibrated Confidence Meter */}
        <div className="pt-1.5 border-t border-slate-800/80">
          <div className="flex items-center justify-between text-[10px] text-slate-400 mb-0.5">
            <span className="flex items-center gap-1 font-mono text-[9px]">
              <ShieldCheck className="w-2.5 h-2.5 text-cyan-400" /> Calibrated Confidence
            </span>
            <span className="font-mono font-bold text-[10px]" style={{ color: agent.accentColor }}>
              {(agent.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden border border-slate-800">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${agent.confidence * 100}%`,
                backgroundColor: agent.accentColor,
              }}
            />
          </div>
        </div>
      </div>

      {/* Desk Artifact Output Footer */}
      <div className="pt-1.5 border-t border-slate-800/80 flex items-center justify-between">
        <span className="text-[10px] text-slate-400 font-mono truncate max-w-[100px]">{agent.name}</span>
        <div className="flex items-center gap-1">
          {agentArtifacts.map((artifact) => (
            <motion.button
              key={artifact.id}
              whileHover={{ scale: 1.05 }}
              onClick={() => onSelectArtifact(artifact)}
              className="flex items-center gap-1 text-[9px] bg-slate-950 hover:bg-slate-800 border border-slate-700 text-cyan-300 px-2 py-0.5 rounded-lg transition-colors font-mono"
            >
              <FileCode className="w-3 h-3 text-cyan-400" />
              <span className="truncate max-w-[80px]">{artifact.title}</span>
            </motion.button>
          ))}
          {agentArtifacts.length === 0 && (
            <span className="text-[9px] text-slate-500 italic font-mono">Standby</span>
          )}
        </div>
      </div>
    </div>
  );
};
