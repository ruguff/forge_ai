import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import { HelpCircle, Sparkles, Send, Check, ShieldAlert, ArrowRight } from 'lucide-react';
import { ClarificationQuestion } from '../../types/office';

interface AdaptiveClarificationModalProps {
  question: ClarificationQuestion;
  onAnswer: (questionId: string, answer: string) => Promise<void>;
  onClose?: () => void;
}

export const AdaptiveClarificationModal: React.FC<AdaptiveClarificationModalProps> = ({
  question,
  onAnswer,
}) => {
  const [selectedOption, setSelectedOption] = useState<string>('');
  const [customText, setCustomText] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const activeAnswer = customText.trim() || selectedOption;

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!activeAnswer || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onAnswer(question.question_id, activeAnswer);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUseAutonomousDefault = async () => {
    const defaultOption = question.possible_options[0] || 'Standard recommended configuration';
    setIsSubmitting(true);
    try {
      await onAnswer(question.question_id, defaultOption);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-slate-950/85 backdrop-blur-md">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        className="bg-slate-900 border border-cyan-500/40 rounded-3xl w-full max-w-2xl overflow-hidden shadow-[0_0_50px_rgba(6,182,212,0.15)] p-7 flex flex-col space-y-5"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-950/90 border border-cyan-500/60 flex items-center justify-center text-cyan-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono font-bold text-cyan-400 uppercase tracking-widest">
                  Requirement Engine · Adaptive Clarification
                </span>
                <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-amber-950/60 text-amber-400 border border-amber-500/40">
                  CRITICAL IMPACT
                </span>
              </div>
              <h3 className="text-sm font-semibold text-slate-200 mt-0.5">
                PROJECTFORGE needs your decision to continue
              </h3>
            </div>
          </div>
          <span className="text-[10px] font-mono text-slate-500 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800">
            {question.question_id}
          </span>
        </div>

        {/* Targeted Question Box */}
        <div className="bg-slate-950/80 border border-slate-800/80 rounded-2xl p-4 space-y-2">
          <h4 className="text-sm font-bold text-slate-100 leading-snug">
            {question.question}
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1 text-[11px]">
            <div className="bg-cyan-950/30 border border-cyan-800/40 p-2.5 rounded-xl text-slate-300">
              <span className="font-bold text-cyan-400 block mb-0.5">Why this matters:</span>
              <span className="text-slate-400 leading-relaxed">{question.reason}</span>
            </div>
            <div className="bg-amber-950/30 border border-amber-800/40 p-2.5 rounded-xl text-slate-300">
              <span className="font-bold text-amber-400 block mb-0.5">Impact if unknown:</span>
              <span className="text-slate-400 leading-relaxed">{question.impact_if_unknown}</span>
            </div>
          </div>
        </div>

        {/* Recommended Options */}
        {question.possible_options && question.possible_options.length > 0 && (
          <div className="space-y-2">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Curated Architectural Options (Click to select):
            </span>
            <div className="space-y-2">
              {question.possible_options.map((opt, idx) => {
                const isSelected = selectedOption === opt && !customText.trim();
                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setSelectedOption(opt);
                      setCustomText('');
                    }}
                    className={`w-full text-left p-3 rounded-xl text-xs transition-all flex items-center justify-between border ${
                      isSelected
                        ? 'bg-cyan-950/70 border-cyan-400 text-cyan-200 shadow-sm'
                        : 'bg-slate-950/50 border-slate-800 hover:border-slate-700 text-slate-300'
                    }`}
                  >
                    <span className="pr-4 leading-relaxed">{opt}</span>
                    <div
                      className={`w-4 h-4 rounded-full flex items-center justify-center border shrink-0 ${
                        isSelected
                          ? 'border-cyan-400 bg-cyan-500 text-slate-950'
                          : 'border-slate-700 bg-slate-900'
                      }`}
                    >
                      {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Custom Input */}
        <form onSubmit={handleSubmit} className="space-y-3 pt-1">
          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1">
              Or specify your custom requirements:
            </label>
            <input
              type="text"
              value={customText}
              onChange={(e) => {
                setCustomText(e.target.value);
                if (e.target.value) setSelectedOption('');
              }}
              placeholder="e.g. Prefer commercial 30cm GeoTIFF with nightly automated synchronization"
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400"
            />
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={handleUseAutonomousDefault}
              disabled={isSubmitting}
              className="text-xs text-slate-400 hover:text-cyan-400 transition-colors flex items-center gap-1.5"
            >
              <span>Accept System Default</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>

            <button
              type="submit"
              disabled={!activeAnswer || isSubmitting}
              className="flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-40 text-slate-950 font-bold text-xs px-5 py-2.5 rounded-xl transition-all shadow-md"
            >
              <span>{isSubmitting ? 'Confirming...' : 'Submit Decision & Continue'}</span>
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
};
