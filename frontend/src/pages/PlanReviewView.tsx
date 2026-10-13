import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  ArrowRight,
  Plus,
  Trash2,
  Pencil,
  Check,
  Sparkles,
  Compass,
  Loader2,
} from 'lucide-react';
import { QuorumLogo } from '../components/logo/QuorumLogo';

interface PlanReviewViewProps {
  topic: string;
  subquestions: string[];
  onConfirm: (editedSubquestions: string[]) => void;
  onBack: () => void;
}

const MAX_QUESTIONS = 5;

export const PlanReviewView: React.FC<PlanReviewViewProps> = ({
  topic,
  subquestions,
  onConfirm,
  onBack,
}) => {
  const [questions, setQuestions] = useState<string[]>([...subquestions]);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');
  const [newQuestion, setNewQuestion] = useState('');
  const [showAddInput, setShowAddInput] = useState(false);

  const handleStartEdit = (index: number) => {
    setEditingIndex(index);
    setEditValue(questions[index]);
  };

  const handleSaveEdit = () => {
    if (editingIndex === null || !editValue.trim()) return;
    const updated = [...questions];
    updated[editingIndex] = editValue.trim();
    setQuestions(updated);
    setEditingIndex(null);
    setEditValue('');
  };

  const handleDelete = (index: number) => {
    if (questions.length <= 1) return; // Keep at least 1
    setQuestions(questions.filter((_, i) => i !== index));
    if (editingIndex === index) {
      setEditingIndex(null);
      setEditValue('');
    } else if (editingIndex !== null && editingIndex > index) {
      setEditingIndex(editingIndex - 1);
    }
  };

  const handleAddQuestion = () => {
    if (!newQuestion.trim() || questions.length >= MAX_QUESTIONS) return;
    setQuestions([...questions, newQuestion.trim()]);
    setNewQuestion('');
    setShowAddInput(false);
  };

  const handleConfirm = () => {
    let finalQuestions = [...questions];
    if (editingIndex !== null && editValue.trim()) {
      finalQuestions[editingIndex] = editValue.trim();
    }
    const valid = finalQuestions.filter((q) => q.trim().length > 0);
    if (valid.length === 0) return;
    onConfirm(valid);
  };

  return (
    <div className="min-h-screen w-full bg-[#09090b] text-[#fafafa] flex flex-col selection:bg-white/20 selection:text-white">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#0c0d0f]/90 backdrop-blur-md border-b border-white/[0.08] px-4 lg:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3 overflow-hidden">
          <button
            onClick={onBack}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/[0.06] transition-colors cursor-pointer"
            title="Back to Workspace"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="space-y-0.5 text-left">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-zinc-400">
                Research Plan
              </span>
              <span className="text-zinc-600">•</span>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <Compass className="w-2.5 h-2.5" />
                Review & Edit
              </span>
            </div>
            <h1 className="text-sm sm:text-base font-semibold text-white truncate max-w-xl">
              {topic}
            </h1>
          </div>
        </div>
      </header>

      {/* Progress bar */}
      <div className="w-full h-1 bg-white/[0.04]">
        <div className="h-full w-[15%] bg-gradient-to-r from-indigo-500 to-emerald-400" />
      </div>

      {/* Main Content */}
      <div className="flex-1 max-w-3xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-8">
        {/* Title Section */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="text-center space-y-3 pt-4"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono uppercase bg-indigo-500/10 border border-indigo-500/20 text-indigo-300">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Planner Agent Output</span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Review your research plan
          </h2>

          <p className="text-sm text-zinc-400 max-w-lg mx-auto leading-relaxed">
            The Planner Agent decomposed your topic into focused sub-questions.
            Edit, remove, or add your own questions before launching the research swarm.
          </p>
        </motion.div>

        {/* Sub-questions List */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="space-y-3"
        >
          {questions.map((q, idx) => (
            <div
              key={idx}
              className={`group p-4 rounded-2xl border transition-all ${
                editingIndex === idx
                  ? 'bg-[#17181c] border-indigo-500/30 ring-1 ring-indigo-500/20'
                  : 'bg-[#121316] border-white/[0.08] hover:border-white/15'
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Number Badge */}
                <span className="shrink-0 w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-mono font-bold flex items-center justify-center mt-0.5">
                  {idx + 1}
                </span>

                {/* Question Content */}
                <div className="flex-1 min-w-0">
                  {editingIndex === idx ? (
                    <div className="space-y-2">
                      <textarea
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSaveEdit();
                          }
                          if (e.key === 'Escape') {
                            setEditingIndex(null);
                            setEditValue('');
                          }
                        }}
                        rows={2}
                        className="w-full bg-transparent text-sm text-white placeholder-zinc-500 outline-none resize-none leading-relaxed border-b border-indigo-500/30 pb-2"
                      />
                      <div className="flex items-center gap-2">
                        <button
                          onClick={handleSaveEdit}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-500/20 text-indigo-300 text-xs font-medium hover:bg-indigo-500/30 transition-colors cursor-pointer"
                        >
                          <Check className="w-3 h-3" />
                          Save
                        </button>
                        <button
                          onClick={() => {
                            setEditingIndex(null);
                            setEditValue('');
                          }}
                          className="px-2.5 py-1 rounded-lg text-zinc-400 text-xs hover:text-white hover:bg-white/[0.06] transition-colors cursor-pointer"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p
                      onClick={() => handleStartEdit(idx)}
                      className="text-sm text-zinc-200 leading-relaxed text-left cursor-pointer hover:text-white transition-colors"
                      title="Click to edit sub-question"
                    >
                      {q}
                    </p>
                  )}
                </div>

                {/* Action Buttons (visible on mobile, hover on desktop) */}
                {editingIndex !== idx && (
                  <div className="shrink-0 flex items-center gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => handleStartEdit(idx)}
                      className="p-1.5 rounded-lg text-zinc-400 hover:text-indigo-400 hover:bg-indigo-500/10 transition-colors cursor-pointer"
                      title="Edit question"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                    {questions.length > 1 && (
                      <button
                        onClick={() => handleDelete(idx)}
                        className="p-1.5 rounded-lg text-zinc-400 hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
                        title="Remove question"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Add Question Section */}
          {questions.length < MAX_QUESTIONS && (
            <>
              {showAddInput ? (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="p-4 rounded-2xl bg-[#121316] border border-dashed border-emerald-500/30 space-y-3"
                >
                  <div className="flex items-start gap-3">
                    <span className="shrink-0 w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono font-bold flex items-center justify-center mt-0.5">
                      +
                    </span>
                    <textarea
                      autoFocus
                      value={newQuestion}
                      onChange={(e) => setNewQuestion(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleAddQuestion();
                        }
                        if (e.key === 'Escape') {
                          setShowAddInput(false);
                          setNewQuestion('');
                        }
                      }}
                      placeholder="Type your custom research sub-question..."
                      rows={2}
                      className="flex-1 bg-transparent text-sm text-white placeholder-zinc-500 outline-none resize-none leading-relaxed"
                    />
                  </div>
                  <div className="flex items-center gap-2 pl-10">
                    <button
                      onClick={handleAddQuestion}
                      disabled={!newQuestion.trim()}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 text-xs font-medium hover:bg-emerald-500/30 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <Plus className="w-3 h-3" />
                      Add
                    </button>
                    <button
                      onClick={() => {
                        setShowAddInput(false);
                        setNewQuestion('');
                      }}
                      className="px-2.5 py-1 rounded-lg text-zinc-400 text-xs hover:text-white hover:bg-white/[0.06] transition-colors cursor-pointer"
                    >
                      Cancel
                    </button>
                  </div>
                </motion.div>
              ) : (
                <button
                  onClick={() => setShowAddInput(true)}
                  className="w-full p-3.5 rounded-2xl border border-dashed border-white/10 hover:border-emerald-500/30 bg-white/[0.01] hover:bg-emerald-500/5 transition-all flex items-center justify-center gap-2 text-xs text-zinc-400 hover:text-emerald-400 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add a custom sub-question ({questions.length}/{MAX_QUESTIONS})</span>
                </button>
              )}
            </>
          )}
        </motion.div>

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-white/[0.08]"
        >
          <div className="text-left space-y-1">
            <p className="text-xs text-zinc-400">
              {questions.length} sub-question{questions.length !== 1 ? 's' : ''} will be researched concurrently
            </p>
            <p className="text-[11px] text-zinc-500 font-mono">
              Estimated time: ~{(questions.length * 0.5).toFixed(1)}–{(questions.length * 0.8).toFixed(1)} min
            </p>
          </div>

          <button
            onClick={handleConfirm}
            disabled={questions.filter((q) => q.trim()).length === 0}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-white text-zinc-950 hover:bg-zinc-200 text-sm font-semibold transition-all cursor-pointer shadow-lg shadow-white/10 active:scale-[0.97] disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span>Run Research</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </motion.div>
      </div>
    </div>
  );
};
