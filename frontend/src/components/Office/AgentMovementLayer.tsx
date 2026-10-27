import React from 'react';
import { motion } from 'framer-motion';
import { AgentCharacter, AgentRole } from '../../types/office';
import { AGENT_COLOR_MAP } from '../../services/initialData';
import {
  Target,
  BrainCircuit,
  Cpu,
  Palette,
  ShieldAlert,
  CheckCircle2,
  Scale,
  Building,
  Code2,
  Loader2,
  Clock,
  AlertTriangle,
  Check,
} from 'lucide-react';

const ICON_MAP: Record<string, React.ElementType> = {
  Target,
  BrainCircuit,
  Cpu,
  Palette,
  ShieldAlert,
  CheckCircle2,
  Scale,
  Building,
  Code2,
};

interface AgentMovementLayerProps {
  agents: Record<AgentRole, AgentCharacter>;
  selectedAgentId: AgentRole | null;
  onSelectAgent: (role: AgentRole) => void;
}

export const AgentMovementLayer: React.FC<AgentMovementLayerProps> = ({
  agents,
  selectedAgentId,
  onSelectAgent,
}) => {
  const agentList = Object.values(agents);

  return (
    <div className="absolute inset-0 pointer-events-none z-20">
      {agentList.map((agent) => {
        const IconComponent = ICON_MAP[agent.iconName] || Cpu;
        const colorTheme = AGENT_COLOR_MAP[agent.id] || {
          hex: '#06b6d4',
          bg: 'bg-cyan-950/80',
          border: 'border-cyan-500/80',
          text: 'text-cyan-400',
          shadow: 'shadow-[0_0_25px_rgba(6,182,212,0.35)]',
        };

        const isDiscussing = agent.status === 'DISCUSSING';
        const isWorking = agent.status === 'WORKING';
        const isConflict = agent.status === 'CONFLICT';
        const isCompleted = agent.status === 'COMPLETED';
        const isSelected = selectedAgentId === agent.id;

        return (
          <motion.div
            key={agent.id}
            animate={{
              x: agent.position.x - 36,
              y: agent.position.y - 36,
            }}
            transition={{
              type: 'spring',
              stiffness: 90,
              damping: 18,
            }}
            className="absolute top-0 left-0 pointer-events-auto cursor-pointer"
            onClick={() => onSelectAgent(agent.id)}
          >
            {/* Animated Speech Bubble when Discussing or Alerting */}
            {isDiscussing && (
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                className="absolute -top-16 left-1/2 -translate-x-1/2 w-48 bg-slate-900/95 border border-purple-500/80 text-purple-200 text-[10px] p-2 rounded-2xl shadow-2xl z-30 text-center backdrop-blur-md"
              >
                <div className="font-bold text-[9px] uppercase tracking-wider text-purple-400 mb-0.5">
                  Discussing Alignment
                </div>
                <p className="line-clamp-2 leading-tight">{agent.activityMessage}</p>
                <div className="absolute left-1/2 -bottom-1 -translate-x-1/2 border-4 border-transparent border-t-purple-600" />
              </motion.div>
            )}

            {/* Agent Physical Avatar Pod */}
            <motion.div
              whileHover={{ scale: 1.15 }}
              whileTap={{ scale: 0.95 }}
              className={`w-[72px] h-[72px] rounded-full bg-gradient-to-br ${agent.avatarColor} p-1 shadow-2xl transition-all ${
                isSelected
                  ? 'ring-4 ring-cyan-400 shadow-[0_0_30px_#38bdf8]'
                  : isConflict
                  ? 'ring-4 ring-amber-500 shadow-[0_0_30px_#f59e0b] animate-pulse'
                  : isDiscussing
                  ? 'ring-4 ring-purple-500 shadow-[0_0_25px_#a855f7]'
                  : isWorking
                  ? `ring-2 ring-cyan-400 ${colorTheme.shadow} animate-pulse`
                  : isCompleted
                  ? 'ring-2 ring-emerald-400 shadow-[0_0_20px_#10b981]'
                  : 'ring-1 ring-slate-700 opacity-80'
              }`}
            >
              <div className="w-full h-full bg-slate-950 rounded-full flex flex-col items-center justify-center relative overflow-hidden backdrop-blur-md">
                <IconComponent
                  className="w-7 h-7 transition-transform group-hover:scale-110"
                  style={{ color: agent.accentColor }}
                />
              </div>

              {/* Status Badge Tag */}
              <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 whitespace-nowrap">
                {isWorking && (
                  <span className="flex items-center gap-0.5 text-[8px] bg-cyan-950 text-cyan-300 border border-cyan-700 px-1.5 py-0.2 rounded-full font-bold shadow-md">
                    <Loader2 className="w-2 h-2 animate-spin" /> RUN
                  </span>
                )}
                {isDiscussing && (
                  <span className="flex items-center gap-0.5 text-[8px] bg-purple-950 text-purple-300 border border-purple-700 px-1.5 py-0.2 rounded-full font-bold shadow-md">
                    <Clock className="w-2 h-2 animate-pulse" /> MEET
                  </span>
                )}
                {isConflict && (
                  <span className="flex items-center gap-0.5 text-[8px] bg-amber-950 text-amber-300 border border-amber-600 px-1.5 py-0.2 rounded-full font-bold shadow-md">
                    <AlertTriangle className="w-2 h-2" /> DISPUTE
                  </span>
                )}
                {isCompleted && (
                  <span className="flex items-center gap-0.5 text-[8px] bg-emerald-950 text-emerald-300 border border-emerald-600 px-1.5 py-0.2 rounded-full font-bold shadow-md">
                    <Check className="w-2 h-2" /> DONE
                  </span>
                )}
              </div>
            </motion.div>

            {/* Name Label */}
            <div className="text-center mt-1 -ml-6 w-36">
              <div className="text-[10px] font-extrabold text-slate-100 drop-shadow-md truncate">
                {agent.name}
              </div>
              <div className="text-[8px] font-mono text-slate-400 truncate">
                {agent.roleTitle}
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
};
