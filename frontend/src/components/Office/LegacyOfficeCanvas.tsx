import React, { useRef, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import { AgentRole } from '../../types/office';
import { ZoomIn, ZoomOut, Maximize2, RotateCcw } from 'lucide-react';

// Specialized Physical Workspace Components
import { PixelBackWall } from './PixelBackWall';
import { PixelCommandCenter } from './PixelCommandCenter';
import { PixelWorkspaceDesk } from './PixelWorkspaceDesk';
import { PixelConferenceTable } from './PixelConferenceTable';
import { PixelConflictRoom } from './PixelConflictRoom';
import { PixelArchitectStudio } from './PixelArchitectStudio';
import { PixelCodingWorkshop } from './PixelCodingWorkshop';
import { PixelTestingArea } from './PixelTestingArea';
import { PixelFootprints } from './PixelFootprints';
import { PixelDataFlowBeams, DataBeam } from './PixelDataFlowBeams';
import { Minimap } from '../Navigation/Minimap';

interface OfficeCanvasProps {
  onOpenDiscussion: () => void;
  onOpenConflict: () => void;
  onOpenBlueprint: () => void;
  onOpenRequirements: () => void;
  onOpenClarification: () => void;
}

export const OfficeCanvas: React.FC<OfficeCanvasProps> = ({
  onOpenDiscussion,
  onOpenConflict,
  onOpenBlueprint,
  onOpenRequirements,
  onOpenClarification,
}) => {
  const {
    agents,
    pipelineStage,
    activeDiscussion,
    activeConflict,
    selectAgent,
  } = useOffice();

  const containerRef = useRef<HTMLDivElement>(null);
  const [viewportSize, setViewportSize] = useState({ width: 1366, height: 680 });
  const [userZoom, setUserZoom] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });

  // Calibrated World Bounds (1360px x 700px)
  const WORLD_WIDTH = 1360;
  const WORLD_HEIGHT = 700;

  // Responsive Camera Observer: measures viewport to guarantee the office dominates the screen
  useEffect(() => {
    if (!containerRef.current) return;
    const updateSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          setViewportSize({ width: rect.width, height: rect.height });
        }
      }
    };
    updateSize();
    const ro = new ResizeObserver(updateSize);
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // Compute scale required to fill 88-94% of the viewport on any resolution (1280x720, 1366x768, 1920x1080)
  const marginX = 20;
  const marginY = 16;
  const scaleX = (viewportSize.width - marginX * 2) / WORLD_WIDTH;
  const scaleY = (viewportSize.height - marginY * 2) / WORLD_HEIGHT;
  const baseFitScale = Math.min(scaleX, scaleY);
  const effectiveScale = Math.max(0.4, baseFitScale * userZoom);

  const zoomIn = () => setUserZoom((z) => Math.min(2.0, z + 0.15));
  const zoomOut = () => setUserZoom((z) => Math.max(0.65, z - 0.15));
  const fitOffice = () => {
    setUserZoom(1);
    setPanOffset({ x: 0, y: 0 });
  };
  const resetCamera = () => {
    setUserZoom(1);
    setPanOffset({ x: 0, y: 0 });
  };

  const isDiscussing = pipelineStage === 'DISCUSSION' || Boolean(activeDiscussion);
  const isConflictActive = Boolean(activeConflict);

  // Active Information Data Flow Beams between physical labs
  const activeDataBeams: DataBeam[] = [];

  if (isDiscussing) {
    activeDataBeams.push({
      id: 'beam-disc-pm',
      from: { x: 125, y: 380 }, // Product Lab
      to: { x: 980, y: 220 }, // Collaboration Table
      color: '#10b981',
      label: 'PRD SCOPE',
    });
    activeDataBeams.push({
      id: 'beam-disc-ai',
      from: { x: 325, y: 380 }, // AI/ML Lab
      to: { x: 980, y: 220 }, // Collaboration Table
      color: '#a855f7',
      label: 'MODEL DECISION',
    });
  }

  if (isConflictActive) {
    activeDataBeams.push({
      id: 'beam-conf-1',
      from: { x: 325, y: 380 }, // AI/ML Lab
      to: { x: 670, y: 380 }, // Conflict Arbiter Lex
      color: '#ef4444',
      label: 'TRADE-OFF A',
    });
    activeDataBeams.push({
      id: 'beam-conf-2',
      from: { x: 1015, y: 380 }, // Engineering Lab
      to: { x: 670, y: 380 }, // Conflict Arbiter Lex
      color: '#f59e0b',
      label: 'TRADE-OFF B',
    });
  }

  if (pipelineStage === 'FINAL_SYNTHESIS' || pipelineStage === 'ARCHITECTURE') {
    activeDataBeams.push({
      id: 'beam-arch',
      from: { x: 1015, y: 380 }, // Engineering Lab
      to: { x: 1220, y: 380 }, // Final Architect Prime
      color: '#6366f1',
      label: 'SYSTEM BLUEPRINT',
    });
  }

  if (pipelineStage === 'BUILD') {
    activeDataBeams.push({
      id: 'beam-build',
      from: { x: 1220, y: 410 }, // Prime
      to: { x: 850, y: 570 }, // Coding Agent
      color: '#22c55e',
      label: 'CODE GENERATION',
    });
  }

  if (pipelineStage === 'TEST') {
    activeDataBeams.push({
      id: 'beam-test',
      from: { x: 550, y: 570 }, // Coding Workshop
      to: { x: 220, y: 570 }, // QA Testing Arena
      color: '#f59e0b',
      label: 'PYTEST VERIFY',
    });
  }

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full bg-[#090D16] overflow-hidden select-none flex items-center justify-center"
    >
      {/* 2D Responsive Camera Viewport */}
      <motion.div
        animate={{
          x: panOffset.x,
          y: panOffset.y,
          scale: effectiveScale,
        }}
        transition={{ type: 'spring', stiffness: 220, damping: 28 }}
        className="w-[1360px] h-[700px] shrink-0 relative"
      >
        {/* =========================================================================
           AUTHENTIC PIXEL ART ENGINEERING OFFICE WORLD
           ========================================================================= */}
        <div className="relative w-full h-full pixel-wood-floor rounded-2xl border-4 border-[#2b180d] shadow-[0_0_50px_rgba(0,0,0,0.85)] overflow-hidden">
          {/* Top Wainscoted Wall with Clock, Curtains, Posters, Plant & Water Cooler */}
          <PixelBackWall />

          {/* Footprint Trails on the Wooden Floorboards */}
          <PixelFootprints />

          {/* Dynamic SVG Data Flow Information Beams */}
          <PixelDataFlowBeams beams={activeDataBeams} />

          {/* =======================================================================
             ROW 1 (y: 135px to 310px):
             UX STUDIO | SECURITY LAB | COMMAND CENTER | COLLABORATION TABLE
             ======================================================================= */}
          {/* 1. UX Studio (Sora Takahashi) */}
          <div className="absolute left-[30px] top-[135px] z-15">
            <PixelWorkspaceDesk
              role="ux_designer"
              labName="UX STUDIO"
              status={agents.ux_designer.status}
              artifactName="ux_spec.md"
              artifactDocType="SPEC"
              onSelectAgent={() => selectAgent('ux_designer')}
              onOpenArtifact={onOpenRequirements}
            />
          </div>

          {/* 2. Security Lab (Kaelen Cross) */}
          <div className="absolute left-[230px] top-[135px] z-15">
            <PixelWorkspaceDesk
              role="security_auditor"
              labName="SECURITY LAB"
              status={agents.security_auditor.status}
              artifactName="threat_model.md"
              artifactDocType="AUDIT"
              onSelectAgent={() => selectAgent('security_auditor')}
              onOpenArtifact={onOpenRequirements}
            />
          </div>

          {/* 3. Central Mission Command Center (Elena Host & Project Status) */}
          <div className="absolute left-[450px] top-[130px] z-15">
            <PixelCommandCenter
              onOpenIntake={onOpenRequirements}
              onOpenRequirements={onOpenRequirements}
            />
          </div>

          {/* 4. Central Collaboration Table (Meeting Area) */}
          <div className="absolute left-[940px] top-[135px] z-15">
            <PixelConferenceTable onOpenDiscussion={onOpenDiscussion} />
          </div>

          {/* =======================================================================
             ROW 2 (y: 320px to 495px):
             PRODUCT LAB | AI/ML LAB | CONFLICT ARBITRATION | ENG LAB | FINAL ARCHITECT
             ======================================================================= */}
          {/* 5. Product Lab (Elena Rostova) */}
          <div className="absolute left-[30px] top-[320px] z-15">
            <PixelWorkspaceDesk
              role="product_manager"
              labName="PRODUCT LAB"
              status={agents.product_manager.status}
              artifactName="prd.md"
              artifactDocType="PRD"
              onSelectAgent={() => selectAgent('product_manager')}
              onOpenArtifact={onOpenRequirements}
              isAgentPresent={!isDiscussing}
            />
          </div>

          {/* 6. AI/ML Lab (Dr. Aris Thorne) */}
          <div className="absolute left-[230px] top-[320px] z-15">
            <PixelWorkspaceDesk
              role="aiml_architect"
              labName="AI/ML LAB"
              status={agents.aiml_architect.status}
              artifactName="model_decision.md"
              artifactDocType="DECISION"
              onSelectAgent={() => selectAgent('aiml_architect')}
              onOpenArtifact={onOpenRequirements}
              isAgentPresent={!isDiscussing && !isConflictActive}
            />
          </div>

          {/* 7. Dedicated Conflict Arbitration Room (Lex) */}
          <div className="absolute left-[450px] top-[320px] z-15">
            <PixelConflictRoom onOpenConflict={onOpenConflict} />
          </div>

          {/* 8. Engineering Lab (Marcus Vance) */}
          <div className="absolute left-[940px] top-[320px] z-15">
            <PixelWorkspaceDesk
              role="engineering_lead"
              labName="ENGINEERING LAB"
              status={agents.engineering_lead.status}
              artifactName="arch_diagram.md"
              artifactDocType="SCHEMA"
              onSelectAgent={() => selectAgent('engineering_lead')}
              onOpenArtifact={onOpenDiscussion}
              isAgentPresent={!isDiscussing && !isConflictActive}
            />
          </div>

          {/* 9. Final Architect Studio (Prime) */}
          <div className="absolute left-[1145px] top-[320px] z-15">
            <PixelArchitectStudio onOpenBlueprint={onOpenBlueprint} />
          </div>

          {/* =======================================================================
             ROW 3 (y: 505px to 685px):
             QA TESTING ARENA | CODING WORKSHOP
             ======================================================================= */}
          {/* 10. Dedicated QA Testing Arena (Devon Reed) */}
          <div className="absolute left-[30px] top-[505px] z-15">
            <PixelTestingArea onOpenTestInspector={onOpenBlueprint} />
          </div>

          {/* 11. Coding Workshop (Qwen3-Coder & Computer Desks) */}
          <div className="absolute left-[450px] top-[505px] z-15">
            <PixelCodingWorkshop onOpenCodeStream={onOpenBlueprint} />
          </div>

          {/* Subtle Ambient Wood Floorboard Vignette */}
          <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_60px_rgba(43,24,13,0.45)]" />
        </div>
      </motion.div>

      {/* Floating HUD Controls (Bottom Left: Zoom / Reset / Fit) */}
      <div className="absolute left-6 bottom-6 z-25 flex items-center gap-1.5 bg-slate-950/90 border border-slate-800/90 p-1.5 rounded-2xl shadow-2xl backdrop-blur-xl">
        <button
          onClick={zoomIn}
          title="Zoom In"
          className="p-2 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors cursor-pointer"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={zoomOut}
          title="Zoom Out"
          className="p-2 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors cursor-pointer"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <div className="h-4 w-[1px] bg-slate-800" />
        <button
          onClick={fitOffice}
          title="Fit Office to Screen"
          className="px-2.5 py-1.5 rounded-xl text-cyan-400 bg-cyan-950/40 border border-cyan-700/40 hover:bg-cyan-900/50 transition-colors cursor-pointer flex items-center gap-1.5 text-xs font-mono font-bold"
        >
          <Maximize2 className="w-3.5 h-3.5" />
          <span>FIT</span>
        </button>
        <button
          onClick={resetCamera}
          title="Reset View"
          className="p-2 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Radar Minimap Floating Overlay (Bottom Right) */}
      <div className="absolute right-6 bottom-6 z-25">
        <Minimap />
      </div>
    </div>
  );
};
