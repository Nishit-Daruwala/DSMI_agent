"use client";

import { useEffect, useState, useMemo } from "react";
import { api } from "@/lib/api";
import { motion } from "framer-motion";
import { Search, SlidersHorizontal, ArrowRight, Loader2, Calendar } from "lucide-react";
import { useRouter } from "next/navigation";

interface SessionSummary {
  id: string;
  query: string;
  status: string;
  quality_score: number | null;
  created_at: string;
}

export default function HistoryPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState<"newest" | "oldest" | "quality">("newest");
  const router = useRouter();

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const data = await api.get("/sessions?limit=200");
        setSessions(data.sessions);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchSessions();
  }, []);

  const filteredAndSorted = useMemo(() => {
    let result = sessions;
    
    if (searchTerm) {
      const lower = searchTerm.toLowerCase();
      result = result.filter(s => s.query.toLowerCase().includes(lower));
    }

    result = [...result].sort((a, b) => {
      if (sortBy === "newest") {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      } else if (sortBy === "oldest") {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      } else if (sortBy === "quality") {
        return (b.quality_score || 0) - (a.quality_score || 0);
      }
      return 0;
    });

    return result;
  }, [sessions, searchTerm, sortBy]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">Research Library</h1>
        <p className="text-[#9BA6C3] mt-1">Browse, compare, and manage your past intelligence operations.</p>
      </div>

      <div className="glass p-4 rounded-xl flex flex-col sm:flex-row gap-4 border border-[rgba(255,255,255,0.05)]">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[#64748b]" />
          <input 
            type="text" 
            placeholder="Search by query keywords..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#0D1424] border border-[#1e293b] rounded-lg pl-10 pr-4 py-2.5 text-white placeholder-[#475569] focus:outline-none focus:border-[#00D4FF] focus:ring-1 focus:ring-[#00D4FF] transition-all"
          />
        </div>
        
        <div className="relative">
          <select 
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="appearance-none bg-[#0D1424] border border-[#1e293b] rounded-lg pl-10 pr-10 py-2.5 text-white focus:outline-none focus:border-[#00D4FF] focus:ring-1 focus:ring-[#00D4FF] transition-all"
          >
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="quality">Highest Quality</option>
          </select>
          <SlidersHorizontal className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748b]" />
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-[#00D4FF]" />
        </div>
      ) : filteredAndSorted.length === 0 ? (
        <div className="glass p-12 rounded-2xl text-center border border-[rgba(255,255,255,0.05)]">
          <p className="text-lg font-medium text-white mb-2">No intelligence found</p>
          <p className="text-[#9BA6C3]">Start a new operation from the dashboard to populate your library.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAndSorted.map((session, i) => (
            <motion.div 
              key={session.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.3 }}
              onClick={() => router.push(`/report/${session.id}`)}
              className="group glass p-6 rounded-2xl border border-[rgba(255,255,255,0.05)] hover:border-[#00D4FF]/40 cursor-pointer transition-all flex flex-col h-[200px]"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="bg-[#1e293b] text-[#cbd5e1] text-xs font-medium px-2.5 py-1 rounded-md">
                  {session.status.toUpperCase()}
                </div>
                {session.quality_score !== null && (
                  <div className={`text-xs font-bold px-2.5 py-1 rounded-md ${
                    session.quality_score >= 0.8 ? 'bg-[#14F195]/10 text-[#14F195]' :
                    session.quality_score >= 0.6 ? 'bg-yellow-500/10 text-yellow-500' :
                    'bg-red-500/10 text-red-500'
                  }`}>
                    Q-SCORE {(session.quality_score * 100).toFixed(0)}
                  </div>
                )}
              </div>
              
              <h3 className="text-white font-semibold text-base line-clamp-3 mb-auto group-hover:text-[#00D4FF] transition-colors leading-snug">
                {session.query}
              </h3>
              
              <div className="mt-4 pt-4 border-t border-[#1e293b] flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[#64748b] text-xs font-medium">
                  <Calendar className="w-3.5 h-3.5" />
                  {new Date(session.created_at).toLocaleDateString()}
                </div>
                <ArrowRight className="w-4 h-4 text-[#00D4FF] opacity-0 group-hover:opacity-100 transition-opacity -translate-x-2 group-hover:translate-x-0 transform duration-300" />
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
