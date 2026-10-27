import React from 'react';

interface Footprint {
  x: number;
  y: number;
  rotation: number;
  side: 'left' | 'right';
  opacity?: number;
}

export const PixelFootprints: React.FC = () => {
  // Coordinated footprints matching the reference image
  const footprints: Footprint[] = [
    // Top doorway coming in
    { x: 740, y: 125, rotation: 80, side: 'left', opacity: 0.6 },
    { x: 755, y: 132, rotation: 85, side: 'right', opacity: 0.65 },
    { x: 745, y: 148, rotation: 90, side: 'left', opacity: 0.7 },
    { x: 760, y: 156, rotation: 85, side: 'right', opacity: 0.7 },

    // Path leading from reception towards top-right conference table
    { x: 970, y: 220, rotation: 30, side: 'left', opacity: 0.5 },
    { x: 990, y: 228, rotation: 25, side: 'right', opacity: 0.55 },
    { x: 1010, y: 240, rotation: 35, side: 'left', opacity: 0.5 },
    { x: 1030, y: 250, rotation: 30, side: 'right', opacity: 0.45 },

    // Trail near Designing booth
    { x: 260, y: 440, rotation: 120, side: 'left', opacity: 0.45 },
    { x: 275, y: 450, rotation: 125, side: 'right', opacity: 0.5 },
    { x: 290, y: 465, rotation: 110, side: 'left', opacity: 0.55 },

    // Footprints in center hallway leading towards Coding
    { x: 710, y: 360, rotation: 100, side: 'left', opacity: 0.5 },
    { x: 725, y: 375, rotation: 95, side: 'right', opacity: 0.55 },
    { x: 715, y: 395, rotation: 100, side: 'left', opacity: 0.6 },
    { x: 730, y: 410, rotation: 95, side: 'right', opacity: 0.55 },

    // Footprints moving toward Testing table
    { x: 880, y: 380, rotation: 45, side: 'left', opacity: 0.5 },
    { x: 900, y: 395, rotation: 50, side: 'right', opacity: 0.55 },
    { x: 920, y: 410, rotation: 40, side: 'left', opacity: 0.5 },
    { x: 940, y: 430, rotation: 45, side: 'right', opacity: 0.55 },
  ];

  return (
    <div className="absolute inset-0 pointer-events-none z-12">
      {footprints.map((fp, i) => (
        <div
          key={i}
          className="absolute"
          style={{
            left: `${fp.x}px`,
            top: `${fp.y}px`,
            transform: `rotate(${fp.rotation}deg)`,
            opacity: fp.opacity || 0.5,
          }}
        >
          {/* Pixel Shoe Footprint */}
          <div className="flex flex-col items-center gap-[1px]">
            {/* Front sole */}
            <div className="w-2.5 h-3 bg-[#4a2e1b] rounded-t-sm shadow-[0.5px_0.5px_0_rgba(255,255,255,0.2)]" />
            {/* Heel gap */}
            <div className="w-1.5 h-1.5 bg-[#4a2e1b] rounded-b-sm" />
          </div>
        </div>
      ))}
    </div>
  );
};
