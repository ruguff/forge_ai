import React from 'react';
import { useOffice } from '../../context/OfficeContext';
import { Activity, CheckCircle2, AlertCircle, Info, Bell } from 'lucide-react';

export const ActivityFeed: React.FC = () => {
  const { activityFeed } = useOffice();

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
    <div className="h-28 bg-slate-950/90 border-t border-slate-800 px-6 py-2 flex flex-col backdrop-blur-md">
      <div className="flex items-center gap-2 pb-1 border-b border-slate-800/60 text-[11px] font-bold uppercase tracking-wider text-slate-400">
        <Activity className="w-3.5 h-3.5 text-cyan-400" />
        <span>Live Multi-Agent Event Stream ({activityFeed.length})</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1 mt-1 pr-2">
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
      </div>
    </div>
  );
};
