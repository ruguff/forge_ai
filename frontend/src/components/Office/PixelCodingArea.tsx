import React from 'react';
import { motion } from 'framer-motion';
import { PixelCharacter } from './PixelCharacter';
import { useOffice } from '../../context/OfficeContext';

interface PixelCodingAreaProps {
  onOpenCodeStream?: () => void;
}

export const PixelCodingArea: React.FC<PixelCodingAreaProps> = ({ onOpenCodeStream }) => {
  const { pipelineStage, buildTestState, agents } = useOffice();

  const isBuilding =
    pipelineStage === 'BUILD' ||
    pipelineStage === 'TEST' ||
    pipelineStage === 'SHIP' ||
    buildTestState.status === 'BUILDING' ||
    buildTestState.status === 'FIXING';

  return (
    <div className="absolute left-1/2 -translate-x-1/2 top-[440px] flex flex-col items-center select-none z-15">
      {/* 1. Wooden Signpost: "Coding" */}
      <div className="flex flex-col items-center -mb-2 z-20 cursor-pointer" onClick={onOpenCodeStream}>
        <div className="pixel-signpost px-4 py-1 rounded-md shadow-md text-center">
          <span className="text-[10px] font-pixel text-yellow-100 font-bold uppercase tracking-wider">
            Coding
          </span>
        </div>
        {/* Signpost Wooden Pole */}
        <div className="w-2.5 h-6 bg-[#4a2e1b] border-x border-[#2b180d]" />
      </div>

      {/* 2. Row of 3 Computer Workstations with Seated Coders */}
      <div className="flex items-end gap-3 p-2 bg-[#b48560]/40 rounded-2xl border-2 border-dashed border-[#8b5a35]/60 relative">
        {/* Standing Tech Lead / Engineer behind the coders with speech bubble */}
        <div className="absolute -top-10 -right-2 z-30">
          <PixelCharacter
            role="aiml_architect"
            name="Dr. Thorne"
            status={isBuilding ? 'WORKING' : 'IDLE'}
            bubbleType={isBuilding ? 'code' : 'warning'}
            bubbleText={isBuilding ? 'main()' : undefined}
            scale={0.9}
          />
        </div>

        {/* Station 1: Left Coder (Blonde Hair) */}
        <div className="flex flex-col items-center">
          {/* Computer Desk with CRT Monitor */}
          <div className="w-14 h-12 bg-[#cbd5e1] border-2 border-[#64748b] rounded-t-md shadow p-1 flex flex-col items-center justify-between">
            {/* Monitor Screen */}
            <div className="w-10 h-7 bg-[#0f172a] border border-[#38bdf8] rounded-sm p-0.5 overflow-hidden">
              <div className="text-[5px] font-mono text-emerald-400 font-bold leading-tight">
                {isBuilding ? 'def run():\n  api.post' : 'ready...'}
              </div>
            </div>
            {/* Keyboard */}
            <div className="w-8 h-2 bg-slate-400 rounded-sm" />
          </div>
          {/* Coder Seated Facing Away (Blonde / Devon) */}
          <div className="relative -top-2 z-20">
            <PixelCharacter
              role="qa_strategist"
              name="Devon"
              status={isBuilding ? 'WORKING' : 'IDLE'}
              facingBack
              isSeated
              scale={0.9}
            />
          </div>
        </div>

        {/* Station 2: Center Coder (Byte / Qwen3-Coder / Blue Hair) */}
        <div className="flex flex-col items-center">
          {/* Computer Desk with CRT Monitor */}
          <div className="w-14 h-12 bg-[#cbd5e1] border-2 border-[#64748b] rounded-t-md shadow p-1 flex flex-col items-center justify-between">
            {/* Monitor Screen */}
            <div className="w-10 h-7 bg-[#0f172a] border border-[#22c55e] rounded-sm p-0.5 overflow-hidden">
              <div className="text-[5px] font-mono text-cyan-300 font-bold leading-tight">
                {isBuilding ? 'FastAPI()\nStripe.v1' : 'standby'}
              </div>
            </div>
            {/* Keyboard */}
            <div className="w-8 h-2 bg-slate-400 rounded-sm" />
          </div>
          {/* Coder Seated Facing Away (Byte / Qwen3-Coder) */}
          <div className="relative -top-2 z-20">
            <PixelCharacter
              role="coding_agent"
              name="Byte"
              status={isBuilding ? 'WORKING' : 'IDLE'}
              facingBack
              isSeated
              scale={0.9}
            />
          </div>
        </div>

        {/* Station 3: Right Coder (Brown Hair / Marcus) */}
        <div className="flex flex-col items-center">
          {/* Computer Desk with CRT Monitor */}
          <div className="w-14 h-12 bg-[#cbd5e1] border-2 border-[#64748b] rounded-t-md shadow p-1 flex flex-col items-center justify-between">
            {/* Monitor Screen */}
            <div className="w-10 h-7 bg-[#0f172a] border border-[#a855f7] rounded-sm p-0.5 overflow-hidden">
              <div className="text-[5px] font-mono text-yellow-300 font-bold leading-tight">
                {isBuilding ? 'models.py\nPostgres' : 'idle'}
              </div>
            </div>
            {/* Keyboard */}
            <div className="w-8 h-2 bg-slate-400 rounded-sm" />
          </div>
          {/* Coder Seated Facing Away (Marcus Vance) */}
          <div className="relative -top-2 z-20">
            <PixelCharacter
              role="engineering_lead"
              name="Marcus"
              status={isBuilding ? 'WORKING' : 'IDLE'}
              facingBack
              isSeated
              scale={0.9}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
