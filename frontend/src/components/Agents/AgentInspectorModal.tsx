import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import { AgentRole } from '../../types/office';
import {
  X,
  ShieldCheck,
  FileCode,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Quote,
} from 'lucide-react';

interface AgentInspectorModalProps {
  agentRole: AgentRole | null;
  onClose: () => void;
}

export const AgentInspectorModal: React.FC<AgentInspectorModalProps> = ({
  agentRole,
  onClose,
}) => {
  const { agents, artifacts, requestReanalysis, selectArtifact } = useOffice();

  if (!agentRole) return null;
  const agent = agents[agentRole];
  if (!agent) return null;

  const agentArtifacts = artifacts.filter((a) => a.producedBy === agentRole);

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          className="bg-slate-900 border border-slate-700 rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]"
        >
          {/* Modal Header */}
          <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
            <div className="flex items-center gap-4">
              <div
                className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${agent.avatarColor} p-0.5 flex items-center justify-center`}
              >
                <div className="w-full h-full bg-slate-950/80 rounded-[14px] flex items-center justify-center text-white font-bold text-lg">
                  {agent.name[0]}
                </div>
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                  <span>{agent.name}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-cyan-950 text-cyan-400 border border-cyan-800/40">
                    {agent.status}
                  </span>
                </h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">{agent.roleTitle}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Modal Body */}
          <div className="p-6 overflow-y-auto space-y-6 flex-1">
            {/* Personality & Focus Quote */}
            <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-2xl">
              <div className="flex items-center gap-2 text-xs font-bold text-cyan-400 uppercase tracking-wider mb-1">
                <Quote className="w-4 h-4" /> Agent Persona & Philosophy
              </div>
              <p className="text-xs italic text-slate-300">"{agent.personality.quote}"</p>
              <div className="mt-2 text-[11px] text-slate-400">
                <span className="font-semibold text-slate-300">Domain Focus:</span> {agent.personality.focus}
              </div>
            </div>

            {/* Current Work & Reasoning */}
            <div>
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-cyan-400" /> Current Work & Activity
              </h4>
              <div className="bg-slate-950/40 border border-slate-800 p-4 rounded-2xl space-y-2">
                <div className="text-xs text-slate-200 font-medium">
                  <span className="text-slate-400">Active Task:</span> {agent.currentTask}
                </div>
                <div className="text-xs text-slate-300 bg-slate-900/90 p-2.5 rounded-xl border border-slate-800/80">
                  <span className="text-cyan-400 font-semibold">Activity Line:</span> {agent.activityMessage}
                </div>
              </div>
            </div>

            {/* Calibrated Confidence Breakdown */}
            <div>
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-cyan-400" /> Empirical Confidence Calibration
              </h4>
              <div className="bg-slate-950/40 border border-slate-800 p-4 rounded-2xl">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-slate-300 font-semibold">Calibrated Score:</span>
                  <span className="text-sm font-mono font-bold text-cyan-400">
                    {(agent.confidence * 100).toFixed(0)}%
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-3 text-center my-3">
                  <div className="bg-slate-900 p-2 rounded-xl border border-slate-800">
                    <div className="text-[10px] text-slate-400">Fact References (E)</div>
                    <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">{agent.factCount}</div>
                  </div>
                  <div className="bg-slate-900 p-2 rounded-xl border border-slate-800">
                    <div className="text-[10px] text-slate-400">Unverified Assumptions (A)</div>
                    <div className="text-sm font-bold text-amber-400 font-mono mt-0.5">{agent.assumptionsCount}</div>
                  </div>
                  <div className="bg-slate-900 p-2 rounded-xl border border-slate-800">
                    <div className="text-[10px] text-slate-400">Risk Penalty (P)</div>
                    <div className="text-sm font-bold text-rose-400 font-mono mt-0.5">{agent.riskPenalty.toFixed(2)}</div>
                  </div>
                </div>

                <div className="text-[10px] text-slate-500 font-mono text-center">
                  Formula: C = (E / (E + A)) × (1.0 - P_risk), clamped to [0.05, 0.98]
                </div>
              </div>
            </div>

            {/* Produced Artifacts */}
            <div>
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <FileCode className="w-4 h-4 text-cyan-400" /> Produced Artifacts ({agentArtifacts.length})
              </h4>
              <div className="space-y-2">
                {agentArtifacts.map((art) => (
                  <div
                    key={art.id}
                    className="flex items-center justify-between bg-slate-950/60 border border-slate-800 p-3 rounded-2xl hover:border-cyan-500/40 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <FileCode className="w-4 h-4 text-cyan-400" />
                      <div>
                        <div className="text-xs font-semibold text-slate-200">{art.title}</div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          v{art.version} • Produced at {art.createdAt}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        selectArtifact(art);
                        onClose();
                      }}
                      className="text-xs text-cyan-400 hover:text-cyan-300 bg-cyan-950/50 border border-cyan-800/40 px-3 py-1 rounded-xl transition-colors font-semibold"
                    >
                      View Artifact
                    </button>
                  </div>
                ))}
                {agentArtifacts.length === 0 && (
                  <div className="text-xs text-slate-500 italic p-3 text-center bg-slate-950/30 rounded-2xl border border-slate-800/50">
                    No artifacts generated yet in this session.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Modal Footer Controls */}
          <div className="p-4 border-t border-slate-800 bg-slate-950 flex items-center justify-between">
            <button
              onClick={() => {
                requestReanalysis(agentRole);
                onClose();
              }}
              className="flex items-center gap-1.5 text-xs text-amber-300 bg-amber-950/60 border border-amber-800/40 px-4 py-2 rounded-xl hover:bg-amber-900/60 transition-colors font-semibold"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Request Re-analysis
            </button>
            <button
              onClick={onClose}
              className="text-xs text-slate-300 bg-slate-800 hover:bg-slate-700 px-5 py-2 rounded-xl transition-colors font-semibold"
            >
              Close
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
