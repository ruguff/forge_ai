import React from 'react';
import { useOffice } from '../../context/OfficeContext';
import { WORKSPACE_COORDINATES } from '../../services/initialData';
import { AgentRole, WorkspaceId } from '../../types/office';

export const Minimap: React.FC = () => {
  const { agents, focusCameraOnTarget } = useOffice();

  // Canvas bounds: 2150 x 920 mapped to 160 x 80
  const scaleX = 160 / 2150;
  const scaleY = 80 / 920;

  return (
    <div className="w-[170px] bg-slate-950/95 border border-slate-800 rounded-2xl p-2 shadow-2xl backdrop-blur-xl select-none">
      <div className="text-[9px] font-mono font-bold text-slate-400 uppercase tracking-wider mb-1 flex items-center justify-between">
        <span>Radar Minimap</span>
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
      </div>

      <div className="relative w-[160px] h-[80px] bg-slate-900/90 border border-slate-800 rounded-lg overflow-hidden">
        {/* Workspace Boxes */}
        {(Object.keys(WORKSPACE_COORDINATES) as WorkspaceId[]).map((wsId) => {
          const ws = WORKSPACE_COORDINATES[wsId];
          const isConflict = wsId === 'conflict_room';
          const isArchitect = wsId === 'architect_office';

          return (
            <div
              key={wsId}
              onClick={() => focusCameraOnTarget(wsId, 1.3)}
              className={`absolute rounded cursor-pointer transition-colors ${
                isConflict
                  ? 'bg-cyan-950/80 border border-cyan-600/50'
                  : isArchitect
                  ? 'bg-indigo-950/80 border border-indigo-600/50'
                  : 'bg-slate-800/40 border border-slate-700/30 hover:border-cyan-500/50'
              }`}
              style={{
                left: ws.x * scaleX,
                top: ws.y * scaleY,
                width: Math.max(ws.width * scaleX, 10),
                height: Math.max(ws.height * scaleY, 10),
              }}
            />
          );
        })}

        {/* Agent Dots */}
        {(Object.keys(agents) as AgentRole[]).map((role) => {
          const ag = agents[role];
          const isActive = ag.status === 'WORKING' || ag.status === 'DISCUSSING';

          return (
            <div
              key={role}
              onClick={() => focusCameraOnTarget(role, 1.3)}
              className={`absolute w-2 h-2 rounded-full transform -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-all ${
                isActive ? 'ring-2 ring-white scale-125 z-10' : ''
              }`}
              style={{
                left: ag.position.x * scaleX,
                top: ag.position.y * scaleY,
                backgroundColor: ag.accentColor,
              }}
              title={`${ag.name} (${ag.status})`}
            />
          );
        })}
      </div>
    </div>
  );
};
