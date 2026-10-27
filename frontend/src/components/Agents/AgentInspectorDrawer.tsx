import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import { AgentRole } from '../../types/office';
import {
  X,
  ShieldCheck,
  FileCode,
  RotateCcw,
  Clock,
  Quote,
  Layers,
  AlertTriangle,
  Cpu,
  CheckCircle2,
  FileText,
} from 'lucide-react';

interface AgentInspectorDrawerProps {
  agentRole: AgentRole | null;
  onClose: () => void;
}

export const AgentInspectorDrawer: React.FC<AgentInspectorDrawerProps> = ({
  agentRole,
  onClose,
}) => {
  const { agents, artifacts, requestReanalysis, selectArtifact } = useOffice();
  const [activeTab, setActiveTab] = useState<'contract' | 'reasoning' | 'artifacts'>('contract');

  if (!agentRole) return null;
  const agent = agents[agentRole];
  if (!agent) return null;

  const agentArtifacts = artifacts.filter((a) => a.producedBy === agentRole);

  return (
    <AnimatePresence>
      <motion.aside
        initial={{ x: 420, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 420, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 280, damping: 28 }}
        className="fixed top-[58px] right-0 bottom-0 w-[400px] max-w-full bg-slate-950/98 border-l border-slate-800 shadow-2xl z-30 flex flex-col backdrop-blur-2xl select-none"
      >
        {/* Drawer Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/70">
          <div className="flex items-center gap-3">
            <div
              className={`w-11 h-11 rounded-2xl bg-gradient-to-br ${agent.avatarColor} p-0.5 flex items-center justify-center shadow-lg`}
            >
              <div className="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center text-white font-extrabold text-base">
                {agent.name[0]}
              </div>
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <span>{agent.name}</span>
                <span
                  className="text-[9px] px-2 py-0.5 rounded-full font-mono font-bold uppercase border"
                  style={{
                    color: agent.accentColor,
                    borderColor: `${agent.accentColor}40`,
                    backgroundColor: `${agent.accentColor}15`,
                  }}
                >
                  {agent.status}
                </span>
              </h3>
              <p className="text-[10px] text-slate-400 font-mono truncate">{agent.roleTitle}</p>
            </div>
          </div>
          <button
            aria-label="Close agent details"
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="px-4 py-2 border-b border-slate-800/80 bg-slate-900/40 flex items-center gap-2 text-[11px] font-mono">
          <button
            onClick={() => setActiveTab('contract')}
            className={`px-3 py-1 rounded-lg transition-colors ${
              activeTab === 'contract'
                ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/60 font-bold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Contract & Spec
          </button>
          <button
            onClick={() => setActiveTab('reasoning')}
            className={`px-3 py-1 rounded-lg transition-colors ${
              activeTab === 'reasoning'
                ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/60 font-bold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Decisions & Audit
          </button>
          <button
            onClick={() => setActiveTab('artifacts')}
            className={`px-3 py-1 rounded-lg transition-colors ${
              activeTab === 'artifacts'
                ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/60 font-bold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Artifacts ({agentArtifacts.length})
          </button>
        </div>

        {/* Drawer Body */}
        <div className="p-4 overflow-y-auto space-y-4 flex-1 text-xs">
          {activeTab === 'contract' && (
            <>
              {/* Agent Philosophy */}
              <div className="bg-slate-900/80 border border-slate-800 p-3.5 rounded-2xl">
                <div className="flex items-center gap-1.5 text-[10px] font-bold text-cyan-400 uppercase tracking-wider mb-1">
                  <Quote className="w-3.5 h-3.5" /> Agent Operational Philosophy
                </div>
                <p className="text-xs italic text-slate-300">"{agent.personality.quote}"</p>
                <div className="mt-2 text-[10px] text-slate-400">
                  <span className="font-semibold text-slate-300">Core Focus:</span> {agent.personality.focus}
                </div>
              </div>

              {/* Current Task & Activity */}
              <div>
                <h4 className="text-[10px] font-bold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-cyan-400" /> Active Assignment
                </h4>
                <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-2xl space-y-2">
                  <div className="text-xs text-slate-200 font-semibold">
                    <span className="text-slate-400 font-normal">Task:</span> {agent.currentTask}
                  </div>
                  <div className="text-xs text-cyan-300 bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
                    <span className="text-slate-500 font-semibold font-mono">Activity:</span> {agent.activityMessage}
                  </div>
                </div>
              </div>

              {/* Confidence Breakdown */}
              <div>
                <h4 className="text-[10px] font-bold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" /> Calibrated Confidence Formula
                </h4>
                <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-2xl">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-slate-300 font-semibold">Empirical Score:</span>
                    <span className="text-sm font-mono font-bold text-cyan-400">
                      {(agent.confidence * 100).toFixed(0)}%
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center my-2">
                    <div className="bg-slate-950 p-2 rounded-xl border border-slate-800">
                      <div className="text-[9px] text-slate-400 font-mono">Facts (E)</div>
                      <div className="text-xs font-bold text-emerald-400 font-mono mt-0.5">{agent.factCount}</div>
                    </div>
                    <div className="bg-slate-950 p-2 rounded-xl border border-slate-800">
                      <div className="text-[9px] text-slate-400 font-mono">Assumptions (A)</div>
                      <div className="text-xs font-bold text-amber-400 font-mono mt-0.5">{agent.assumptionsCount}</div>
                    </div>
                    <div className="bg-slate-950 p-2 rounded-xl border border-slate-800">
                      <div className="text-[9px] text-slate-400 font-mono">Risk (P)</div>
                      <div className="text-xs font-bold text-rose-400 font-mono mt-0.5">{agent.riskPenalty.toFixed(2)}</div>
                    </div>
                  </div>

                  <div className="text-[9px] text-slate-500 font-mono text-center">
                    C = (E / (E + A)) × (1.0 - P_risk)
                  </div>
                </div>
              </div>
            </>
          )}

          {activeTab === 'reasoning' && (
            <div className="space-y-3">
              {/* Inputs */}
              <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-2xl">
                <div className="text-[10px] font-bold text-slate-400 uppercase font-mono mb-1">Inputs</div>
                <p className="text-xs text-slate-200">
                  ProjectContext v1, 17-dimension extracted specifications, and upstream specialist assertions.
                </p>
              </div>

              {/* Decisions */}
              <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-2xl">
                <div className="text-[10px] font-bold text-slate-400 uppercase font-mono mb-1">Decisions</div>
                <p className="text-xs text-slate-200">
                  Selected architectural trade-offs recorded with minimum 2 evaluated alternatives.
                </p>
              </div>

              {/* Assumptions & Risks */}
              <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-2xl">
                <div className="text-[10px] font-bold text-slate-400 uppercase font-mono mb-1">Assumptions & Risks</div>
                <p className="text-xs text-slate-200">
                  Identified potential scale bottlenecks and fallback strategies. All assumptions tagged explicitly.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'artifacts' && (
            <div className="space-y-2">
              {agentArtifacts.map((art) => (
                <div
                  key={art.id}
                  className="flex items-center justify-between bg-slate-900/60 border border-slate-800 p-3 rounded-2xl hover:border-cyan-500/40 transition-colors"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <FileCode className="w-4 h-4 text-cyan-400 shrink-0" />
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-slate-200 truncate">{art.title}</div>
                      <div className="text-[9px] text-slate-400 font-mono">v{art.version} • {art.createdAt}</div>
                    </div>
                  </div>
                  <button
                    onClick={() => selectArtifact(art)}
                    className="text-[10px] text-cyan-400 hover:text-cyan-300 bg-cyan-950/60 border border-cyan-800/40 px-3 py-1 rounded-xl font-semibold shrink-0 cursor-pointer"
                  >
                    Inspect
                  </button>
                </div>
              ))}
              {agentArtifacts.length === 0 && (
                <div className="text-xs text-slate-500 italic p-6 text-center bg-slate-900/30 rounded-2xl border border-slate-800/60">
                  No artifacts generated yet. Output will appear here upon phase completion.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between">
          <button
            onClick={() => {
              requestReanalysis(agentRole);
              onClose();
            }}
            className="flex items-center gap-1.5 text-xs text-amber-300 bg-amber-950/60 border border-amber-800/40 px-3.5 py-1.5 rounded-xl hover:bg-amber-900/60 transition-colors font-semibold cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Re-analyze
          </button>
          <button
            aria-label="Close agent details"
            onClick={onClose}
            className="text-xs text-slate-300 bg-slate-800 hover:bg-slate-700 px-4 py-1.5 rounded-xl font-semibold cursor-pointer"
          >
            Close
          </button>
        </div>
      </motion.aside>
    </AnimatePresence>
  );
};
