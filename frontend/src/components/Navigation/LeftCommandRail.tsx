import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import {
  LayoutGrid,
  Users,
  GitMerge,
  Scale,
  FileCode,
  FileText,
  Activity,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from 'lucide-react';

interface LeftCommandRailProps {
  onOpenBlueprint: () => void;
  onOpenConflict: () => void;
}

export const LeftCommandRail: React.FC<LeftCommandRailProps> = ({
  onOpenBlueprint,
  onOpenConflict,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const {
    pipelineStage,
    activeConflict,
    conflictsHistory,
    artifacts,
    resetCameraOverview,
  } = useOffice();

  const navItems = [
    {
      id: 'office',
      label: 'Office Overview',
      icon: LayoutGrid,
      action: resetCameraOverview,
      badge: null,
    },
    {
      id: 'agents',
      label: 'Specialist Agents',
      icon: Users,
      action: resetCameraOverview,
      badge: '8',
    },
    {
      id: 'pipeline',
      label: 'Pipeline Stage',
      icon: GitMerge,
      action: resetCameraOverview,
      badge: pipelineStage !== 'NOT_STARTED' ? 'ACTIVE' : null,
    },
    {
      id: 'conflicts',
      label: 'Conflict Room',
      icon: Scale,
      action: onOpenConflict,
      badge: activeConflict ? '1' : conflictsHistory.length > 0 ? `${conflictsHistory.length}` : null,
      highlight: !!activeConflict,
    },
    {
      id: 'artifacts',
      label: 'Artifact Registry',
      icon: FileCode,
      action: resetCameraOverview,
      badge: `${artifacts.length}`,
    },
    {
      id: 'blueprint',
      label: 'Final Blueprint',
      icon: FileText,
      action: onOpenBlueprint,
      badge: pipelineStage === 'COMPLETED' ? 'READY' : null,
      highlight: pipelineStage === 'COMPLETED',
    },
  ];

  return (
    <motion.aside
      animate={{ width: isExpanded ? 220 : 56 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="h-[calc(100vh-56px)] bg-slate-950/95 border-r border-slate-800/80 flex flex-col justify-between z-20 relative select-none backdrop-blur-xl"
    >
      {/* Top Navigation Items */}
      <div>
        <div className="p-3 border-b border-slate-800/60 flex items-center justify-between">
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="w-8 h-8 rounded-xl bg-cyan-950 border border-cyan-500/50 flex items-center justify-center text-cyan-400 shrink-0">
              <Sparkles className="w-4 h-4" />
            </div>
            {isExpanded && (
              <span className="text-xs font-bold text-slate-200 truncate">
                COMMAND RAIL
              </span>
            )}
          </div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            {isExpanded ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
        </div>

        <nav className="p-2 space-y-1 mt-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={item.action}
                className={`w-full flex items-center justify-between p-2.5 rounded-xl transition-all ${
                  item.highlight
                    ? 'bg-amber-950/60 border border-amber-600/60 text-amber-300 shadow-md'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/80'
                }`}
                title={!isExpanded ? item.label : undefined}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Icon className={`w-4 h-4 shrink-0 ${item.highlight ? 'text-amber-400' : 'text-slate-400'}`} />
                  {isExpanded && (
                    <span className="text-xs font-semibold truncate">{item.label}</span>
                  )}
                </div>

                {item.badge && (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded-full font-bold ${
                      item.highlight
                        ? 'bg-amber-500 text-slate-950'
                        : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Rail Footer */}
      <div className="p-2 border-t border-slate-800/80">
        <div className="flex items-center gap-2 p-2 rounded-xl text-slate-500 text-[10px] font-mono">
          <Activity className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          {isExpanded && <span>SYSTEM ONLINE</span>}
        </div>
      </div>
    </motion.aside>
  );
};
