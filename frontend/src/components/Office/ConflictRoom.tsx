import React from 'react';
import { motion } from 'framer-motion';
import { ConflictItem } from '../../types/office';
import { WORKSPACE_COORDINATES } from '../../services/initialData';
import { Scale, AlertTriangle, ChevronRight, CheckCircle2 } from 'lucide-react';

interface ConflictRoomProps {
  activeConflict: ConflictItem | null;
  conflictsHistory: ConflictItem[];
  onOpenConflict: () => void;
}

export const ConflictRoom: React.FC<ConflictRoomProps> = ({
  activeConflict,
  conflictsHistory,
  onOpenConflict,
}) => {
  const coord = WORKSPACE_COORDINATES.conflict_room;

  return (
    <div
      className={`absolute bg-slate-900/95 border rounded-3xl p-4 shadow-2xl backdrop-blur-xl flex flex-col justify-between transition-all select-none ${
        activeConflict
          ? 'border-amber-500/90 shadow-[0_0_30px_rgba(245,158,11,0.35)]'
          : 'border-cyan-500/50 shadow-lg'
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
          <Scale className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-xs font-extrabold uppercase tracking-wider text-slate-100">
            Conflict Arbiter
          </span>
        </div>
        {activeConflict ? (
          <span className="flex items-center gap-1 text-[9px] bg-amber-950/80 text-amber-300 border border-amber-600/50 px-2 py-0.2 rounded-full font-bold animate-pulse">
            <AlertTriangle className="w-2.5 h-2.5" /> Disputed
          </span>
        ) : (
          <span className="text-[9px] bg-cyan-950 text-cyan-400 border border-cyan-700/50 px-2 py-0.2 rounded-full font-bold font-mono">
            Aligned
          </span>
        )}
      </div>

      {/* Screen Monitor Area */}
      <div className="bg-slate-950/90 border border-slate-800 rounded-2xl p-2.5 my-1.5 flex-1 flex flex-col justify-between min-h-0 text-[10px]">
        {activeConflict ? (
          <div>
            <div className="text-[9px] font-mono text-amber-400 font-bold uppercase tracking-wider">
              Contradiction Detected
            </div>
            <div className="text-xs font-bold text-slate-100 mt-0.5 line-clamp-2">
              {activeConflict.issue || activeConflict.title}
            </div>
            <div className="text-[9px] text-slate-400 mt-1 font-mono">
              Confidence: {((activeConflict.confidence || 0.92) * 100).toFixed(0)}%
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center py-1">
            <CheckCircle2 className="w-5 h-5 text-cyan-400 mb-1 opacity-80" />
            <div className="text-xs font-bold text-slate-200">Zero Blockers</div>
            <div className="text-[9px] text-slate-500 mt-0.5">
              {conflictsHistory.length} ADRs arbitrated & logged
            </div>
          </div>
        )}

        {/* Action Button */}
        {activeConflict && (
          <button
            onClick={onOpenConflict}
            className="w-full mt-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 text-[10px] font-extrabold py-1.5 rounded-xl transition-all shadow-md flex items-center justify-center gap-1"
          >
            <span>Inspect Decision Matrix</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Footer Info */}
      <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
        <span>Lex (Arbiter)</span>
        <span className="text-cyan-400 font-bold">{conflictsHistory.length} ADRs</span>
      </div>
    </div>
  );
};
