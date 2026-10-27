import React from 'react';
import { motion } from 'framer-motion';
import { AgentRole } from '../../types/office';
import { WORKSPACE_COORDINATES } from '../../services/initialData';

interface DataFlowBeamsProps {
  activeConnections: Array<{
    id: string;
    fromRole: AgentRole;
    toRole: AgentRole;
    label?: string;
    type?: 'normal' | 'conflict' | 'resolved';
  }>;
}

export const DataFlowBeams: React.FC<DataFlowBeamsProps> = ({ activeConnections }) => {
  const coords = WORKSPACE_COORDINATES as Record<string, { x: number; y: number; width: number; height: number }>;

  // Permanent DAG Pipeline Connections
  const permanentDagPipelines = [
    { from: 'product_workspace', to: 'engineering_workspace' },
    { from: 'aiml_workspace', to: 'engineering_workspace' },
    { from: 'engineering_workspace', to: 'ux_workspace' },
    { from: 'engineering_workspace', to: 'security_workspace' },
    { from: 'engineering_workspace', to: 'qa_workspace' },
    { from: 'ux_workspace', to: 'conflict_room' },
    { from: 'security_workspace', to: 'conflict_room' },
    { from: 'qa_workspace', to: 'conflict_room' },
    { from: 'conflict_room', to: 'architect_office' },
  ];

  return (
    <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
      <defs>
        <linearGradient id="beam-normal" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#00f2fe" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#4facfe" stopOpacity="0.8" />
        </linearGradient>
        <linearGradient id="beam-conflict" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#ef4444" stopOpacity="0.9" />
        </linearGradient>
        <linearGradient id="beam-resolved" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#10b981" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.9" />
        </linearGradient>

        {/* 24px Architectural Grid Pattern */}
        <pattern id="dot-grid" x="0" y="0" width="24" height="24" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="2" r="1.2" className="fill-slate-800/40" />
        </pattern>
      </defs>

      {/* Grid Pattern Fill */}
      <rect width="100%" height="100%" fill="url(#dot-grid)" />

      {/* 1. Permanent DAG Base Flow Lines */}
      {permanentDagPipelines.map((pipe, idx) => {
        const fromC = coords[pipe.from];
        const toC = coords[pipe.to];
        if (!fromC || !toC) return null;

        const x1 = fromC.x + fromC.width / 2;
        const y1 = fromC.y + fromC.height / 2;
        const x2 = toC.x + toC.width / 2;
        const y2 = toC.y + toC.height / 2;

        const cx = (x1 + x2) / 2;
        const cy = (y1 + y2) / 2 - 20;

        return (
          <g key={`dag-${idx}`}>
            <path
              d={`M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`}
              fill="none"
              stroke="#1e293b"
              strokeWidth="2"
              strokeDasharray="4 4"
              opacity="0.6"
            />
          </g>
        );
      })}

      {/* 2. Active Animated Connection Rays */}
      {activeConnections.map((conn) => {
        const fromCoord = coords[`${conn.fromRole}_workspace`] || coords.collaboration_table;
        const toCoord = coords[`${conn.toRole}_workspace`] || coords.conflict_room;

        if (!fromCoord || !toCoord) return null;

        const x1 = fromCoord.x + fromCoord.width / 2;
        const y1 = fromCoord.y + fromCoord.height / 2;
        const x2 = toCoord.x + toCoord.width / 2;
        const y2 = toCoord.y + toCoord.height / 2;

        const cx = (x1 + x2) / 2;
        const cy = (y1 + y2) / 2 - 50;

        const pathD = `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;

        const strokeColor =
          conn.type === 'conflict'
            ? 'url(#beam-conflict)'
            : conn.type === 'resolved'
            ? 'url(#beam-resolved)'
            : 'url(#beam-normal)';

        return (
          <g key={conn.id}>
            <path
              d={pathD}
              fill="none"
              stroke={strokeColor}
              strokeWidth="4"
              strokeLinecap="round"
              opacity="0.3"
            />
            <motion.path
              d={pathD}
              fill="none"
              stroke={strokeColor}
              strokeWidth="3"
              strokeDasharray="8 6"
              initial={{ strokeDashoffset: 100 }}
              animate={{ strokeDashoffset: 0 }}
              transition={{ repeat: Infinity, duration: 1.2, ease: 'linear' }}
            />
          </g>
        );
      })}
    </svg>
  );
};
