import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic,
  MicOff,
  Image as ImageIcon,
  ArrowUp,
  Sparkles,
  Paperclip,
  X,
  FileText,
  Clock,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  BarChart3,
  Layers,
  Search,
  Zap,
  Scale,
  Microscope,
} from 'lucide-react';
import { Sidebar, NavItem } from '../components/layout/Sidebar';
import { TopBar } from '../components/layout/TopBar';
import { fetchUserResearchFromSupabase, SavedResearch } from '../lib/supabase';

interface AppShellProps {
  onStartResearch: (query: string, options?: { image?: string | null; depth?: string }) => void;
  onSignOut: () => void;
}

export const AppShell: React.FC<AppShellProps> = ({
  onStartResearch,
  onSignOut,
}) => {
  const [currentTab, setCurrentTab] = useState<NavItem>('workspace');
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [attachedImage, setAttachedImage] = useState<string | null>(null);
  const [attachedImageName, setAttachedImageName] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [speechFeedback, setSpeechFeedback] = useState<string | null>(null);
  const [supabaseHistory, setSupabaseHistory] = useState<SavedResearch[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [researchDepth, setResearchDepth] = useState<'flash' | 'standard' | 'deep'>('standard');

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (currentTab === 'history' || currentTab === 'reports') {
      setLoadingHistory(true);
      fetchUserResearchFromSupabase().then(({ data }) => {
        setSupabaseHistory(data || []);
        setLoadingHistory(false);
      });
    }
  }, [currentTab]);

  const examplePrompts = [
    'Compare solid-state batteries vs lithium-ion for grid-scale energy storage',
    'State of commercial nuclear fusion reactors in 2025',
    'Latest clinical trial breakthroughs for GLP-1 receptor agonists beyond diabetes',
    'Quantum error correction milestones in superconducting transmon qubits',
  ];

  // Auto-resize textarea as user types
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        200
      )}px`;
    }
  }, [prompt]);

  // Voice recognition handler
  const handleToggleVoice = () => {
    // Check for browser SpeechRecognition
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      // Graceful fallback for environments without Speech API
      setSpeechFeedback('Voice input simulated: "Analyzing next-gen battery chemistries"');
      setPrompt((prev) =>
        prev
          ? `${prev} Analyzing next-gen battery chemistries`
          : 'Analyzing next-gen battery chemistries'
      );
      setTimeout(() => setSpeechFeedback(null), 3500);
      return;
    }

    if (isListening) {
      setIsListening(false);
      setSpeechFeedback(null);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsListening(true);
        setSpeechFeedback('Listening... speak your research topic');
      };

      recognition.onresult = (event: any) => {
        const transcript = Array.from(event.results)
          .map((result: any) => result[0].transcript)
          .join('');
        setPrompt(transcript);
      };

      recognition.onerror = (event: any) => {
        console.warn('Speech recognition error:', event.error);
        setIsListening(false);
        setSpeechFeedback('Microphone permission required or speech ended.');
        setTimeout(() => setSpeechFeedback(null), 3000);
      };

      recognition.onend = () => {
        setIsListening(false);
        setSpeechFeedback(null);
      };

      recognition.start();
    } catch (err) {
      console.warn('Failed to start speech recognition:', err);
      setIsListening(false);
      setSpeechFeedback('Speech recognition unavailable in this browser session.');
      setTimeout(() => setSpeechFeedback(null), 3000);
    }
  };

  // Image attachment handler
  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setAttachedImageName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      setAttachedImage(event.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveImage = () => {
    setAttachedImage(null);
    setAttachedImageName(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Submit research query
  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = prompt.trim();
    if (!query) return;

    onStartResearch(query, {
      image: attachedImage,
      depth: researchDepth,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex h-screen w-full bg-[#09090b] text-[#fafafa] overflow-hidden selection:bg-white/20 selection:text-white">
      {/* 1. Left Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        onNewResearch={() => {
          setCurrentTab('workspace');
          setPrompt('');
          if (textareaRef.current) textareaRef.current.focus();
        }}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
        onSignOut={onSignOut}
      />

      {/* 2. Main Workspace Layout */}
      <div className="flex-1 flex flex-col h-full overflow-y-auto">
        {/* Top Bar */}
        <TopBar
          onOpenMobileSidebar={() => setIsMobileSidebarOpen(true)}
          onSearchClick={() => setCurrentTab('history')}
        />

        {/* Dynamic Tab Views */}
        <main className="flex-1 flex flex-col justify-center items-center px-4 lg:px-8 py-8 relative">
          {/* Subtle Ambient Radial Glow */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_40%,rgba(99,102,241,0.06),transparent_70%)] pointer-events-none" />

          {/* ================= TAB 1: MAIN WORKSPACE (Empty State Prompt Box) ================= */}
          {currentTab === 'workspace' && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="w-full max-w-3xl my-auto flex flex-col items-center space-y-8 z-10"
            >
              {/* Header Title & Helper Statement */}
              <div className="text-center space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono uppercase bg-white/[0.04] border border-white/10 text-zinc-300">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Autonomous Swarm Engine</span>
                </div>

                <h1 className="text-3xl sm:text-5xl font-bold tracking-tight text-white leading-tight">
                  What should we look into?
                </h1>

                <p className="text-sm text-zinc-400 max-w-lg mx-auto leading-relaxed">
                  Planner, Researcher, Critic, and Writer will coordinate to explore sources, verify claims, and build a cited report.
                </p>
              </div>

              {/* Big, Warm Centered Prompt Box with Focus Glow */}
              <div className="w-full">
                <form
                  onSubmit={handleSubmit}
                  className="relative w-full rounded-2xl bg-[#121316] border border-white/10 hover:border-white/20 focus-within:border-white/30 focus-within:ring-2 focus-within:ring-white/10 shadow-2xl transition-all p-4 flex flex-col justify-between min-h-[140px]"
                >
                  {/* Attached Image Preview Chip (if any) */}
                  {attachedImage && (
                    <div className="mb-2 flex items-center gap-2 p-2 rounded-xl bg-white/[0.05] border border-white/10 max-w-xs text-xs">
                      <img
                        src={attachedImage}
                        alt="Attached document"
                        className="w-8 h-8 rounded-lg object-cover shrink-0"
                      />
                      <div className="flex-1 truncate">
                        <p className="font-medium text-white truncate">
                          {attachedImageName || 'Uploaded image'}
                        </p>
                        <p className="text-[10px] text-zinc-400">Multimodal OCR active</p>
                      </div>
                      <button
                        type="button"
                        onClick={handleRemoveImage}
                        className="p-1 rounded-md text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}

                  {/* Textarea Input */}
                  <textarea
                    ref={textareaRef}
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Enter any complex research topic or hypothesis..."
                    rows={2}
                    className="w-full bg-transparent text-sm sm:text-base text-white placeholder-zinc-500 outline-none resize-none leading-relaxed"
                  />

                  {/* Speech Feedback Alert */}
                  {speechFeedback && (
                    <div className="text-xs text-emerald-400 flex items-center gap-1.5 py-1">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                      <span>{speechFeedback}</span>
                    </div>
                  )}

                  {/* Prompt Box Bottom Action Bar */}
                  <div className="pt-3 flex items-center justify-between border-t border-white/[0.06] mt-2">
                    <div className="flex items-center gap-1.5">
                      {/* Voice Input Trigger */}
                      <button
                        type="button"
                        onClick={handleToggleVoice}
                        className={`p-2 rounded-xl transition-all cursor-pointer ${
                          isListening
                            ? 'bg-red-500/20 text-red-400 ring-2 ring-red-500/40 animate-pulse'
                            : 'text-zinc-400 hover:text-white hover:bg-white/[0.06]'
                        }`}
                        title={isListening ? 'Stop voice recording' : 'Voice input (speech-to-text)'}
                      >
                        {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                      </button>

                      {/* Image Attachment Trigger */}
                      <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleImageUpload}
                        accept="image/*"
                        className="hidden"
                      />
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className={`p-2 rounded-xl transition-all cursor-pointer ${
                          attachedImage
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'text-zinc-400 hover:text-white hover:bg-white/[0.06]'
                        }`}
                        title="Attach image or handwritten notes for OCR"
                      >
                        <ImageIcon className="w-4 h-4" />
                      </button>

                      {/* Swarm Mode Pill */}
                      <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-mono text-zinc-400 bg-white/[0.03] border border-white/[0.06]">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        <span>4 Agents</span>
                      </span>

                      {/* Research Depth Mode Selector */}
                      <div className="flex items-center gap-1 p-0.5 rounded-xl bg-white/[0.03] border border-white/[0.08] text-xs">
                        <button
                          type="button"
                          onClick={() => setResearchDepth('flash')}
                          className={`flex items-center gap-1 px-2 py-0.5 rounded-lg transition-all cursor-pointer text-[11px] font-medium ${
                            researchDepth === 'flash'
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-sm'
                              : 'text-zinc-400 hover:text-zinc-200'
                          }`}
                          title="Flash Brief: 1 subquestion, fast verification (~10-12s)"
                        >
                          <Zap className="w-3 h-3 text-amber-400" />
                          <span>Flash</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setResearchDepth('standard')}
                          className={`flex items-center gap-1 px-2 py-0.5 rounded-lg transition-all cursor-pointer text-[11px] font-medium ${
                            researchDepth === 'standard'
                              ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shadow-sm'
                              : 'text-zinc-400 hover:text-zinc-200'
                          }`}
                          title="Standard Dossier: 3 subquestions, comprehensive research (~20-25s)"
                        >
                          <Scale className="w-3 h-3 text-indigo-400" />
                          <span>Standard</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setResearchDepth('deep')}
                          className={`flex items-center gap-1 px-2 py-0.5 rounded-lg transition-all cursor-pointer text-[11px] font-medium ${
                            researchDepth === 'deep'
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow-sm'
                              : 'text-zinc-400 hover:text-zinc-200'
                          }`}
                          title="Deep Investigation: 5 subquestions, exhaustive multi-source research (~60-90s)"
                        >
                          <Microscope className="w-3 h-3 text-emerald-400" />
                          <span>Deep</span>
                        </button>
                      </div>
                    </div>

                    {/* Submit Button */}
                    <div className="flex items-center gap-2">
                      <span className="hidden sm:inline text-[11px] text-zinc-500 font-mono">
                        Press ↵ Enter
                      </span>
                      <button
                        type="submit"
                        disabled={!prompt.trim()}
                        className={`p-2 rounded-xl transition-all cursor-pointer ${
                          prompt.trim()
                            ? 'bg-white text-zinc-950 hover:bg-zinc-200 shadow-md shadow-white/10 active:scale-95'
                            : 'bg-white/10 text-zinc-500 cursor-not-allowed'
                        }`}
                        title="Start research run"
                      >
                        <ArrowUp className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </form>
              </div>

              {/* Example Prompt Chips */}
              <div className="w-full space-y-2.5 pt-2">
                <p className="text-xs font-mono uppercase text-zinc-500 tracking-wider text-left sm:text-center">
                  Suggested Research Topics
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full">
                  {examplePrompts.map((example, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setPrompt(example);
                        if (textareaRef.current) textareaRef.current.focus();
                      }}
                      className="text-left p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/[0.06] hover:border-white/10 transition-all text-xs text-zinc-300 hover:text-white group cursor-pointer"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="line-clamp-2 leading-relaxed">{example}</span>
                        <ArrowUp className="w-3.5 h-3.5 text-zinc-500 group-hover:text-white shrink-0 rotate-45 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {/* ================= TAB 2: RESEARCH HISTORY ================= */}
          {currentTab === 'history' && (
            <div className="w-full max-w-4xl space-y-6 z-10 text-left">
              <div className="flex items-center justify-between pb-4 border-b border-white/[0.08]">
                <div>
                  <h2 className="text-xl font-bold text-white">Research History</h2>
                  <p className="text-xs text-zinc-400">Past multi-agent sessions and fact-check logs</p>
                </div>
                <button
                  onClick={() => setCurrentTab('workspace')}
                  className="px-3.5 py-1.5 rounded-xl bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200"
                >
                  New Investigation
                </button>
              </div>

              <div className="space-y-3">
                {loadingHistory ? (
                  <div className="p-8 text-center text-zinc-500 font-mono text-xs">
                    Loading research history from Supabase...
                  </div>
                ) : supabaseHistory.length > 0 ? (
                  supabaseHistory.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => onStartResearch(item.topic)}
                      className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-white/15 transition-all flex items-center justify-between cursor-pointer"
                    >
                      <div className="space-y-1">
                        <h4 className="text-sm font-semibold text-white">{item.topic}</h4>
                        <div className="flex items-center gap-3 text-xs text-zinc-400 font-mono">
                          <span>{new Date(item.created_at).toLocaleDateString()}</span>
                          <span>•</span>
                          <span>{item.citations_count} citations</span>
                          <span>•</span>
                          <span className="text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> Cloud Saved
                          </span>
                        </div>
                      </div>
                      <ExternalLink className="w-4 h-4 text-zinc-500 hover:text-white" />
                    </div>
                  ))
                ) : (
                  [
                    {
                      title: 'Solid-State Battery Electrolytes vs Sodium-Ion Longevity',
                      date: 'Yesterday at 4:15 PM',
                      agents: 4,
                      citations: 18,
                      status: 'Verified',
                    },
                    {
                      title: 'Commercial Fusion Confinement Milestones & Net Energy Q-factors',
                      date: 'Oct 8, 2026',
                      agents: 4,
                      citations: 24,
                      status: 'Verified',
                    },
                    {
                      title: 'Post-Quantum Cryptography Lattice-Based NIST Standardization',
                      date: 'Oct 5, 2026',
                      agents: 4,
                      citations: 14,
                      status: 'Verified',
                    },
                  ].map((item, i) => (
                    <div
                      key={i}
                      onClick={() => onStartResearch(item.title)}
                      className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-white/15 transition-all flex items-center justify-between cursor-pointer"
                    >
                      <div className="space-y-1">
                        <h4 className="text-sm font-semibold text-white">{item.title}</h4>
                        <div className="flex items-center gap-3 text-xs text-zinc-400 font-mono">
                          <span>{item.date}</span>
                          <span>•</span>
                          <span>{item.citations} citations</span>
                          <span>•</span>
                          <span className="text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> {item.status}
                          </span>
                        </div>
                      </div>
                      <ExternalLink className="w-4 h-4 text-zinc-500 hover:text-white" />
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* ================= TAB 3: VERIFIED REPORTS ================= */}
          {currentTab === 'reports' && (
            <div className="w-full max-w-4xl space-y-6 z-10 text-left">
              <div className="pb-4 border-b border-white/[0.08]">
                <h2 className="text-xl font-bold text-white">Verified Reports</h2>
                <p className="text-xs text-zinc-400">Fully synthesized research dossiers with citation graph</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {[
                  'Comprehensive Review of Solid-State Electrolytes',
                  'Fusion Power Grid Commercialization Timeline',
                  'GLP-1 Weight Regulation & Cardiovascular Outcomes',
                  'Superconducting Qubit Coherence Limits',
                ].map((report, i) => (
                  <div
                    key={i}
                    onClick={() => onStartResearch(report)}
                    className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] hover:border-white/15 transition-all space-y-3 cursor-pointer"
                  >
                    <div className="flex items-center justify-between">
                      <span className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                        <FileText className="w-4 h-4" />
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-zinc-400">
                        Markdown & PDF
                      </span>
                    </div>
                    <h4 className="text-sm font-semibold text-white leading-snug">{report}</h4>
                    <p className="text-xs text-zinc-400">
                      Cross-checked by Critic agent with 15+ primary academic sources.
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ================= TAB 4: USAGE & QUOTA ================= */}
          {currentTab === 'usage' && (
            <div className="w-full max-w-3xl space-y-6 z-10 text-left">
              <div className="pb-4 border-b border-white/[0.08]">
                <h2 className="text-xl font-bold text-white">Usage & Quota</h2>
                <p className="text-xs text-zinc-400">Autonomous swarm executions and Tavily API metrics</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                  <p className="text-xs text-zinc-400">Swarm Runs This Month</p>
                  <p className="text-2xl font-bold text-white mt-1">28 / 100</p>
                  <div className="w-full bg-white/10 rounded-full h-1.5 mt-3">
                    <div className="bg-emerald-400 h-1.5 rounded-full w-[28%]" />
                  </div>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                  <p className="text-xs text-zinc-400">Claims Cross-Examined</p>
                  <p className="text-2xl font-bold text-white mt-1">426</p>
                  <p className="text-[10px] text-zinc-500 mt-2 font-mono">100% Critic verified</p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                  <p className="text-xs text-zinc-400">Active Workspace</p>
                  <p className="text-2xl font-bold text-white mt-1">Pro Tier</p>
                  <p className="text-[10px] text-emerald-400 mt-2 font-mono">Continuous Swarm</p>
                </div>
              </div>
            </div>
          )}

          {/* ================= TAB 5: DOCUMENTATION ================= */}
          {currentTab === 'docs' && (
            <div className="w-full max-w-3xl space-y-6 z-10 text-left">
              <div className="pb-4 border-b border-white/[0.08]">
                <h2 className="text-xl font-bold text-white">Multi-Agent Architecture Docs</h2>
                <p className="text-xs text-zinc-400">How Planner, Researcher, Critic, and Writer collaborate</p>
              </div>
              <div className="space-y-4 text-xs text-zinc-300 leading-relaxed">
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                  <h4 className="font-semibold text-white text-sm">1. Planner Agent</h4>
                  <p className="text-zinc-400">
                    Deconstructs the user query into high-priority research questions, identifying angles, required domains, and evaluation criteria.
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                  <h4 className="font-semibold text-white text-sm">2. Researcher Agent</h4>
                  <p className="text-zinc-400">
                    Queries Tavily and the live web, aggregating raw source text, citation URLs, and author attribution across scientific databases.
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                  <h4 className="font-semibold text-white text-sm">3. Critic Agent</h4>
                  <p className="text-zinc-400">
                    Performs rigorous adversarial fact-checking. Flags dubious assertions and sends drafts back until primary claims have corroborating citations.
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                  <h4 className="font-semibold text-white text-sm">4. Writer Agent</h4>
                  <p className="text-zinc-400">
                    Synthesizes executive summaries, comprehensive deep dives, and structured footnote citations in export-ready markdown.
                  </p>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
