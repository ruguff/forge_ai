import React from 'react';
import { motion } from 'framer-motion';
import { PixelCharacter } from './PixelCharacter';
import { useOffice } from '../../context/OfficeContext';

interface PixelReceptionDeskProps {
  onOpenIntake: () => void;
  onOpenRequirements: () => void;
}

export const PixelReceptionDesk: React.FC<PixelReceptionDeskProps> = ({
  onOpenIntake,
  onOpenRequirements,
}) => {
  const { pipelineStage, activeClarification, projectContext } = useOffice();

  const isUnderstanding = pipelineStage === 'UNDERSTANDING' || pipelineStage === 'REQUIREMENTS';

  return (
    <div className="absolute left-1/2 top-[170px] -translate-x-1/2 flex flex-col items-center select-none z-15">
      {/* 1. Large Woven Carpet with Branded Text */}
      <div className="w-[380px] h-[190px] pixel-rug rounded-xl flex flex-col items-center justify-between p-3 relative">
        {/* Subtle Carpet Geometric Border */}
        <div className="w-full h-full border-2 border-[#5c371d]/60 rounded-lg flex flex-col items-center justify-between p-2">
          {/* Top Space for Character behind desk */}
          <div className="relative -top-7 z-20">
            <PixelCharacter
              role="product_manager"
              name="Elena (Host)"
              status={isUnderstanding ? 'WORKING' : 'IDLE'}
              bubbleType={activeClarification ? 'warning' : isUnderstanding ? 'idea' : 'document'}
              bubbleText={activeClarification ? 'DECISION!' : isUnderstanding ? '17D PARSING' : undefined}
              scale={1.1}
              onClick={onOpenRequirements}
            />
          </div>

          {/* Curved Reception Counter Desk */}
          <motion.div
            whileHover={{ scale: 1.02 }}
            onClick={onOpenIntake}
            className="w-[240px] h-[72px] bg-gradient-to-b from-[#cbd5e1] to-[#94a3b8] border-4 border-[#475569] rounded-b-[40px] rounded-t-lg shadow-2xl relative flex items-center justify-center cursor-pointer group"
          >
            {/* Desktop Computer Monitor */}
            <div className="absolute -top-6 w-12 h-10 bg-slate-800 border-2 border-slate-600 rounded flex flex-col items-center justify-center shadow-md">
              <div className="w-10 h-7 bg-cyan-900 border border-cyan-400 rounded-sm flex items-center justify-center">
                <span className="text-[6px] font-pixel text-cyan-300 animate-pulse font-bold">17D</span>
              </div>
              <div className="w-4 h-1.5 bg-slate-600 rounded-b" />
            </div>

            {/* Desk Counter Surface Items: Mousepad, Pen Stand, Papers */}
            <div className="absolute left-5 top-2 w-7 h-4 bg-blue-900/60 rounded-sm border border-blue-400/40" />
            <div className="absolute right-6 top-2 w-5 h-5 bg-amber-800/80 rounded-full border border-amber-900" />

            {/* Front Desk Panel Label */}
            <div className="mt-3 text-center">
              <span className="text-[9px] font-pixel text-slate-900 tracking-wider font-extrabold uppercase">
                RECEPTION & INTAKE
              </span>
            </div>
          </motion.div>

          {/* Large Retro Pixel Text on Rug: "PROJECTFORGE" (Replaces "CHATDEV") */}
          <div className="text-center py-0.5">
            <span
              className="text-xl sm:text-2xl font-arcade font-extrabold tracking-widest text-[#4a2e1b] uppercase drop-shadow-[1px_1px_0px_rgba(255,255,255,0.4)]"
              style={{ letterSpacing: '0.25em' }}
            >
              PROJECTFORGE
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
