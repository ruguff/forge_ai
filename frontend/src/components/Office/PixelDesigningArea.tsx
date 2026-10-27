import React from 'react';
import { motion } from 'framer-motion';
import { PixelCharacter } from './PixelCharacter';
import { useOffice } from '../../context/OfficeContext';

interface PixelDesigningAreaProps {
  onOpenRequirements: () => void;
}

export const PixelDesigningArea: React.FC<PixelDesigningAreaProps> = ({ onOpenRequirements }) => {
  const { agents } = useOffice();

  return (
    <div className="absolute left-[60px] top-[440px] flex flex-col items-center select-none z-15">
      {/* 1. Wooden Signpost: "Designing" */}
      <div className="flex flex-col items-center -mb-2 z-20 cursor-pointer" onClick={onOpenRequirements}>
        <div className="pixel-signpost px-3 py-1 rounded-md shadow-md text-center">
          <span className="text-[10px] font-pixel text-yellow-100 font-bold uppercase tracking-wider">
            Designing
          </span>
        </div>
        {/* Signpost Wooden Pole */}
        <div className="w-2.5 h-6 bg-[#4a2e1b] border-x border-[#2b180d]" />
      </div>

      {/* 2. Oval Table with Booth Seats & Characters */}
      <div className="relative flex items-center justify-center">
        {/* Left Character (Sora / UX Designer) */}
        <div className="absolute -left-7 top-4 z-20">
          <PixelCharacter
            role="ux_designer"
            name="Sora"
            status={agents.ux_designer.status}
            bubbleType="lightbulb"
            scale={0.9}
            onClick={onOpenRequirements}
          />
        </div>

        {/* Booth Surround & Oval Table */}
        <div className="w-[170px] h-[110px] bg-[#6d3e23] border-3 border-[#452412] rounded-[35px] shadow-2xl p-2 flex items-center justify-center relative">
          {/* Oval Table Surface */}
          <div className="w-[120px] h-[75px] rounded-[30px] bg-[#f8fafc] border-3 border-[#cbd5e1] shadow-inner flex flex-col items-center justify-center p-2">
            {/* Teapot & Cups on Table */}
            <div className="flex items-center gap-2">
              <div className="text-sm">🫖</div>
              <div className="w-2.5 h-2.5 bg-cyan-700 rounded-full border border-cyan-900" />
              <div className="w-2.5 h-2.5 bg-pink-700 rounded-full border border-pink-900" />
            </div>
          </div>
        </div>

        {/* Right Character (Elena / Product Strategy) */}
        <div className="absolute -right-7 top-4 z-20">
          <PixelCharacter
            role="product_manager"
            name="Elena"
            status={agents.product_manager.status}
            bubbleType="idea"
            scale={0.9}
            onClick={onOpenRequirements}
          />
        </div>
      </div>
    </div>
  );
};
