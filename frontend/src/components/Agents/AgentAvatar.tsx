import React from 'react';
import { motion } from 'framer-motion';
import { AgentCharacter } from '../../types/office';
import { AGENT_COLOR_MAP } from '../../services/initialData';
import {
  Layout,
  BrainCircuit,
  Cpu,
  Palette,
  ShieldAlert,
  CheckCircle2,
  Scale,
  FileText,
  AlertCircle,
  Clock,
  Loader2,
} from 'lucide-react';

const ICON_MAP: Record<string, React.ElementType> = {
  Layout,
  BrainCircuit,
  Cpu,
  Palette,
  ShieldAlert,
  CheckCircle2,
  Scale,
  FileText,
};

interface AgentAvatarProps {
  agent: AgentCharacter;
  onClick?: () => void;
  showSpeechBubble?: boolean;
}

export const AgentAvatar: React.FC<AgentAvatarProps> = ({
  agent,
  onClick,
  showSpeechBubble = true,
}) => {
  const IconComponent = ICON_MAP[agent.iconName] || Cpu;
  const colors = AGENT_COLOR_MAP[agent.id] || {
    hex: '#06b6d4',
    bg: 'bg-cyan-950/80',
    border: 'border-cyan-500/80',
    text: 'text-cyan-400',
    shadow: 'shadow-[0_0_25px_rgba(6,182,212,0.35)]',
  };

  const getStatusGlow = () => {
    switch (agent.status) {
      case 'WORKING':
        return `ring-2 ring-cyan-400 ${colors.shadow} animate-pulse`;
      case 'DISCUSSING':
        return 'ring-2 ring-purple-400 shadow-[0_0_25px_rgba(168,85,247,0.6)] animate-bounce';
      case 'BLOCKED':
      case 'ERROR':
        return 'ring-2 ring-red-500 shadow-[0_0_25px_rgba(239,68,68,0.6)]';
      case 'COMPLETED':
        return 'ring-2 ring-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.5)]';
      default:
        return 'ring-1 ring-slate-700 hover:ring-cyan-500/50';
    }
  };

  const getStatusBadge = () => {
    switch (agent.status) {
      case 'WORKING':
        return (
          <span className="flex items-center gap-1 text-[10px] bg-cyan-950/90 text-cyan-300 border border-cyan-700/60 px-1.5 py-0.5 rounded-full font-bold">
            <Loader2 className="w-2.5 h-2.5 animate-spin" /> Working
          </span>
        );
      case 'DISCUSSING':
        return (
          <span className="flex items-center gap-1 text-[10px] bg-purple-950/90 text-purple-300 border border-purple-700/60 px-1.5 py-0.5 rounded-full font-bold">
            <Clock className="w-2.5 h-2.5 animate-pulse" /> Discussing
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="flex items-center gap-1 text-[10px] bg-emerald-950/90 text-emerald-300 border border-emerald-700/60 px-1.5 py-0.5 rounded-full font-bold">
            <CheckCircle2 className="w-2.5 h-2.5" /> Done
          </span>
        );
      case 'ERROR':
        return (
          <span className="flex items-center gap-1 text-[10px] bg-red-950/90 text-red-300 border border-red-700/60 px-1.5 py-0.5 rounded-full font-bold">
            <AlertCircle className="w-2.5 h-2.5" /> Error
          </span>
        );
      default:
        return (
          <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded-full font-mono">
            Idle
          </span>
        );
    }
  };

  return (
    <div className="relative group cursor-pointer" onClick={onClick}>
      {/* Floating Animated Thought / Speech Bubble */}
      {showSpeechBubble && agent.activityMessage && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute -top-16 left-1/2 -translate-x-1/2 w-52 bg-slate-900/95 border border-slate-700 text-slate-200 text-[11px] p-2.5 rounded-2xl shadow-2xl z-30 pointer-events-none text-center backdrop-blur-md"
        >
          <p className="line-clamp-2 leading-snug font-medium text-cyan-200">{agent.activityMessage}</p>
          <div className="absolute left-1/2 -bottom-1 -translate-x-1/2 border-4 border-transparent border-t-slate-700" />
        </motion.div>
      )}

      {/* Circular Avatar Token sitting on Pod Top */}
      <motion.div
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
        className={`w-16 h-16 rounded-full bg-gradient-to-br ${agent.avatarColor} p-0.5 transition-all duration-300 ${getStatusGlow()}`}
      >
        <div className="w-full h-full bg-slate-950 rounded-full flex flex-col items-center justify-center relative overflow-hidden backdrop-blur-sm">
          <IconComponent
            className="w-7 h-7 transition-transform group-hover:scale-110"
            style={{ color: agent.accentColor }}
          />
        </div>
      </motion.div>

      {/* Name and Status Badge */}
      <div className="mt-1 text-center w-32 -ml-8">
        <div className="text-[11px] font-extrabold text-slate-100 truncate">{agent.name}</div>
        <div className="flex justify-center mt-0.5">{getStatusBadge()}</div>
      </div>
    </div>
  );
};
