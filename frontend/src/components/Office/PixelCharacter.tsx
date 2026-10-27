import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { AgentRole, AgentStatus } from '../../types/office';

interface PixelCharacterProps {
  role: AgentRole;
  name: string;
  status: AgentStatus;
  direction?: 'down' | 'up' | 'left' | 'right';
  bubbleType?: 'lightbulb' | 'document' | 'warning' | 'code' | 'bug' | 'scale' | 'idea' | 'text';
  bubbleText?: string;
  currentTask?: string;
  isSeated?: boolean;
  facingBack?: boolean;
  scale?: number;
  isZoomedIn?: boolean;
  onClick?: () => void;
}

export const AGENT_PERSONALITIES: Record<
  AgentRole,
  {
    fullName: string;
    shortName: string;
    title: string;
    accentColor: string;
    defaultTask: string;
    hair: string;
    hairShade: string;
    skin: string;
    shirt: string;
    pants: string;
    eye: string;
  }
> = {
  product_manager: {
    fullName: 'Elena Rostova',
    shortName: 'Elena',
    title: 'Product Lead',
    accentColor: '#10B981',
    defaultTask: 'PRD & 17D Architecture Scope',
    hair: '#e6683b',
    hairShade: '#b8441d',
    skin: '#fed0ad',
    shirt: '#10b981',
    pants: '#0f172a',
    eye: '#065f46',
  },
  aiml_architect: {
    fullName: 'Dr. Aris Thorne',
    shortName: 'Aris',
    title: 'AI/ML Agent',
    accentColor: '#A855F7',
    defaultTask: 'Model evaluation & embeddings',
    hair: '#e2e8f0',
    hairShade: '#94a3b8',
    skin: '#fbd7b5',
    shirt: '#9333ea',
    pants: '#1e293b',
    eye: '#6b21a8',
  },
  engineering_lead: {
    fullName: 'Marcus Vance',
    shortName: 'Marcus',
    title: 'Engineering Lead',
    accentColor: '#3B82F6',
    defaultTask: 'API & schema design',
    hair: '#38bdf8',
    hairShade: '#0284c7',
    skin: '#fed0ad',
    shirt: '#2563eb',
    pants: '#0f172a',
    eye: '#1e40af',
  },
  ux_designer: {
    fullName: 'Sora Takahashi',
    shortName: 'Sora',
    title: 'UX Studio Lead',
    accentColor: '#EC4899',
    defaultTask: 'Design token & flow spec',
    hair: '#ec4899',
    hairShade: '#be185d',
    skin: '#fde0c2',
    shirt: '#db2777',
    pants: '#334155',
    eye: '#9d174d',
  },
  security_auditor: {
    fullName: 'Kaelen Cross',
    shortName: 'Kaelen',
    title: 'Security Auditor',
    accentColor: '#EF4444',
    defaultTask: 'Threat modeling & audit',
    hair: '#64748b',
    hairShade: '#334155',
    skin: '#fad2b2',
    shirt: '#dc2626',
    pants: '#0f172a',
    eye: '#991b1b',
  },
  qa_strategist: {
    fullName: 'Devon Reed',
    shortName: 'Devon',
    title: 'QA Strategist',
    accentColor: '#F59E0B',
    defaultTask: 'Regression & SLA validation',
    hair: '#f59e0b',
    hairShade: '#b45309',
    skin: '#fed0ad',
    shirt: '#d97706',
    pants: '#78350f',
    eye: '#92400e',
  },
  conflict_resolver: {
    fullName: 'Lex',
    shortName: 'Lex',
    title: 'Conflict Arbiter',
    accentColor: '#06B6D4',
    defaultTask: 'ADR & trade-off arbitration',
    hair: '#06b6d4',
    hairShade: '#0891b2',
    skin: '#fce3cd',
    shirt: '#0891b2',
    pants: '#164e63',
    eye: '#155e75',
  },
  blueprint_architect: {
    fullName: 'Prime',
    shortName: 'Prime',
    title: 'Final Architect',
    accentColor: '#6366F1',
    defaultTask: 'Master Blueprint synthesis',
    hair: '#8b5cf6',
    hairShade: '#6d28d9',
    skin: '#fed0ad',
    shirt: '#4f46e5',
    pants: '#1e1b4b',
    eye: '#3730a3',
  },
  coding_agent: {
    fullName: 'Qwen3-Coder',
    shortName: 'Coder',
    title: 'Coding Agent',
    accentColor: '#22C55E',
    defaultTask: 'Implement generated architecture',
    hair: '#22c55e',
    hairShade: '#15803d',
    skin: '#fbd7b5',
    shirt: '#16a34a',
    pants: '#14532d',
    eye: '#166534',
  },
};

