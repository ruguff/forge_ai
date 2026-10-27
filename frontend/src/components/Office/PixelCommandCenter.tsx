import React from 'react';
import { motion } from 'framer-motion';
import { PixelCharacter } from './PixelCharacter';
import { useOffice } from '../../context/OfficeContext';
import { Sparkles, Terminal, Activity } from 'lucide-react';

interface PixelCommandCenterProps {
  onOpenIntake: () => void;
  onOpenRequirements: () => void;
}

export const PixelCommandCenter: React.FC<PixelCommandCenterProps> = ({
  onOpenIntake,
  onOpenRequirements,
}) => {
  const {
    pipelineStage,
    activeClarification,
    projectContext,
    projectIdea,
    projectId,
    agents,
  } = useOffice();

  const isUnderstanding =
    pipelineStage === 'UNDERSTANDING' || pipelineStage === 'REQUIREMENTS';

  const projectName =
    projectContext?.project_name ||
    (projectIdea
      ? projectIdea.length > 24
        ? projectIdea.substring(0, 24) + '...'
        : projectIdea
      : 'Cake and Joy Platform');

  // Count active agents
  const activeCount = Object.values(agents).filter(
    (a) => a.status === 'WORKING' || a.status === 'DISCUSSING' || a.status === 'CONFLICT'
  ).length;

  const pipelineStagesList = [
    { key: 'UNDERSTANDING', label: 'Understand' },
    { key: 'REQUIREMENTS', label: 'Requirements' },
    { key: 'CORE_ANALYSIS', label: 'Analysis' },
    { key: 'DISCUSSION', label: 'Discussion' },
    { key: 'CONFLICT_RESOLUTION', label: 'Arbitration' },
    { key: 'ARCHITECTURE', label: 'Architecture' },
    { key: 'BUILD', label: 'Build' },
    { key: 'TEST', label: 'Test' },
    { key: 'SHIP', label: 'Ship' },
  ];

  const stageOrder = [
    'NOT_STARTED',
    'UNDERSTANDING',
    'REQUIREMENTS',
    'CORE_ANALYSIS',
    'ENGINEERING_ANALYSIS',
    'DISCUSSION',
    'CONFLICT_RESOLUTION',
    'ARBITRATION',
    'ARCHITECTURE',
    'FINAL_SYNTHESIS',
    'BUILD',
    'TEST',
    'VERIFICATION',
    'SHIP',
    'COMPLETED',
  ];

  const getStageIndicator = (key: string) => {
    if (pipelineStage === 'COMPLETED') return '✓';
    if (pipelineStage === key) return '●';
    const curIdx = stageOrder.indexOf(pipelineStage);
    const keyIdx = stageOrder.indexOf(key);
    if (keyIdx < curIdx) return '✓';
    return '○';
  };

  return (
    <div className="flex flex-col items-center select-none z-15 w-[460px]">
      {/* 1. Woven Rug with "PROJECTFORGE AI" Branded Border */}
      <div className="w-full pixel-rug rounded-2xl p-2.5 flex flex-col items-center justify-between relative shadow-xl">
        {/* Top Space for Host Character (Elena) */}
        <div className="relative -top-6 z-20">
          <PixelCharacter
            role="product_manager"
            name="Elena (Host)"
            status={isUnderstanding ? 'WORKING' : 'IDLE'}
            bubbleType={activeClarification ? 'warning' : isUnderstanding ? 'idea' : undefined}
            bubbleText={activeClarification ? 'DECISION!' : isUnderstanding ? '17D PARSING' : undefined}
            currentTask="Autonomous Intake & 17D Scope"
            scale={1.05}
            onClick={onOpenRequirements}
          />
        </div>

        {/* 2. Curved Central Command Desk & Screen */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          onClick={onOpenIntake}
          className="w-full bg-[#1e293b]/90 border-3 border-[#475569] rounded-xl shadow-2xl p-2.5 relative flex flex-col gap-1.5 cursor-pointer backdrop-blur-md"
        >
          {/* Top Row: Brand & Live Phase */}
          <div className="flex items-center justify-between border-b border-slate-700/80 pb-1">
            <div className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-[10px] font-arcade font-extrabold text-yellow-300 tracking-wider">
                PROJECTFORGE AI
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[7.5px] font-pixel text-slate-300 bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-600">
                ACTIVE: <span className="text-cyan-400 font-bold">{Math.max(1, activeCount)} / 8</span>
              </span>
              <span className="text-[7.5px] font-pixel text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-700/60">
                {pipelineStage.replace('_', ' ')}
              </span>
            </div>
          </div>

          {/* Middle Row: Current Project Name & ID */}
          <div className="flex items-center justify-between text-[8px] font-mono text-slate-300 px-1">
            <div className="flex items-center gap-1 truncate max-w-[280px]">
              <span className="text-slate-400">PROJECT:</span>
              <span className="font-bold text-white truncate">{projectName}</span>
            </div>
            <span className="text-cyan-400/80 font-mono text-[7px]">{projectId}</span>
          </div>

          {/* Bottom Row: Compact Pipeline Track */}
          <div className="w-full bg-slate-900/90 rounded-md p-1 border border-slate-700/60 flex items-center justify-between text-[6.5px] font-pixel">
            {pipelineStagesList.map((stg) => {
              const indicator = getStageIndicator(stg.key);
              const isActive = indicator === '●';
              const isDone = indicator === '✓';
              return (
                <div
                  key={stg.key}
                  className={`flex flex-col items-center ${
                    isActive
                      ? 'text-cyan-300 font-bold'
                      : isDone
                      ? 'text-emerald-400'
                      : 'text-slate-500'
                  }`}
                >
                  <span>{stg.label}</span>
                  <span className="text-[8px] leading-none mt-0.5">{indicator}</span>
                </div>
              );
            })}
          </div>
        </motion.div>
      </div>
    </div>
  );
};
