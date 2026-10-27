import React from 'react';
import { motion } from 'framer-motion';
import { PixelCharacter } from './PixelCharacter';
import { useOffice } from '../../context/OfficeContext';
import { ShieldCheck, Bug, CheckCircle2, XCircle, ArrowRight } from 'lucide-react';

interface PixelTestingAreaProps {
  onOpenTestInspector: () => void;
}

export const PixelTestingArea: React.FC<PixelTestingAreaProps> = ({ onOpenTestInspector }) => {
  const { pipelineStage, buildTestState, agents } = useOffice();

  const isTesting = pipelineStage === 'TEST' || buildTestState.status === 'TESTING';
  const isFailed = buildTestState.status === 'FAILED';
  const isFixing = buildTestState.status === 'FIXING';
  const isPassed =
    pipelineStage === 'SHIP' ||
    pipelineStage === 'COMPLETED' ||
    buildTestState.status === 'PASSED';

  const passedTests = buildTestState.passedTests || (isPassed ? 28 : isFailed ? 27 : 14);
  const totalTests = buildTestState.totalTests || 28;
  const failedTests = isFailed ? 1 : 0;

  return (
    <div className="flex flex-col items-center select-none z-15 w-[380px]">
      {/* 1. Testing Station Signpost */}
      <div
        className="pixel-signpost px-3 py-0.5 rounded shadow flex items-center gap-1.5 -mb-2 z-25 cursor-pointer"
        onClick={onOpenTestInspector}
        style={{ borderTopColor: '#F59E0B' }}
      >
        <ShieldCheck className="w-3 h-3 text-amber-400" />
        <span className="text-[8px] font-pixel text-yellow-100 font-bold uppercase tracking-wider">
          QA TESTING ARENA
        </span>
        {isFailed ? (
          <span className="text-[6px] font-pixel text-red-400 bg-red-950 px-1 py-0.2 rounded border border-red-600 animate-pulse">
            FAIL DETECTED
          </span>
        ) : isPassed ? (
          <span className="text-[6px] font-pixel text-emerald-400 bg-emerald-950 px-1 py-0.2 rounded border border-emerald-600">
            ALL PASS
          </span>
        ) : null}
      </div>

      {/* 2. Round Testing Station Container */}
      <div
        onClick={onOpenTestInspector}
        className="w-full bg-[#1e293b]/90 border-2 border-[#334155] rounded-xl shadow-2xl p-2.5 flex items-center justify-between cursor-pointer group backdrop-blur-md"
      >
        {/* Left: Devon Reed QA Strategist Character */}
        <div className="flex flex-col items-center">
          <PixelCharacter
            role="qa_strategist"
            name="Devon"
            status={isTesting || isFailed ? 'WORKING' : agents.qa_strategist.status}
            bubbleType={isFailed ? 'warning' : isPassed || isTesting ? 'bug' : undefined}
            currentTask={
              isFailed
                ? 'Regression triage & patch verification'
                : isPassed
                ? 'All 28 tests passing (SLA 48ms)'
                : 'Pytest suite & API contract tests'
            }
            scale={0.95}
          />
        </div>

        {/* Center: Dual Curved Monitors & Test Status */}
        <div className="flex flex-col items-center gap-1">
          {/* Dual Monitors */}
          <div className="flex items-center gap-1">
            <div className="w-16 h-11 bg-slate-950 border-2 border-slate-700 rounded p-1 flex flex-col justify-between shadow">
              <span className="text-[5.5px] font-mono text-slate-400">TEST MATRIX</span>
              <div
                className={`text-[7px] font-pixel font-bold text-center py-0.5 rounded ${
                  isFailed
                    ? 'bg-red-950/80 text-red-400'
                    : isPassed
                    ? 'bg-emerald-950/80 text-emerald-400'
                    : 'bg-cyan-950/80 text-cyan-300'
                }`}
              >
                {isFailed ? 'FAIL 1' : isPassed ? 'PASS 28' : 'TESTING'}
              </div>
            </div>

            <div className="w-16 h-11 bg-slate-950 border-2 border-slate-700 rounded p-1 flex flex-col justify-between shadow">
              <span className="text-[5.5px] font-mono text-slate-400">SLA LATENCY</span>
              <div className="text-[7px] font-pixel font-bold text-center py-0.5 rounded bg-slate-900 text-amber-400">
                48ms
              </div>
            </div>
          </div>

          {/* Test Metrics Pill */}
          <div className="text-[6.5px] font-mono text-slate-300 flex items-center gap-2 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
            <span className="text-emerald-400 font-bold">{passedTests} passed</span>
            <span>•</span>
            <span className={failedTests > 0 ? 'text-red-400 font-bold' : 'text-slate-400'}>
              {failedTests} failed
            </span>
          </div>
        </div>

        {/* Right: QA Lifecycle Tracker */}
        <div className="flex flex-col gap-1 text-[5.5px] font-pixel bg-slate-950/80 p-1.5 rounded border border-slate-800/80 min-w-[90px]">
          <span className="text-[6px] font-mono text-slate-400 border-b border-slate-800 pb-0.5 mb-0.5">
            QA LIFECYCLE
          </span>
          <div className="flex items-center gap-1 text-slate-400">
            <span className={pipelineStage === 'BUILD' ? 'text-emerald-400 font-bold' : ''}>BUILD</span>
            <ArrowRight className="w-2 h-2 text-slate-600" />
            <span className={isTesting ? 'text-cyan-400 font-bold' : ''}>TEST</span>
          </div>
          <div className="flex items-center gap-1 text-slate-400">
            <span className={isFailed ? 'text-red-400 font-bold' : ''}>FAIL</span>
            <ArrowRight className="w-2 h-2 text-slate-600" />
            <span className={isFixing ? 'text-amber-400 font-bold' : ''}>FIX</span>
            <ArrowRight className="w-2 h-2 text-slate-600" />
            <span className={isPassed ? 'text-emerald-400 font-bold' : ''}>PASS</span>
          </div>
        </div>
      </div>
    </div>
  );
};
