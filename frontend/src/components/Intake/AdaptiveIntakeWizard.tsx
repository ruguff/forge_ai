import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import { HelpCircle, ChevronRight, CheckCircle2, Sparkles, Send } from 'lucide-react';

export const INTAKE_QUESTIONS = [
  { id: 'Q1', title: 'Q1. Core Problem & Affected Persona', prompt: 'What specific problem does this software solve, and who suffers most from it?' },
  { id: 'Q2', title: 'Q2. Target Users & Operating Environment', prompt: 'Who will interact with this system daily, and in what deployment environment?' },
  { id: 'Q3', title: 'Q3. Desired Solution Flow', prompt: 'Describe the step-by-step user interaction flow from start to finish.' },
  { id: 'Q4', title: 'Q4. Core Functionality', prompt: 'What are the 2-3 absolute must-have core features for Phase 1?' },
  { id: 'Q5', title: 'Q5. Expected Input Data', prompt: 'What data formats, volumes, and sources will enter the system?' },
  { id: 'Q6', title: 'Q6. Expected Output Data', prompt: 'What reports, artifacts, or visual UI updates must the system produce?' },
  { id: 'Q7', title: 'Q7. Intelligence & Processing Logic', prompt: 'Can logic be resolved deterministically (rules, SQL, regex) or does it require probabilistic AI/ML?' },
  { id: 'Q8', title: 'Q8. Technology & Budget Constraints', prompt: 'What are your hardware, cloud host, legacy integration, or budget boundaries?' },
  { id: 'Q9', title: 'Q9. Scale & Availability SLA', prompt: 'How many concurrent users and what latency/downtime tolerance is required?' },
  { id: 'Q10', title: 'Q10. Objective Success Criteria', prompt: 'What quantifiable 3-month metrics define project success?' },
];

interface AdaptiveIntakeWizardProps {
  onComplete: () => void;
}

export const AdaptiveIntakeWizard: React.FC<AdaptiveIntakeWizardProps> = ({ onComplete }) => {
  const { currentIntakeIndex, answerIntakeQuestion, launchPipeline, intakeAnswers } = useOffice();
  const [currentText, setCurrentText] = useState('');

  const currentQ = INTAKE_QUESTIONS[currentIntakeIndex];
  const isFinished = currentIntakeIndex >= INTAKE_QUESTIONS.length;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentQ || !currentText.trim()) return;

    await answerIntakeQuestion(currentQ.id, currentText.trim());
    setCurrentText('');
  };

  const handleLaunch = async () => {
    await launchPipeline();
    onComplete();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-slate-950/90 backdrop-blur-lg">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-slate-900 border border-cyan-500/40 rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl p-8 flex flex-col"
      >
        {!isFinished && currentQ ? (
          <div>
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-cyan-400" />
                <span className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider">
                  Adaptive Intake Orchestrator ({currentIntakeIndex + 1} / 10)
                </span>
              </div>
              <div className="w-32 bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                <div
                  className="bg-cyan-400 h-full transition-all duration-300"
                  style={{ width: `${((currentIntakeIndex + 1) / 10) * 100}%` }}
                />
              </div>
            </div>

            <h3 className="text-lg font-bold text-slate-100 mb-2">{currentQ.title}</h3>
            <p className="text-xs text-slate-300 mb-6 leading-relaxed bg-slate-950/60 p-4 rounded-2xl border border-slate-800">
              {currentQ.prompt}
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <textarea
                value={currentText}
                onChange={(e) => setCurrentText(e.target.value)}
                placeholder="Enter details..."
                rows={4}
                className="w-full bg-slate-950 border border-slate-700 rounded-2xl p-4 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition-colors"
                autoFocus
              />

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => answerIntakeQuestion(currentQ.id, 'Standard enterprise default settings.')}
                  className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Use Standard Defaults
                </button>
                <button
                  type="submit"
                  disabled={!currentText.trim()}
                  className="flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 disabled:opacity-50 text-slate-950 font-bold text-xs px-6 py-2.5 rounded-xl transition-all shadow-md"
                >
                  <span>Submit & Next Question</span>
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </form>
          </div>
        ) : (
          <div className="text-center py-6 space-y-6">
            <div className="w-16 h-16 bg-emerald-950/80 border border-emerald-500/60 rounded-3xl flex items-center justify-center text-emerald-400 mx-auto">
              <CheckCircle2 className="w-8 h-8" />
            </div>

            <div>
              <h3 className="text-xl font-bold text-slate-100">Your Project Team Is Ready!</h3>
              <p className="text-xs text-slate-400 mt-2 max-w-md mx-auto leading-relaxed">
                All 10 adaptive clarification domain responses have been collected. All 8 AI specialists will now execute autonomous analysis across their workspaces.
              </p>
            </div>

            <button
              onClick={handleLaunch}
              className="w-full bg-gradient-to-r from-emerald-400 via-teal-500 to-cyan-500 hover:from-emerald-300 hover:to-cyan-400 text-slate-950 font-extrabold text-sm py-3.5 rounded-2xl shadow-xl transition-all transform hover:scale-[1.02] flex items-center justify-center gap-2"
            >
              <Sparkles className="w-5 h-5" />
              <span>START MULTI-AGENT PIPELINE ANALYSIS</span>
            </button>
          </div>
        )}
      </motion.div>
    </div>
  );
};
