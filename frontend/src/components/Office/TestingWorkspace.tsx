import React from 'react';
import { motion } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import { WORKSPACE_COORDINATES } from '../../services/initialData';
import { CheckCircle2, XCircle, Wrench, PlayCircle, ShieldCheck } from 'lucide-react';

export const TestingWorkspace: React.FC = () => {
  const { pipelineStage, buildTestState } = useOffice();
  const coord = WORKSPACE_COORDINATES.testing_workspace;

  const isTesting = pipelineStage === 'TEST' || buildTestState.status === 'TESTING';
  const isFailed = buildTestState.status === 'FAILED';
  const isFixing = buildTestState.status === 'FIXING';
  const isPassed = pipelineStage === 'SHIP' || pipelineStage === 'COMPLETED' || buildTestState.status === 'PASSED';

  return (
    <div
      className={`absolute bg-slate-900/95 border rounded-3xl p-4 shadow-2xl backdrop-blur-xl transition-all flex flex-col justify-between select-none ${
        isFailed
          ? 'border-red-500/80 shadow-[0_0_25px_rgba(239,68,68,0.3)]'
          : isFixing
          ? 'border-amber-500/80 shadow-[0_0_25px_rgba(245,158,11,0.3)]'
          : isPassed
          ? 'border-emerald-500/80 shadow-[0_0_25px_rgba(16,185,129,0.3)]'
          : 'border-slate-800/80 shadow-lg opacity-85'
      }`}
      style={{
        left: coord.x,
        top: coord.y,
        width: coord.width,
        height: coord.height,
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              isPassed
                ? 'bg-emerald-400 shadow-[0_0_10px_#10b981]'
                : isFailed
                ? 'bg-red-400 shadow-[0_0_10px_#ef4444]'
                : isFixing
                ? 'bg-amber-400 shadow-[0_0_10px_#f59e0b]'
                : 'bg-slate-600'
            }`}
          />
          <span className="text-xs font-extrabold tracking-wider uppercase text-slate-100 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-amber-400" />
            Verification Arena
          </span>
        </div>
        <span
          className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
            isPassed
              ? 'bg-emerald-950/80 text-emerald-300 border-emerald-700/60 font-bold'
              : isFailed
              ? 'bg-red-950/80 text-red-300 border-red-700/60 font-bold'
              : isFixing
              ? 'bg-amber-950/80 text-amber-300 border-amber-700/60 font-bold'
              : 'bg-slate-950 text-slate-500 border-slate-800'
          }`}
        >
          {isPassed ? 'PASSED' : isFailed ? 'FAILED' : isFixing ? 'FIXING' : isTesting ? 'TESTING' : 'IDLE'}
        </span>
      </div>

      {/* Test Execution Telemetry Display */}
      <div className="bg-slate-950 border border-slate-800 rounded-2xl p-2.5 my-2 flex-1 flex flex-col justify-between min-h-0 font-mono text-[10px]">
        <div className="flex items-center justify-between text-slate-400 border-b border-slate-800/80 pb-1 mb-1">
          <span className="flex items-center gap-1 text-amber-400">
            <ShieldCheck className="w-3 h-3" /> PyTest Suite & SLA Runner
          </span>
          <span className="text-slate-500 text-[9px]">70/20/10 Pyramid</span>
        </div>

        {/* Dynamic Test Loop Status */}
        <div className="flex-1 flex flex-col justify-center space-y-1.5 py-1">
          {isFailed ? (
            <motion.div
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              className="bg-red-950/50 border border-red-800/80 p-2 rounded-xl text-red-200"
            >
              <div className="flex items-center gap-1 text-red-400 font-bold">
                <XCircle className="w-3 h-3 shrink-0" />
                <span>Test Failure Detected</span>
              </div>
              <p className="text-[9px] text-red-300 mt-0.5 truncate">
                {buildTestState.testOutput || 'Assertion failed: P95 latency > 100ms on simulated peak concurrency.'}
              </p>
            </motion.div>
          ) : isFixing ? (
            <motion.div
              animate={{ opacity: [0.7, 1, 0.7] }}
              transition={{ repeat: Infinity, duration: 1.5 }}
              className="bg-amber-950/50 border border-amber-800/80 p-2 rounded-xl text-amber-200"
            >
              <div className="flex items-center gap-1 text-amber-400 font-bold">
                <Wrench className="w-3 h-3 shrink-0" />
                <span>Coding Agent Debug Loop</span>
              </div>
              <p className="text-[9px] text-amber-300 mt-0.5 truncate">
                Refactoring connection pool to satisfy SLA threshold...
              </p>
            </motion.div>
          ) : isPassed ? (
            <div className="bg-emerald-950/50 border border-emerald-800/80 p-2 rounded-xl text-emerald-200">
              <div className="flex items-center gap-1 text-emerald-400 font-bold">
                <CheckCircle2 className="w-3 h-3 shrink-0" />
                <span>All Tests Passed</span>
              </div>
              <p className="text-[9px] text-emerald-300 mt-0.5">
                100% assertions verified. Zero regressions.
              </p>
            </div>
          ) : isTesting ? (
            <div className="flex items-center gap-2 text-slate-200 py-2">
              <PlayCircle className="w-4 h-4 text-amber-400 animate-spin" />
              <span>Executing test suite against containerized app...</span>
            </div>
          ) : (
            <div className="text-slate-500 italic text-center py-2">
              Ready to execute automated test pyramid upon build completion.
            </div>
          )}
        </div>

        {/* Test Counts Bar */}
        <div className="pt-1 border-t border-slate-800/80 grid grid-cols-3 gap-1 text-[9px] text-center">
          <div className="bg-slate-900 px-1 py-0.5 rounded border border-slate-800">
            <span className="text-slate-500">Total: </span>
            <span className="font-bold text-slate-200">{buildTestState.totalTests || 28}</span>
          </div>
          <div className="bg-slate-900 px-1 py-0.5 rounded border border-slate-800">
            <span className="text-slate-500">Passed: </span>
            <span className="font-bold text-emerald-400">
              {buildTestState.passedTests || (isPassed ? 28 : 0)}
            </span>
          </div>
          <div className="bg-slate-900 px-1 py-0.5 rounded border border-slate-800">
            <span className="text-slate-500">Failed: </span>
            <span className={`font-bold ${buildTestState.failedTests > 0 ? 'text-red-400' : 'text-slate-500'}`}>
              {buildTestState.failedTests || 0}
            </span>
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
        <span>Devon Reed (QA)</span>
        <span className="text-slate-500 text-[9px]">Automated Regression Gate</span>
      </div>
    </div>
  );
};
