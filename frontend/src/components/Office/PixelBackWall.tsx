import React, { useEffect, useState } from 'react';

export const PixelBackWall: React.FC = () => {
  const [timeStr, setTimeStr] = useState('12:00');

  useEffect(() => {
    const update = () => {
      const d = new Date();
      setTimeStr(
        `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
      );
    };
    update();
    const interval = setInterval(update, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="absolute top-0 inset-x-0 h-[140px] select-none pointer-events-none z-10 flex">
      {/* 1. Left Brick / Wood Side Trim */}
      <div className="w-[180px] h-full bg-[#4a2e1b] border-r-4 border-[#2b180d] p-3 flex flex-col justify-between">
        {/* Horizontal Wooden Shutter Slats */}
        <div className="space-y-2 opacity-70">
          <div className="h-2 bg-[#6b4428] rounded-sm" />
          <div className="h-2 bg-[#6b4428] rounded-sm" />
          <div className="h-2 bg-[#6b4428] rounded-sm" />
          <div className="h-2 bg-[#6b4428] rounded-sm" />
          <div className="h-2 bg-[#6b4428] rounded-sm" />
        </div>

        {/* Chalkboard Easel */}
        <div className="bg-[#1f2937] border-4 border-[#8b5a35] p-2 rounded shadow-md text-center">
          <div className="text-[7px] font-pixel text-yellow-300 font-bold">PROJECTFORGE</div>
          <div className="text-[6px] font-pixel text-slate-300 mt-1">AI SPRINT #1</div>
        </div>
      </div>

      {/* 2. Main Wainscoted Blue Wall */}
      <div className="flex-1 h-full bg-[#82a7c9] border-b-8 border-[#54351d] relative flex items-center justify-between px-10 shadow-inner">
        {/* Wainscot Horizontal & Vertical Moldings */}
        <div className="absolute inset-0 pointer-events-none">
          {/* Top Wooden Crown Molding */}
          <div className="h-3 bg-[#4a2e1b] border-b border-[#2b180d]" />
          {/* Middle Wall Rail */}
          <div className="absolute top-[80px] inset-x-0 h-2 bg-[#5d3b23] border-t border-[#3e2413]" />
          {/* Vertical Panel Dividers */}
          <div className="absolute top-3 bottom-0 inset-x-0 flex justify-around opacity-30">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="w-[2px] h-full bg-[#2c4c69]" />
            ))}
          </div>
        </div>

        {/* Water Cooler Dispenser (Left Side of Wall) */}
        <div className="relative z-10 flex items-end gap-3">
          {/* Water Cooler */}
          <div className="w-10 h-24 bg-slate-200 border-2 border-slate-400 rounded-t shadow-lg flex flex-col items-center justify-between p-1">
            {/* Blue 5-Gallon Inverted Water Bottle */}
            <div className="w-8 h-10 bg-cyan-400/80 border-2 border-cyan-600 rounded-t-lg relative overflow-hidden shadow-inner">
              <div className="absolute inset-x-0 top-2 h-4 bg-cyan-200/50 rounded-full" />
              <div className="absolute bottom-1 right-1 w-1.5 h-1.5 bg-white/70 rounded-full animate-ping" />
            </div>
            {/* Dispenser Spouts */}
            <div className="w-full flex justify-around my-1">
              <div className="w-2 h-2 bg-blue-500 rounded-sm" />
              <div className="w-2 h-2 bg-red-500 rounded-sm" />
            </div>
            {/* Cup Stand */}
            <div className="w-6 h-3 bg-slate-400 rounded-sm" />
          </div>

          {/* Potted Plant */}
          <div className="flex flex-col items-center">
            {/* Green Leaf Foliage */}
            <div className="w-12 h-16 relative">
              <div className="absolute bottom-2 left-1 w-6 h-10 bg-[#16a34a] border-2 border-[#14532d] rounded-full transform -rotate-12" />
              <div className="absolute bottom-3 right-1 w-6 h-12 bg-[#22c55e] border-2 border-[#14532d] rounded-full transform rotate-12" />
              <div className="absolute bottom-6 left-3 w-7 h-10 bg-[#4ade80] border-2 border-[#14532d] rounded-full" />
            </div>
            {/* Clay Terra-cotta Pot */}
            <div className="w-9 h-7 bg-[#c2410c] border-2 border-[#7c2d12] rounded-b-md shadow-md" />
          </div>
        </div>

        {/* Center: Office Window with Curtains */}
        <div className="relative z-10 flex items-center gap-6">
          {/* Retro Wall Clock */}
          <div className="w-12 h-12 rounded-full bg-white border-4 border-[#54351d] shadow-lg flex items-center justify-center relative">
            <div className="w-1.5 h-1.5 rounded-full bg-slate-900 z-10" />
            <div className="absolute top-2 w-[2px] h-3.5 bg-slate-900 rounded origin-bottom transform rotate-45" />
            <div className="absolute top-2 w-[1.5px] h-4.5 bg-red-600 rounded origin-bottom transform rotate-180" />
            <div className="absolute bottom-1 text-[6px] font-pixel text-slate-700 font-bold">{timeStr}</div>
          </div>

          {/* Window with Tied-Back Curtains */}
          <div className="w-28 h-24 bg-cyan-100 border-4 border-[#54351d] rounded shadow-inner relative overflow-hidden flex justify-between">
            {/* Left Blue Curtain */}
            <div className="w-6 h-full bg-[#2563eb] border-r-2 border-[#1e40af] flex flex-col justify-between p-1 z-10">
              <div className="w-full h-4 bg-[#1d4ed8] rounded-sm" />
              <div className="w-4 h-2 bg-yellow-400 rounded-full" />
            </div>

            {/* Window Glass Pane with Sky & Cloud */}
            <div className="flex-1 bg-gradient-to-b from-sky-300 to-sky-100 relative flex items-center justify-center">
              <div className="w-8 h-3 bg-white/90 rounded-full shadow-sm" />
              {/* Window Frame Crossbars */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-full h-[2px] bg-[#54351d]" />
                <div className="absolute h-full w-[2px] bg-[#54351d]" />
              </div>
            </div>

            {/* Right Blue Curtain */}
            <div className="w-6 h-full bg-[#2563eb] border-l-2 border-[#1e40af] flex flex-col justify-between p-1 z-10">
              <div className="w-full h-4 bg-[#1d4ed8] rounded-sm" />
              <div className="w-4 h-2 bg-yellow-400 rounded-full ml-auto" />
            </div>
          </div>
        </div>

        {/* Right Wall Decor: Framed Pictures & Rocket Poster */}
        <div className="relative z-10 flex items-center gap-4">
          {/* Framed Rocket Poster (like in reference image!) */}
          <div className="w-14 h-20 bg-[#0f172a] border-4 border-[#854d0e] rounded shadow-md p-1 flex flex-col items-center justify-between">
            <div className="text-[6px] font-pixel text-cyan-300 font-bold text-center">LAUNCH</div>
            {/* Rocket Icon */}
            <div className="text-xl">🚀</div>
            <div className="text-[5px] font-pixel text-yellow-400 font-bold">SHIP</div>
          </div>

          {/* Small Framed Portrait Pictures */}
          <div className="flex flex-col gap-2">
            <div className="w-9 h-9 bg-[#fef3c7] border-2 border-[#854d0e] rounded shadow flex items-center justify-center text-xs">
              🤖
            </div>
            <div className="w-9 h-9 bg-[#fef3c7] border-2 border-[#854d0e] rounded shadow flex items-center justify-center text-xs">
              ⚡
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
