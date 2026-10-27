import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import {
  X,
  Scale,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sliders,
  ShieldCheck,
  Zap,
} from 'lucide-react';

interface ConflictRoomPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ConflictRoomPanel: React.FC<ConflictRoomPanelProps> = ({ isOpen, onClose }) => {
  const { activeConflict, resolveConflict, requestReanalysis, agents } = useOffice();
  const [showOverrideInput, setShowOverrideInput] = useState(false);
  const [overrideText, setOverrideText] = useState('');

  if (!isOpen || !activeConflict) return null;

  const criteriaList = [
    { key: 'maintainability', label: 'Maintainability', weight: 0.25 },
    { key: 'latency_performance', label: 'Latency / Performance', weight: 0.20 },
    { key: 'implementation_complexity', label: 'Implementation Complexity', weight: 0.20 },
    { key: 'infrastructure_cost', label: 'Infrastructure Cost', weight: 0.20 },
    { key: 'scalability', label: 'Scalability', weight: 0.15 },
  ];

  const optionKeys = Object.keys(activeConflict.criteriaScores);
  const optionA = optionKeys[0] || 'Option A';
  const optionB = optionKeys[1] || 'Option B';

  const scoresA = activeConflict.criteriaScores[optionA] || {};
  const scoresB = activeConflict.criteriaScores[optionB] || {};

  const computeTotal = (scores: Record<string, number>) => {
    return criteriaList.reduce((sum, c) => sum + c.weight * (scores[c.key] || 5.0), 0);
  };

  const totalA = computeTotal(scoresA);
  const totalB = computeTotal(scoresB);
  const winner = totalA >= totalB ? 'A' : 'B';

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          className="bg-slate-900 border border-amber-600/50 rounded-3xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]"
        >
          {/* Header */}
          <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-950/80 border border-amber-600/60 flex items-center justify-center text-amber-400">
                <Scale className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-amber-400 uppercase tracking-wide">
                    Conflict Arbitration Chamber
                  </span>
                  <span className="text-[10px] bg-amber-950 text-amber-300 border border-amber-700/50 px-2 py-0.5 rounded-full font-bold">
                    {activeConflict.id}
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-100 mt-0.5">{activeConflict.title}</h3>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="p-6 overflow-y-auto space-y-6 flex-1">
            {/* Issue summary */}
            <div className="bg-amber-950/20 border border-amber-600/30 p-4 rounded-2xl">
              <div className="text-xs font-bold text-amber-400 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4" /> Structural Contradiction Issue
              </div>
              <p className="text-xs text-slate-200 leading-relaxed">{activeConflict.issue}</p>
            </div>

            {/* Competing Recommendations */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-2xl">
                <div className="text-xs font-bold text-cyan-400 uppercase tracking-wider mb-1">
                  Option A ({optionA})
                </div>
                <p className="text-xs text-slate-300">{activeConflict.recommendations[activeConflict.participatingAgents[0]] || activeConflict.recommendations[optionA] || 'Option A stance'}</p>
              </div>

              <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-2xl">
                <div className="text-xs font-bold text-purple-400 uppercase tracking-wider mb-1">
                  Option B ({optionB})
                </div>
                <p className="text-xs text-slate-300">{activeConflict.recommendations[activeConflict.participatingAgents[1]] || activeConflict.recommendations[optionB] || 'Option B stance'}</p>
              </div>
            </div>

            {/* Weighted Decision Matrix Table */}
            <div>
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Sliders className="w-4 h-4 text-amber-400" /> Multi-Criteria Weighted Utility Matrix
              </h4>

              <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/90 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-4">Evaluation Criterion</th>
                      <th className="py-2.5 px-3">Weight</th>
                      <th className="py-2.5 px-3 text-cyan-400">{optionA} Score (1-10)</th>
                      <th className="py-2.5 px-3 text-purple-400">{optionB} Score (1-10)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {criteriaList.map((c) => (
                      <tr key={c.key} className="hover:bg-slate-900/50">
                        <td className="py-2 px-4 font-medium">{c.label}</td>
                        <td className="py-2 px-3 font-mono text-slate-400">{(c.weight * 100).toFixed(0)}%</td>
                        <td className="py-2 px-3 font-mono font-semibold text-cyan-300">
                          {scoresA[c.key] !== undefined ? scoresA[c.key].toFixed(1) : '5.0'}
                        </td>
                        <td className="py-2 px-3 font-mono font-semibold text-purple-300">
                          {scoresB[c.key] !== undefined ? scoresB[c.key].toFixed(1) : '5.0'}
                        </td>
                      </tr>
                    ))}
                    <tr className="bg-slate-900 font-bold border-t border-slate-700">
                      <td className="py-3 px-4 text-slate-100">Weighted Utility Total U = Σ(w × s)</td>
                      <td className="py-3 px-3 font-mono text-slate-400">100%</td>
                      <td className={`py-3 px-3 font-mono text-sm ${totalA >= totalB ? 'text-emerald-400' : 'text-cyan-400'}`}>
                        {totalA.toFixed(2)} {totalA >= totalB && '★ Winner'}
                      </td>
                      <td className={`py-3 px-3 font-mono text-sm ${totalB > totalA ? 'text-emerald-400' : 'text-purple-400'}`}>
                        {totalB.toFixed(2)} {totalB > totalA && '★ Winner'}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Manual Override Input */}
            {showOverrideInput && (
              <div className="bg-slate-950 border border-slate-800 p-4 rounded-2xl space-y-2">
                <div className="text-xs font-bold text-amber-400 uppercase tracking-wider">Project Owner Manual Override Rationale</div>
                <textarea
                  value={overrideText}
                  onChange={(e) => setOverrideText(e.target.value)}
                  placeholder="Specify custom arbitration directive and technical reason..."
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500 h-20"
                />
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="p-4 border-t border-slate-800 bg-slate-950 flex items-center justify-between gap-3">
            <button
              onClick={() => {
                requestReanalysis(activeConflict.participatingAgents[0]);
                onClose();
              }}
              className="flex items-center gap-1.5 text-xs text-amber-300 bg-amber-950/60 border border-amber-800/40 px-3.5 py-2 rounded-xl hover:bg-amber-900/60 transition-colors font-semibold"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Request Re-analysis
            </button>

            <div className="flex items-center gap-2">
              {!showOverrideInput ? (
                <button
                  onClick={() => setShowOverrideInput(true)}
                  className="text-xs text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 px-4 py-2 rounded-xl transition-colors font-semibold"
                >
                  Manual Override
                </button>
              ) : (
                <button
                  onClick={() => {
                    resolveConflict(activeConflict.id, 'OVERRIDE', overrideText);
                    onClose();
                  }}
                  className="text-xs text-slate-950 bg-amber-400 hover:bg-amber-300 font-bold px-4 py-2 rounded-xl transition-colors"
                >
                  Submit Override
                </button>
              )}

              <button
                onClick={() => {
                  resolveConflict(activeConflict.id, winner as 'A' | 'B');
                  onClose();
                }}
                className="flex items-center gap-1.5 text-xs text-slate-950 bg-emerald-400 hover:bg-emerald-300 font-bold px-5 py-2 rounded-xl transition-all shadow-md"
              >
                <CheckCircle2 className="w-4 h-4" /> Approve Arbitrated Resolution ({winner === 'A' ? optionA : optionB})
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
