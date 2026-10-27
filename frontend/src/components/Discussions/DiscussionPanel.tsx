import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import { X, MessageSquare, Users, AlertCircle, FileCode } from 'lucide-react';

interface DiscussionPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DiscussionPanel: React.FC<DiscussionPanelProps> = ({ isOpen, onClose }) => {
  const { activeDiscussion, agents, selectArtifact, artifacts } = useOffice();

  if (!isOpen || !activeDiscussion) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-end p-4 bg-slate-950/70 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, x: 300 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 300 }}
          className="bg-slate-900 border border-slate-700 rounded-3xl w-full max-w-xl h-[85vh] shadow-2xl flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
            <div>
              <div className="flex items-center gap-2 text-xs font-bold text-purple-400 uppercase tracking-wider">
                <Users className="w-4 h-4" /> Agent Round-Table Discussion
              </div>
              <h3 className="text-sm font-bold text-slate-100 mt-1">{activeDiscussion.topic}</h3>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Participants bar */}
          <div className="p-3 bg-slate-950/40 border-b border-slate-800/80 flex items-center gap-3">
            <span className="text-[11px] text-slate-400 font-mono">Participants:</span>
            <div className="flex items-center gap-2">
              {activeDiscussion.participants.map((role) => {
                const ag = agents[role];
                return (
                  <span
                    key={role}
                    className="text-[11px] font-semibold bg-slate-800 text-slate-200 px-2.5 py-0.5 rounded-full border border-slate-700"
                  >
                    {ag ? ag.name : role}
                  </span>
                );
              })}
            </div>
          </div>

          {/* Messages list */}
          <div className="p-5 overflow-y-auto space-y-4 flex-1">
            {activeDiscussion.messages.map((msg) => {
              const sender = agents[msg.senderRole];
              const isConflict = msg.isConflictPoint;

              return (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`p-4 rounded-2xl border transition-all ${
                    isConflict
                      ? 'bg-amber-950/30 border-amber-600/50 shadow-md'
                      : 'bg-slate-950/60 border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-100">{msg.senderName}</span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        ({sender?.roleTitle.replace('Principal ', '')})
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-500 font-mono">{msg.timestamp}</span>
                  </div>

                  <p className="text-xs text-slate-200 leading-relaxed">{msg.text}</p>

                  {isConflict && (
                    <div className="mt-2.5 pt-2 border-t border-amber-700/40 flex items-center gap-1.5 text-[10px] font-bold text-amber-400">
                      <AlertCircle className="w-3.5 h-3.5" /> Contradiction point logged for Conflict Resolver
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>

          {/* Footer Actions */}
          <div className="p-4 border-t border-slate-800 bg-slate-950 flex items-center justify-between">
            <span className="text-[11px] text-slate-500 font-mono">Discussion in progress...</span>
            <button
              onClick={onClose}
              className="text-xs text-slate-300 bg-slate-800 hover:bg-slate-700 px-5 py-2 rounded-xl transition-colors font-semibold"
            >
              Close Panel
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
