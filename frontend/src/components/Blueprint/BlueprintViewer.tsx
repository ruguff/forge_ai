import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useOffice } from '../../context/OfficeContext';
import { X, FileText, Download, Check, Sparkles, Layers, List } from 'lucide-react';

interface BlueprintViewerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const BlueprintViewer: React.FC<BlueprintViewerProps> = ({ isOpen, onClose }) => {
  const { finalBlueprintMarkdown, projectId } = useOffice();
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'blueprint' | 'traceability'>('blueprint');

  if (!isOpen || !finalBlueprintMarkdown) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(finalBlueprintMarkdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([finalBlueprintMarkdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `FINAL_PROJECT_BLUEPRINT_${projectId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Section Table of Contents parser
  const sections = finalBlueprintMarkdown
    .split('\n')
    .filter((line) => line.startsWith('## '))
    .map((line) => line.replace('## ', ''));

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-slate-950/90 backdrop-blur-lg">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-slate-900 border border-emerald-500/50 rounded-3xl w-full max-w-5xl h-[90vh] shadow-2xl flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/90">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-950/80 border border-emerald-600/60 flex items-center justify-center text-emerald-400">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-emerald-400 uppercase tracking-wide">
                    Canonical Synthesis Output
                  </span>
                  <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-700/50 px-2 py-0.5 rounded-full font-bold">
                    27 Sections Verified
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-100 mt-0.5">FINAL_PROJECT_BLUEPRINT.md</h3>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-xl border border-slate-700 transition-colors font-medium"
              >
                {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <FileText className="w-4 h-4" />}
                <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
              </button>
              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 text-xs bg-emerald-500 hover:bg-emerald-400 text-slate-950 px-3.5 py-1.5 rounded-xl transition-colors font-bold shadow-md"
              >
                <Download className="w-4 h-4" />
                <span>Export .md</span>
              </button>
              <button
                onClick={onClose}
                className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors ml-2"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Navigation Bar */}
          <div className="px-6 py-2 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between text-xs">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setActiveTab('blueprint')}
                className={`flex items-center gap-1.5 py-1.5 px-3 rounded-lg font-semibold transition-colors ${
                  activeTab === 'blueprint'
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-700/50'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <List className="w-4 h-4" /> 27-Section Blueprint
              </button>
              <button
                onClick={() => setActiveTab('traceability')}
                className={`flex items-center gap-1.5 py-1.5 px-3 rounded-lg font-semibold transition-colors ${
                  activeTab === 'traceability'
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-700/50'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Layers className="w-4 h-4" /> Requirement Traceability Matrix
              </button>
            </div>
            <span className="text-[11px] text-slate-500 font-mono">
              User Answer → Req ID → Agent Analysis → Decision → Section
            </span>
          </div>

          {/* Main Content Area */}
          <div className="flex-1 flex overflow-hidden">
            {/* Sidebar Table of Contents */}
            <div className="w-64 border-r border-slate-800 bg-slate-950/40 p-4 overflow-y-auto hidden md:block">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-3">
                Table of Contents ({sections.length})
              </div>
              <div className="space-y-1 text-xs">
                {sections.map((sec, idx) => (
                  <div
                    key={idx}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-300 hover:bg-slate-900 cursor-pointer truncate font-mono text-[11px] transition-colors"
                  >
                    {sec}
                  </div>
                ))}
              </div>
            </div>

            {/* Markdown Display */}
            <div className="flex-1 p-6 overflow-y-auto bg-slate-900/60 font-mono text-xs text-slate-200 leading-relaxed space-y-4">
              {activeTab === 'blueprint' ? (
                <pre className="whitespace-pre-wrap font-sans text-xs space-y-4 leading-relaxed text-slate-200">
                  {finalBlueprintMarkdown}
                </pre>
              ) : (
                <div className="space-y-4 font-sans text-xs">
                  <h4 className="text-sm font-bold text-emerald-400 uppercase tracking-wider">
                    Full Requirement Traceability Audit Trail
                  </h4>
                  <p className="text-slate-400">
                    Bidirectional mapping linking intake answers to requirement IDs, specialized agent analyses, arbitrated conflict decisions, and final blueprint sections.
                  </p>

                  <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden mt-4">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900 text-slate-400 font-mono text-[10px] uppercase">
                        <tr>
                          <th className="py-2.5 px-4">Req ID</th>
                          <th className="py-2.5 px-4">Intake Origin</th>
                          <th className="py-2.5 px-4">Spec Content</th>
                          <th className="py-2.5 px-4">Agent Role</th>
                          <th className="py-2.5 px-4">Blueprint Section</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 text-slate-300">
                        <tr>
                          <td className="py-2.5 px-4 font-mono font-bold text-cyan-400">FR-001</td>
                          <td className="py-2.5 px-4">Intake Q1/Q4</td>
                          <td className="py-2.5 px-4">CSV file drag-and-drop upload</td>
                          <td className="py-2.5 px-4">Product / UX</td>
                          <td className="py-2.5 px-4 text-emerald-400 font-mono">Section 5 & 10</td>
                        </tr>
                        <tr>
                          <td className="py-2.5 px-4 font-mono font-bold text-cyan-400">FR-002</td>
                          <td className="py-2.5 px-4">Intake Q7</td>
                          <td className="py-2.5 px-4">Automated NLP sentiment scoring</td>
                          <td className="py-2.5 px-4">AI/ML Architect</td>
                          <td className="py-2.5 px-4 text-emerald-400 font-mono">Section 14 & 15</td>
                        </tr>
                        <tr>
                          <td className="py-2.5 px-4 font-mono font-bold text-cyan-400">NFR-001</td>
                          <td className="py-2.5 px-4">Intake Q9</td>
                          <td className="py-2.5 px-4">99.9% availability, SLA &lt; 100ms</td>
                          <td className="py-2.5 px-4">Engineering Lead</td>
                          <td className="py-2.5 px-4 text-emerald-400 font-mono">Section 6 & 9</td>
                        </tr>
                        <tr>
                          <td className="py-2.5 px-4 font-mono font-bold text-cyan-400">SEC-001</td>
                          <td className="py-2.5 px-4">Intake Q8</td>
                          <td className="py-2.5 px-4">OAuth2 + OIDC JWT authorization</td>
                          <td className="py-2.5 px-4">Security Auditor</td>
                          <td className="py-2.5 px-4 text-emerald-400 font-mono">Section 17</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
