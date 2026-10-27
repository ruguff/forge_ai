import React from 'react';
import { motion } from 'framer-motion';

export interface DataBeam {
  id: string;
  from: { x: number; y: number };
  to: { x: number; y: number };
  color?: string;
  label?: string;
}

interface PixelDataFlowBeamsProps {
  beams: DataBeam[];
}

export const PixelDataFlowBeams: React.FC<PixelDataFlowBeamsProps> = ({ beams }) => {
  if (!beams || beams.length === 0) return null;

  return (
    <svg className="absolute inset-0 w-full h-full pointer-events-none z-18">
      <defs>
        {beams.map((beam) => (
          <linearGradient
            key={`grad-${beam.id}`}
            id={`beam-grad-${beam.id}`}
            gradientUnits="userSpaceOnUse"
            x1={beam.from.x}
            y1={beam.from.y}
            x2={beam.to.x}
            y2={beam.to.y}
          >
            <stop offset="0%" stopColor={beam.color || '#38bdf8'} stopOpacity="0.2" />
            <stop offset="50%" stopColor={beam.color || '#38bdf8'} stopOpacity="0.9" />
            <stop offset="100%" stopColor={beam.color || '#38bdf8'} stopOpacity="0.2" />
          </linearGradient>
        ))}
      </defs>

      {beams.map((beam) => {
        const midX = (beam.from.x + beam.to.x) / 2;
        const midY = (beam.from.y + beam.to.y) / 2 - 20;
        const pathD = `M ${beam.from.x} ${beam.from.y} Q ${midX} ${midY} ${beam.to.x} ${beam.to.y}`;

        return (
          <g key={beam.id}>
            {/* Base Faint Path */}
            <path
              d={pathD}
              fill="none"
              stroke={beam.color || '#38bdf8'}
              strokeWidth="2"
              strokeDasharray="4 4"
              opacity="0.3"
            />

            {/* Glowing Flowing Pulse Beam */}
            <motion.path
              d={pathD}
              fill="none"
              stroke={`url(#beam-grad-${beam.id})`}
              strokeWidth="3"
              strokeDasharray="12 18"
              animate={{ strokeDashoffset: [-60, 0] }}
              transition={{ repeat: Infinity, duration: 1.2, ease: 'linear' }}
            />

            {/* Optional Floating Event Label */}
            {beam.label && (
              <text
                x={midX}
                y={midY - 6}
                textAnchor="middle"
                className="text-[7px] font-pixel font-bold fill-cyan-300 drop-shadow"
              >
                {beam.label}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
};