export const PixelCharacter: React.FC<PixelCharacterProps> = ({
  role,
  name,
  status,
  bubbleType,
  bubbleText,
  currentTask,
  isSeated = false,
  facingBack = false,
  scale = 1,
  isZoomedIn = false,
  onClick,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const personality = AGENT_PERSONALITIES[role] || AGENT_PERSONALITIES.engineering_lead;
  const isWorking = status === 'WORKING';
  const isDiscussing = status === 'DISCUSSING';
  const isConflict = status === 'CONFLICT';

  const statusLabel =
    isConflict
      ? 'CONFLICT'
      : isDiscussing
      ? 'DISCUSSING'
      : isWorking
      ? 'WORKING'
      : status || 'IDLE';

  const statusDotColor =
    status === 'WORKING'
      ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]'
      : status === 'DISCUSSING'
      ? 'bg-purple-400 shadow-[0_0_8px_#c084fc]'
      : status === 'CONFLICT'
      ? 'bg-cyan-400 shadow-[0_0_8px_#22d3ee]'
      : 'bg-slate-400';

  const showDetailed = isZoomedIn || isHovered;

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="relative flex flex-col items-center select-none cursor-pointer group"
      style={{ transform: `scale(${scale})` }}
    >
      {/* 1. Retro Pixel Speech Bubble (if active, warning, code, etc.) */}
      {(bubbleType || bubbleText || isDiscussing || isWorking) && (
        <motion.div
          initial={{ opacity: 0, y: 4, scale: 0.8 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          className="absolute -top-12 z-30 pixel-bubble px-2 py-0.5 flex items-center justify-center min-w-[28px] min-h-[24px] pointer-events-none"
        >
          {bubbleType === 'lightbulb' && <span className="text-sm">💡</span>}
          {bubbleType === 'document' && (
            <svg className="w-3.5 h-3.5 text-blue-600" viewBox="0 0 16 16" fill="currentColor">
              <path d="M4 1h5l4 4v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1zm4 1v3h3L8 2zM5 8h6v1H5V8zm0 2h6v1H5v-1zm0 2h4v1H5v-1z" />
            </svg>
          )}
          {bubbleType === 'warning' && <span className="text-xs">⚠️</span>}
          {bubbleType === 'code' && (
            <span className="text-[8px] font-pixel font-bold text-blue-800 tracking-tighter">main()</span>
          )}
          {bubbleType === 'bug' && (
            <div className="flex items-center text-xs">
              <span className="text-red-500 font-bold text-xs">🚫</span>
              <span className="text-xs">🐛</span>
            </div>
          )}
          {bubbleType === 'scale' && <span className="text-xs">⚖️</span>}
          {bubbleType === 'idea' && <span className="text-xs">✨</span>}
          {bubbleText && (
            <span className="text-[8px] font-pixel font-bold text-slate-900 truncate max-w-[84px]">
              {bubbleText}
            </span>
          )}
          {!bubbleType && !bubbleText && isDiscussing && (
            <span className="text-[8px] font-pixel text-purple-700 font-bold">...</span>
          )}
          {!bubbleType && !bubbleText && isWorking && (
            <span className="text-[8px] font-pixel text-emerald-700 font-bold">⚙️</span>
          )}
        </motion.div>
      )}

      {/* 2. Authentic 16-bit SVG Pixel Character (48px x 60px) */}
      <motion.div
        animate={
          isDiscussing
            ? { y: [0, -3, 0], rotate: [0, -1, 1, 0] }
            : isWorking
            ? { y: [0, -1.5, 0] }
            : { y: [0, -1, 0] }
        }
        transition={{
          repeat: Infinity,
          duration: isDiscussing ? 0.6 : isWorking ? 0.8 : 2.5,
          ease: 'easeInOut',
        }}
        className="w-[48px] h-[60px] relative"
      >
        <svg
          viewBox="0 0 22 28"
          className="w-full h-full pixelated drop-shadow-[0_4px_4px_rgba(0,0,0,0.4)]"
          shapeRendering="crispEdges"
        >
          {facingBack ? (
            /* Character Viewed From Back */
            <g>
              <rect x="5" y="2" width="12" height="10" fill={personality.hair} />
              <rect x="4" y="4" width="14" height="8" fill={personality.hair} />
              <rect x="6" y="1" width="10" height="2" fill={personality.hair} />
              <rect x="6" y="10" width="10" height="3" fill={personality.hairShade} />

              <rect x="6" y="13" width="10" height="8" fill={personality.shirt} />
              <rect x="4" y="14" width="2" height="6" fill={personality.shirt} />
              <rect x="16" y="14" width="2" height="6" fill={personality.shirt} />

              <rect x="6" y="21" width="4" height="5" fill={personality.pants} />
              <rect x="12" y="21" width="4" height="5" fill={personality.pants} />

              <rect x="5" y="26" width="5" height="2" fill="#1e293b" />
              <rect x="12" y="26" width="5" height="2" fill="#1e293b" />
            </g>
          ) : (
            /* Character Viewed From Front */
            <g>
              {/* Hair Top */}
              <rect x="5" y="2" width="12" height="5" fill={personality.hair} />
              <rect x="4" y="3" width="14" height="6" fill={personality.hair} />
              <rect x="6" y="1" width="10" height="2" fill={personality.hair} />

              {/* Face */}
              <rect x="5" y="6" width="12" height="7" fill={personality.skin} />

              {/* Bangs */}
              <rect x="5" y="4" width="3" height="3" fill={personality.hairShade} />
              <rect x="14" y="4" width="3" height="3" fill={personality.hairShade} />
              <rect x="8" y="3" width="6" height="2" fill={personality.hairShade} />

              {/* Eyes */}
              <rect x="6" y="8" width="3" height="3" fill="#ffffff" />
              <rect x="7" y="8" width="2" height="2" fill={personality.eye} />
              <rect x="7" y="8" width="1" height="1" fill="#000000" />

              <rect x="13" y="8" width="3" height="3" fill="#ffffff" />
              <rect x="13" y="8" width="2" height="2" fill={personality.eye} />
              <rect x="14" y="8" width="1" height="1" fill="#000000" />

              {/* Blush */}
              <rect x="5" y="11" width="2" height="1" fill="#f87171" opacity="0.6" />
              <rect x="15" y="11" width="2" height="1" fill="#f87171" opacity="0.6" />

              {/* Mouth */}
              <rect x="10" y="11" width="2" height="1" fill="#991b1b" />

              {/* Shirt & Role Badge */}
              <rect x="6" y="13" width="10" height="7" fill={personality.shirt} />
              <rect x="10" y="13" width="2" height="2" fill="#ffffff" />
              <rect x="10" y="15" width="2" height="3" fill={personality.accentColor} />

              {/* Arms */}
              <rect x="4" y="14" width="2" height="5" fill={personality.shirt} />
              <rect x="4" y="19" width="2" height="2" fill={personality.skin} />
              <rect x="16" y="14" width="2" height="5" fill={personality.shirt} />
              <rect x="16" y="19" width="2" height="2" fill={personality.skin} />

              {/* Pants & Shoes */}
              {!isSeated && (
                <>
                  <rect x="6" y="20" width="4" height="6" fill={personality.pants} />
                  <rect x="12" y="20" width="4" height="6" fill={personality.pants} />
                  <rect x="5" y="26" width="5" height="2" fill="#1e293b" />
                  <rect x="12" y="26" width="5" height="2" fill="#1e293b" />
                </>
              )}
            </g>
          )}
        </svg>
      </motion.div>

      {/* 3. Responsive Floating Nameplate */}
      <div
        className={`mt-1 rounded-md px-2 py-1 shadow-lg backdrop-blur-md transition-all duration-200 text-center ${
          showDetailed
            ? 'bg-slate-950/95 border-2 min-w-[120px] max-w-[140px] z-30'
            : 'bg-slate-900/90 border min-w-[70px] max-w-[90px] z-10'
        }`}
        style={{ borderColor: personality.accentColor }}
      >
        {showDetailed ? (
          /* Detailed Zoomed/Hovered Nameplate */
          <div className="flex flex-col items-center gap-0.5">
            <div className="flex items-center gap-1">
              <span className={`w-1.5 h-1.5 rounded-full ${statusDotColor}`} />
              <span className="text-[7px] font-pixel font-bold tracking-wider" style={{ color: personality.accentColor }}>
                {statusLabel}
              </span>
            </div>
            <div className="text-[9px] font-pixel text-slate-100 font-extrabold truncate w-full">
              {personality.fullName}
            </div>
            <div className="text-[7px] font-mono text-slate-300 font-medium">
              {personality.title}
            </div>
            <div className="text-[6.5px] font-mono text-slate-400 truncate w-full border-t border-slate-800 pt-0.5 mt-0.5">
              {currentTask || personality.defaultTask}
            </div>
          </div>
        ) : (
          /* Compact Zoomed-Out Nameplate */
          <div className="flex items-center justify-center gap-1">
            <span className={`w-1.5 h-1.5 rounded-full ${statusDotColor}`} />
            <span className="text-[8px] font-pixel text-slate-100 font-bold truncate">
              {personality.shortName}
            </span>
            <span className="text-[7px] font-mono text-slate-400 font-medium">
              | {personality.title.split(' ')[0]}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
