import React from 'react';
import { motion } from 'framer-motion';
import { PixelCharacter } from './PixelCharacter';
import { useOffice } from '../../context/OfficeContext';
import { Users, MessageSquare, Sparkles } from 'lucide-react';

interface PixelConferenceTableProps {
  onOpenDiscussion: () => void;
}

export const PixelConferenceTable: React.FC<PixelConferenceTableProps> = ({ onOpenDiscussion }) => {
  const { agents, activeDiscussion, pipelineStage } = useOffice();

  const isDiscussing = pipelineStage === 'DISCUSSION' || Boolean(activeDiscussion);

  const topicText =
    activeDiscussion?.topic ||
    (isDiscussing
      ? 'API scope and deployment architecture'
      : 'Cross-agent alignment & review');

  const decisionsCount = activeDiscussion?.messages?.length || 3;
  const participantsCount = activeDiscussion?.participants?.length || 2;

  return (
    <div className="flex flex-col items-center select-none z-15 w-[380px]">
      {/* 1. Collaboration Table Sign & Live Discussion Status */}
      <div
        className="pixel-signpost px-3 py-1 rounded shadow flex items-center gap-1.5 -mb-2 z-25 cursor-pointer"
        onClick={onOpenDiscussion}
      >
        <Users className="w-3 h-3 text-cyan-400" />
        <span className="text-[8px] font-pixel text-yellow-100 font-bold uppercase tracking-wider">
          COLLABORATION TABLE
        </span>
        {isDiscussing && (
          <span className="text-[7px] font-pixel text-emerald-400 bg-emerald-950 px-1.5 py-0.2 rounded border border-emerald-600 animate-pulse">
            LIVE
          </span>
        )}
      </div>

      {/* Top Seated Character (Marcus / Systems Lead) */}
      <div className="relative -bottom-3 z-20">
        <PixelCharacter
          role="engineering_lead"
          name="Marcus"
          status={isDiscussing ? 'DISCUSSING' : agents.engineering_lead.status}
          bubbleType={isDiscussing ? 'document' : undefined}
          isSeated
          scale={0.95}
          onClick={onOpenDiscussion}
        />
      </div>

      {/* Middle Row: Left Chair, Conference Table, Right Chair */}
      <div className="flex items-center gap-1.5 w-full justify-center">
        {/* Left Seated Character (Dr. Aris Thorne / AI Architect) */}
        <div className="relative -right-2 z-20">
          <PixelCharacter
            role="aiml_architect"
            name="Dr. Thorne"
            status={isDiscussing ? 'DISCUSSING' : agents.aiml_architect.status}
            bubbleType={isDiscussing ? 'idea' : undefined}
            isSeated
            scale={0.95}
            onClick={onOpenDiscussion}
          />
        </div>

        {/* Large Rectangular Wooden Conference Table */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          onClick={onOpenDiscussion}
          animate={isDiscussing ? { boxShadow: ['0 0 15px rgba(56,189,248,0.3)', '0 0 25px rgba(56,189,248,0.5)', '0 0 15px rgba(56,189,248,0.3)'] } : {}}
          transition={{ repeat: Infinity, duration: 2 }}
          className="w-[260px] h-[115px] bg-[#d9975b] border-4 border-[#7c4822] rounded-2xl shadow-2xl relative p-2 flex flex-col justify-between cursor-pointer group"
        >
          {/* Subtle Woodgrain Top Strip */}
          <div className="absolute inset-x-4 top-1.5 h-[2px] bg-[#9a5b28]/40" />

          {/* Top Papers / Blueprints Scattered on Table */}
          <div className="flex justify-between items-start">
            <div className="w-7 h-9 bg-white border border-slate-400 rounded-sm shadow p-0.5 transform -rotate-6">
              <div className="w-full h-1 bg-blue-500 rounded-sm mb-0.5" />
              <div className="w-3 h-0.5 bg-slate-400 mb-0.5" />
              <div className="w-4 h-0.5 bg-slate-400" />
            </div>

            {/* Coffee Mug */}
            <div className="w-4 h-4 bg-[#be185d] border border-[#831843] rounded-full shadow flex items-center justify-center">
              <div className="w-2.5 h-2.5 bg-[#451a03] rounded-full" />
            </div>

            <div className="w-7 h-9 bg-white border border-slate-400 rounded-sm shadow p-0.5 transform rotate-12">
              <div className="w-full h-1 bg-purple-500 rounded-sm mb-0.5" />
              <div className="w-4 h-0.5 bg-slate-400 mb-0.5" />
              <div className="w-3 h-0.5 bg-slate-400" />
            </div>
          </div>

          {/* Center Table Discussion Topic Banner */}
          <div className="w-full bg-[#3e2413]/90 border border-[#7c4822] rounded px-1.5 py-0.5 text-center shadow-inner">
            <div className="text-[6.5px] font-pixel text-yellow-300 font-bold uppercase truncate">
              {isDiscussing ? 'Product ↔ Engineering' : 'Cross-Agent Meeting'}
            </div>
            <div className="text-[6px] font-mono text-cyan-200 truncate mt-0.5">
              "{topicText}"
            </div>
            <div className="text-[5.5px] font-mono text-slate-300 mt-0.5 flex items-center justify-center gap-2">
              <span>{participantsCount} agents</span>
              <span>•</span>
              <span className="text-emerald-300">{decisionsCount} decisions</span>
            </div>
          </div>

          {/* Bottom Table Rail */}
          <div className="flex justify-between items-end">
            <div className="w-6 h-7 bg-white border border-slate-400 rounded-sm shadow p-0.5 transform rotate-3">
              <div className="w-full h-1 bg-emerald-500 rounded-sm mb-0.5" />
              <div className="w-3 h-0.5 bg-slate-400" />
            </div>

            {/* Succulent Plant */}
            <div className="w-5 h-4 bg-[#15803d] border border-[#14532d] rounded-full shadow flex items-center justify-center text-[8px]">
              🪴
            </div>

            <div className="w-6 h-7 bg-white border border-slate-400 rounded-sm shadow p-0.5 transform -rotate-12">
              <div className="w-full h-1 bg-cyan-500 rounded-sm mb-0.5" />
              <div className="w-3 h-0.5 bg-slate-400" />
            </div>
          </div>
        </motion.div>

        {/* Right Seated Character (Elena Rostova / Product Lead) */}
        <div className="relative -left-2 z-20">
          <PixelCharacter
            role="product_manager"
            name="Elena"
            status={isDiscussing ? 'DISCUSSING' : agents.product_manager.status}
            bubbleType={isDiscussing ? 'document' : undefined}
            isSeated
            scale={0.95}
            onClick={onOpenDiscussion}
          />
        </div>
      </div>
    </div>
  );
};
