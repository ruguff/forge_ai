import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import { Activity, ChevronUp, ChevronDown, CheckCircle2, AlertCircle, Info } from 'lucide-react';

export const ActivityBar: React.FC = () => {
  const { activityFeed } = useOffice();
  const [isExpanded, setIsExpanded] = useState(false);

  const latestEvent = activityFeed[0];

  const getSeverityIcon = (sev: string = 'info') => {
    switch (sev) {
      case 'success':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />;
      case 'warning':
      case 'error':
        return <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />;
      default:
        return <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0" />;
    }
  };

  return (
    <footer className="h-[36px] bg-slate-950 border-t border-slate-800/80 px-4 flex items-center justify-between text-xs z-30 relative select-none backdrop-blur-xl">
      {/* Latest Live Stream Item */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-cyan-400 font-mono shrink-0">
          <Activity className="w-3.5 h-3.5" />
          <span>Live Events ({activityFeed.length})</span>
        </div>

        <div className="h-4 w-[1px] bg-slate-800 shrink-0" />

        {latestEvent ? (
          <div className="flex items-center gap-2 text-xs truncate">
            <span className="font-mono text-[10px] text-slate-500 shrink-0">{latestEvent.timestamp}</span>
            {getSeverityIcon(latestEvent.severity)}
            {latestEvent.agentName && (
              <span className="font-semibold text-cyan-300 font-mono text-[11px] shrink-0">
                [{latestEvent.agentName}]:
              </span>
            )}
            <span className="text-slate-300 truncate">{latestEvent.message}</span>
          </div>
        ) : (
          <span className="text-slate-500 text-xs italic">Awaiting pipeline events...</span>
        )}
      </div>

      {/* Toggle Drawer Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-[10px] font-mono text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-lg transition-colors ml-3 shrink-0"
      >
        <span>{isExpanded ? 'Hide Stream' : 'Expand Stream'}</span>
        {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
      </button>

      {/* Expandable Feed Drawer */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, y: 100 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 100 }}
            className="absolute left-0 right-0 bottom-[36px] bg-slate-950/95 border-t border-slate-800 p-4 max-h-60 overflow-y-auto shadow-2xl space-y-1.5 backdrop-blur-2xl z-40"
          >
            <div className="text-[10px] font-bold font-mono text-slate-400 uppercase tracking-wider mb-2 pb-1 border-b border-slate-800">
              Chronological Multi-Agent Activity Log
            </div>
            {activityFeed.map((evt) => (
              <div key={evt.id} className="flex items-center gap-2.5 text-xs py-0.5">
                <span className="font-mono text-[10px] text-slate-500 shrink-0">{evt.timestamp}</span>
                {getSeverityIcon(evt.severity)}
                {evt.agentName && (
                  <span className="font-semibold text-cyan-300 font-mono text-[11px] shrink-0">
                    [{evt.agentName}]:
                  </span>
                )}
                <span className="text-slate-300 truncate">{evt.message}</span>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </footer>
  );
};
