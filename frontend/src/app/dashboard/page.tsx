"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { motion } from "framer-motion";
import { Search, Activity, CheckCircle, FileText, ArrowRight, Clock, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";

interface SessionSummary {
  id: string;
  query: string;
  status: string;
  quality_score: number | null;
  created_at: string;
}

export default function DashboardPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  
  const [query, setQuery] = useState("");
  const [loops, setLoops] = useState(1);
  const router = useRouter();

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const data = await api.get("/sessions?limit=10");
        setSessions(data.sessions);
        setTotal(data.total);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchSessions();
  }, []);

  const completed = sessions.filter(s => s.status === "completed").length;
  const avgQuality = sessions.length > 0 
    ? sessions.reduce((acc, s) => acc + (s.quality_score || 0), 0) / sessions.length 
    : 0;

  const handleStartResearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    router.push(`/research?q=${encodeURIComponent(query)}&loops=${loops}`);
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">AI Command Center</h1>
        <p className="text-[#9BA6C3] mt-1">Your intelligence operations overview.</p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: "Total Operations", value: total, icon: Activity, color: "text-[#00D4FF]", bg: "bg-[#00D4FF]/10" },
          { label: "Completed Reports", value: completed, icon: FileText, color: "text-[#7C5CFF]", bg: "bg-[#7C5CFF]/10" },
          { label: "Avg. Quality Score", value: `${(avgQuality * 100).toFixed(0)}%`, icon: CheckCircle, color: "text-[#14F195]", bg: "bg-[#14F195]/10" },
          { label: "System Status", value: "Online", icon: Activity, color: "text-green-400", bg: "bg-green-400/10" },
        ].map((m, i) => (
          <motion.div 
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="glass p-6 rounded-2xl flex items-center gap-4 border border-[rgba(255,255,255,0.05)]"
          >
            <div className={`p-3 rounded-xl ${m.bg}`}>
              <m.icon className={`w-6 h-6 ${m.color}`} />
            </div>
            <div>
              <p className="text-sm text-[#9BA6C3] font-medium">{m.label}</p>
              <h3 className="text-2xl font-bold text-white">{m.value}</h3>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Quick Start Form */}
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="lg:col-span-2 glass p-8 rounded-2xl border border-[#1e293b] relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-64 h-64 bg-[#00D4FF] opacity-5 blur-[100px] rounded-full pointer-events-none" />
          
          <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <Search className="w-5 h-5 text-[#00D4FF]" />
            New Intelligence Operation
          </h2>
          
          <form onSubmit={handleStartResearch} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-[#9BA6C3] mb-2">Target Subject</label>
              <textarea 
                value={query}
                onChange={e => setQuery(e.target.value)}
                rows={3}
                className="w-full bg-[#0D1424] border border-[#1e293b] rounded-xl p-4 text-white placeholder-[#475569] focus:outline-none focus:border-[#00D4FF] focus:ring-1 focus:ring-[#00D4FF] transition-all"
                placeholder="e.g., Market size and growth trajectory of AI semiconductors through 2030..."
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[#9BA6C3] mb-3">Operation Depth</label>
              <div className="flex gap-4">
                {[
                  { val: 1, label: "Quick Scan (1 loop)", desc: "Fast overview" },
                  { val: 3, label: "Deep Dive (3 loops)", desc: "Comprehensive analysis" },
                ].map((opt) => (
                  <label key={opt.val} className={`flex-1 cursor-pointer p-4 rounded-xl border transition-all ${loops === opt.val ? 'border-[#00D4FF] bg-[#00D4FF]/10' : 'border-[#1e293b] bg-[#0D1424] hover:border-[#475569]'}`}>
                    <div className="flex items-center gap-3">
                      <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${loops === opt.val ? 'border-[#00D4FF]' : 'border-[#475569]'}`}>
                        {loops === opt.val && <div className="w-2 h-2 rounded-full bg-[#00D4FF]" />}
                      </div>
                      <div>
                        <div className={`font-medium ${loops === opt.val ? 'text-white' : 'text-[#9BA6C3]'}`}>{opt.label}</div>
                        <div className="text-xs text-[#64748b] mt-0.5">{opt.desc}</div>
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <button 
              type="submit"
              className="w-full bg-gradient-to-r from-[#00D4FF] to-[#3b82f6] text-black font-semibold rounded-xl py-4 hover:opacity-90 transition-opacity flex justify-center items-center gap-2"
            >
              Execute Operation
              <ArrowRight className="w-5 h-5" />
            </button>
          </form>
        </motion.div>

        {/* Recent Activity */}
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="glass p-6 rounded-2xl border border-[#1e293b] flex flex-col h-full"
        >
          <h2 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
            <Clock className="w-5 h-5 text-[#7C5CFF]" />
            Recent Intel
          </h2>
          
          <div className="flex-1 overflow-y-auto pr-2 space-y-4">
            {loading ? (
              <div className="flex justify-center p-4"><Loader2 className="w-6 h-6 animate-spin text-[#9BA6C3]" /></div>
            ) : sessions.length === 0 ? (
              <p className="text-[#64748b] text-sm text-center">No recent operations.</p>
            ) : (
              sessions.slice(0, 5).map((s, i) => (
                <div key={i} className="group p-4 bg-[#0D1424] border border-[#1e293b] rounded-xl hover:border-[#00D4FF]/30 transition-colors cursor-pointer" onClick={() => router.push(`/report/${s.id}`)}>
                  <h4 className="text-sm font-medium text-white line-clamp-2 mb-2 group-hover:text-[#00D4FF] transition-colors">{s.query}</h4>
                  <div className="flex items-center justify-between text-xs text-[#64748b]">
                    <span>{new Date(s.created_at).toLocaleDateString()}</span>
                    {s.quality_score !== null && (
                      <span className="bg-[#14F195]/10 text-[#14F195] px-2 py-0.5 rounded-full font-medium">
                        {(s.quality_score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
          <button 
            onClick={() => router.push('/history')}
            className="w-full mt-4 text-sm text-[#00D4FF] hover:text-white transition-colors py-2 border border-[#00D4FF]/20 rounded-lg hover:bg-[#00D4FF]/10"
          >
            View All History
          </button>
        </motion.div>

      </div>
    </div>
  );
}
