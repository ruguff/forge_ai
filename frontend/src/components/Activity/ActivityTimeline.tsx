import React from 'react';
import { motion } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import { FeedEvent, AgentRole } from '../../types/office';
import {
  Terminal,
  ChevronUp,
  ChevronDown,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Sparkles,
} from 'lucide-react';

interface ActivityTimelineProps {
  isExpanded: boolean;
  onToggleExpand: () => void;
}

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({
  isExpanded,
  onToggleExpand,
}) => {
  const { activityFeed, focusCameraOnTarget, selectAgent } = useOffice();

  const handleEventClick = (event: FeedEvent) => {
    if (event.agentRole) {
      selectAgent(event.agentRole);
      focusCameraOnTarget(event.agentRole, 1.3);
    }
  };

  const getEventIcon = (severity?: string) => {
    switch (severity) {
      case 'success':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />;
      case 'warning':
        return <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />;
      case 'error':
        return <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0" />;
      default:
        return <ArrowRight className="w-3.5 h-3.5 text-cyan-400 shrink-0" />;
    }
  };

  return (
    <div className="fixed bottom-0 inset-x-0 z-20 select-none">
      <div className="max-w-4xl mx-auto px-4">
        {/* Collapsible Panel */}
        <div className="bg-slate-950/95 border-t border-x border-slate-800/90 rounded-t-2xl shadow-2xl backdrop-blur-xl overflow-hidden">
          {/* Header Bar */}
          <div
            onClick={onToggleExpand}
            className="px-4 py-2 flex items-center justify-between cursor-pointer hover:bg-slate-900/60 transition-colors border-b border-slate-900"
          >
            <div className="flex items-center gap-2">
              <Terminal className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-xs font-mono font-bold text-slate-200">
                Live Execution Activity Stream
              </span>
              <span className="text-[10px] bg-slate-900 text-cyan-400 px-2 py-0.2 rounded-full border border-slate-800 font-mono">
                {activityFeed.length} events
              </span>
            </div>

            {/* Latest Event Teaser when collapsed */}
            {!isExpanded && activityFeed[0] && (
              <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400 truncate max-w-md font-mono">
                {getEventIcon(activityFeed[0].severity)}
                <span className="truncate">{activityFeed[0].message}</span>
              </div>
            )}

            <button className="text-slate-400 hover:text-slate-200 p-0.5">
              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
            </button>
          </div>

          {/* Expanded Event Log */}
          {isExpanded && (
            <motion.div
              initial={{ height: 0 }}
              animate={{ height: 180 }}
              exit={{ height: 0 }}
              className="p-3 overflow-y-auto space-y-1.5 font-mono text-[11px]"
            >
              {activityFeed.map((evt) => (
                <div
                  key={evt.id}
                  onClick={() => handleEventClick(evt)}
                  className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-xl hover:bg-slate-900/80 cursor-pointer transition-colors group"
                >
                  <span className="text-slate-600 text-[10px] shrink-0">{evt.timestamp}</span>
                  {getEventIcon(evt.severity)}
                  {evt.agentRole && (
                    <span className="text-cyan-400 font-bold shrink-0">
                      [{evt.agentName || evt.agentRole}]:
                    </span>
                  )}
                  <span className="text-slate-300 group-hover:text-slate-100 truncate">
                    {evt.message}
                  </span>
                </div>
              ))}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
};
