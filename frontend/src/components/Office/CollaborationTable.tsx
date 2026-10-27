import React from 'react';
import { motion } from 'framer-motion';
import { DiscussionSession } from '../../types/office';
import { WORKSPACE_COORDINATES, COLLAB_SEATS } from '../../services/initialData';
import { Users, MessageSquare, Sparkles, MessageCircle } from 'lucide-react';

interface CollaborationTableProps {
  activeDiscussion: DiscussionSession | null;
  onOpenDiscussion: () => void;
}

export const CollaborationTable: React.FC<CollaborationTableProps> = ({
  activeDiscussion,
  onOpenDiscussion,
}) => {
  const coord = WORKSPACE_COORDINATES.collaboration_table;
  const isMeetingActive = Boolean(activeDiscussion);

  return (
    <div
      className={`absolute bg-slate-900/95 border rounded-3xl p-5 shadow-2xl backdrop-blur-xl flex flex-col items-center justify-between text-center select-none transition-all ${
        isMeetingActive
          ? 'border-purple-500/90 shadow-[0_0_40px_rgba(168,85,247,0.35)]'
          : 'border-slate-800/80 shadow-lg'
      }`}
      style={{
        left: coord.x,
        top: coord.y,
        width: coord.width,
        height: coord.height,
      }}
    >
      {/* Subtle Animated Radial Meeting Pulse when active */}
      {isMeetingActive && (
        <motion.div
          animate={{
            scale: [0.95, 1.05, 0.95],
            opacity: [0.3, 0.6, 0.3],
          }}
          transition={{ repeat: Infinity, duration: 2.5, ease: 'easeInOut' }}
          className="absolute inset-0 rounded-3xl bg-gradient-to-r from-purple-600/10 via-indigo-600/10 to-cyan-600/10 pointer-events-none"
        />
      )}

      {/* Table Header Label */}
      <div className="flex items-center justify-between w-full pb-2 border-b border-slate-800/80">
        <div className="flex items-center gap-2 text-purple-400 font-extrabold text-xs uppercase tracking-wider">
          <Users className="w-4 h-4" />
          <span>Central Collaboration Table</span>
        </div>
        <span
          className={`text-[9px] font-mono px-2 py-0.5 rounded-full border ${
            isMeetingActive
              ? 'bg-purple-950 text-purple-300 border-purple-700 font-bold'
              : 'bg-slate-950 text-slate-500 border-slate-800'
          }`}
        >
          {isMeetingActive ? 'IN SESSION' : 'READY'}
        </span>
      </div>

      {/* Visual Round Conference Table Surface */}
      <div className="relative my-2 w-full flex-1 flex flex-col items-center justify-center">
        {/* Conference Table Oval */}
        <div className="w-[380px] h-[150px] rounded-[60px] bg-slate-950/90 border-2 border-slate-800 flex flex-col items-center justify-center p-4 relative shadow-inner">
          {/* Subtle Woodgrain/Cyber Center Strip */}
          <div className="absolute inset-x-8 h-[2px] bg-gradient-to-r from-transparent via-purple-500/40 to-transparent" />

          {isMeetingActive ? (
            <div className="relative z-10">
              <div className="flex items-center justify-center gap-1.5 text-purple-400 font-mono text-[10px] uppercase font-bold tracking-wider mb-1">
                <Sparkles className="w-3 h-3" /> Live Cross-Agent Alignment
              </div>
              <div className="text-xs font-bold text-slate-100 max-w-[320px] line-clamp-2">
                {activeDiscussion?.topic}
              </div>
              <div className="text-[10px] text-purple-300 font-mono mt-1 flex items-center justify-center gap-1">
                <MessageCircle className="w-3 h-3" /> {activeDiscussion?.messages?.length || 3} dialogue turns
              </div>
            </div>
          ) : (
            <div className="text-[11px] text-slate-400 italic max-w-[280px] leading-relaxed">
              Specialists physically meet here to negotiate architectural trade-offs and protocol contracts.
            </div>
          )}
        </div>
      </div>

      {/* Footer CTA Button */}
      {isMeetingActive ? (
        <button
          onClick={onOpenDiscussion}
          className="w-full bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-600 hover:from-purple-500 hover:to-indigo-500 text-white text-[11px] font-extrabold py-2 rounded-xl transition-all shadow-lg flex items-center justify-center gap-1.5 cursor-pointer"
        >
          <MessageSquare className="w-4 h-4" />
          <span>Inspect Active Discussion Transcript</span>
        </button>
      ) : (
        <div className="text-[10px] text-slate-500 font-mono">
          Stage 3 Alignment Hub • Auto-detects Contradictions
        </div>
      )}
    </div>
  );
};
