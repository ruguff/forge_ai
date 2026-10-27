import React from 'react';
import { PixelCharacter } from './PixelCharacter';
import { useOffice } from '../../context/OfficeContext';

export const PixelLoungeArea: React.FC = () => {
  const { agents } = useOffice();

  return (
    <div className="absolute left-[50px] top-[180px] flex items-center gap-3 select-none z-15">
      {/* Left Booth Cushion & Character */}
      <div className="flex flex-col items-center">
        {/* Character Facing Right */}
        <div className="relative -bottom-2 z-20">
          <PixelCharacter
            role="security_auditor"
            name="Kaelen"
            status={agents.security_auditor.status}
            bubbleType="warning"
            isSeated
            scale={0.9}
          />
        </div>
        {/* Leather Booth Backrest */}
        <div className="w-12 h-14 bg-[#6d3e23] border-3 border-[#452412] rounded-l-xl shadow-md flex items-center justify-center">
          <div className="w-8 h-10 bg-[#542d17] rounded-l-md" />
        </div>
      </div>

      {/* Center Small Coffee Table with Plant */}
      <div className="flex flex-col items-center">
        {/* Round Wooden / Glass Table Surface */}
        <div className="w-12 h-12 rounded-full bg-[#f1c40f]/40 border-3 border-[#8e44ad]/80 shadow-md flex flex-col items-center justify-center relative">
          <div className="w-8 h-8 rounded-full bg-white/70 border border-slate-300 flex items-center justify-center">
            <span className="text-xs">🌱</span>
          </div>
        </div>
        {/* Table Leg & Base */}
        <div className="w-3 h-4 bg-[#7f8c8d]" />
        <div className="w-8 h-2 bg-[#34495e] rounded-full" />
      </div>

      {/* Right Booth Cushion & Character */}
      <div className="flex flex-col items-center">
        {/* Character Facing Left */}
        <div className="relative -bottom-2 z-20">
          <PixelCharacter
            role="conflict_resolver"
            name="Lex"
            status={agents.conflict_resolver.status}
            bubbleType="scale"
            isSeated
            scale={0.9}
          />
        </div>
        {/* Leather Booth Backrest */}
        <div className="w-12 h-14 bg-[#6d3e23] border-3 border-[#452412] rounded-r-xl shadow-md flex items-center justify-center">
          <div className="w-8 h-10 bg-[#542d17] rounded-r-md" />
        </div>
      </div>
    </div>
  );
};
