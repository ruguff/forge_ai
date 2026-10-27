import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import {
  X,
  Compass,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Filter,
  Layers,
  Sparkles,
  ChevronRight,
} from 'lucide-react';

interface RequirementsInspectorProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenClarification: () => void;
}

export const RequirementsInspector: React.FC<RequirementsInspectorProps> = ({
  isOpen,
  onClose,
  onOpenClarification,
}) => {
  const { projectContext, activeClarification } = useOffice();
  const [filterType, setFilterType] = useState<string>('ALL');

  if (!isOpen) return null;

  const requirements = projectContext?.requirements || [];
  const filtered =
    filterType === 'ALL'
      ? requirements
      : requirements.filter((r) => r.type === filterType);

  const getBadgeStyle = (type: string) => {
    switch (type) {
      case 'EXPLICIT':
        return 'bg-emerald-950/80 text-emerald-400 border-emerald-700/60 font-bold';
      case 'INFERRED':
        return 'bg-blue-950/80 text-blue-400 border-blue-700/60 font-bold';
      case 'ASSUMPTION':
        return 'bg-purple-950/80 text-purple-400 border-purple-700/60 font-bold';
      case 'UNKNOWN':
        return 'bg-amber-950/80 text-amber-400 border-amber-700/60 font-bold';
      default:
        return 'bg-slate-900 text-slate-400 border-slate-700';
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-end bg-slate-950/70 backdrop-blur-sm">
        <motion.aside
          initial={{ x: 500, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 500, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 280, damping: 28 }}
          className="w-full max-w-xl h-full bg-slate-950 border-l border-slate-800 flex flex-col shadow-2xl select-none"
        >
          {/* Header */}
          <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-cyan-950/80 border border-cyan-500/50 flex items-center justify-center text-cyan-400">
                <Compass className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                  <span>17 Architectural Dimensions</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-slate-900 text-cyan-400 border border-slate-800">
                    {requirements.length} Extracted
                  </span>
                </h3>
                <p className="text-[11px] text-slate-400 font-mono">
                  {projectContext?.project_name || 'ProjectForge Specification'}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Decision Alert Banner if material unknown exists */}
          {activeClarification && (
            <div className="p-4 bg-amber-950/40 border-b border-amber-600/40 flex items-center justify-between gap-3">
              <div className="flex items-start gap-2.5 min-w-0">
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-bold text-amber-200">
                    PROJECTFORGE needs your decision
                  </div>
                  <div className="text-[11px] text-amber-300/80 line-clamp-1">
                    {activeClarification.question}
                  </div>
                </div>
              </div>
              <button
                onClick={onOpenClarification}
                className="shrink-0 text-xs bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-3 py-1.5 rounded-xl transition-colors flex items-center gap-1 shadow-md"
              >
                <span>Decide</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Filter Pills */}
          <div className="px-5 py-3 border-b border-slate-800/80 flex items-center gap-2 text-[11px] overflow-x-auto">
            <span className="text-slate-500 flex items-center gap-1 font-mono shrink-0">
              <Filter className="w-3 h-3" /> Filter:
            </span>
            {['ALL', 'EXPLICIT', 'INFERRED', 'ASSUMPTION', 'UNKNOWN'].map((type) => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`px-2.5 py-1 rounded-lg font-mono transition-colors shrink-0 ${
                  filterType === type
                    ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/60 font-bold'
                    : 'bg-slate-900/60 text-slate-400 border border-slate-800 hover:text-slate-200'
                }`}
              >
                {type}
              </button>
            ))}
          </div>

          {/* Requirement Items List */}
          <div className="p-5 overflow-y-auto space-y-3 flex-1">
            {filtered.map((req) => (
              <div
                key={req.id}
                className="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-3.5 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-[10px] font-mono text-slate-500 uppercase">{req.dimension}</span>
                    <span className="text-xs font-bold text-slate-200 truncate">{req.title}</span>
                  </div>
                  <span
                    className={`text-[9px] font-mono px-2 py-0.5 rounded-full border shrink-0 ${getBadgeStyle(
                      req.type
                    )}`}
                  >
                    {req.type}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">{req.description}</p>

                {/* Evidence & Confidence Footer */}
                <div className="mt-2 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] font-mono text-slate-500">
                  <span className="truncate max-w-[320px]">
                    Source: <span className="text-slate-400">{req.source}</span>
                    {req.evidence && ` • ${req.evidence.substring(0, 40)}...`}
                  </span>
                  <span className="text-cyan-400 font-bold">
                    {(req.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}

            {filtered.length === 0 && (
              <div className="text-center py-12 text-slate-500 font-mono text-xs">
                No requirements match current filter.
              </div>
            )}
          </div>

          {/* Footer Summary */}
          <div className="p-4 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span>ProjectForge Autonomous Engine</span>
            <span className="text-cyan-400">Strict Inferred vs Explicit Audit</span>
          </div>
        </motion.aside>
      </div>
    </AnimatePresence>
  );
};
