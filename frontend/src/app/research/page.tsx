"use client";

import { useEffect, useState, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { motion } from "framer-motion";
import { Terminal, StopCircle, CheckCircle2, Loader2, BrainCircuit, LineChart, Target, ShieldCheck, FileText } from "lucide-react";

export default function ResearchPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const query = searchParams.get("q");
  const loops = parseInt(searchParams.get("loops") || "3", 10);

  const [logs, setLogs] = useState<string[]>(["Initializing intelligence operations..."]);
  const [activeNode, setActiveNode] = useState<string>("pending");
  const [nodesCompleted, setNodesCompleted] = useState<string[]>([]);
  const [metricsCount, setMetricsCount] = useState(0);
  const [sourcesCount, setSourcesCount] = useState(0);
  const [iteration, setIteration] = useState(1);
  const [isDone, setIsDone] = useState(false);

  const logsEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const agentNodes = [
    { id: "planner", name: "Planner", icon: Target },
    { id: "researcher", name: "Researcher", icon: BrainCircuit },
    { id: "data_analyst", name: "Data Analyst", icon: LineChart },
    { id: "strategic_intelligence", name: "Strategic Intel", icon: BrainCircuit },
    { id: "critic", name: "Critic", icon: ShieldCheck },
    { id: "publisher", name: "Publisher", icon: FileText }
  ];

  useEffect(() => {
    if (!query) {
      router.push("/dashboard");
      return;
    }

    // Since EventSource doesn't support custom headers (like Authorization: Bearer...),
    // and we need JWT auth, we must fetch the SSE stream manually.
    const startStream = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/research/start", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${localStorage.getItem("dsmi_token")}`
          },
          body: JSON.stringify({ query, max_iterations: loops })
        });

        if (!response.body) throw new Error("No body in response");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value);
          const lines = chunk.split("\n");
          
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));
                handleSseData(data);
              } catch (e) {
                console.error("Error parsing SSE data", e, line);
              }
            }
          }
        }
      } catch (err: any) {
        setLogs(prev => [...prev, `[ERROR] Connection failed: ${err.message}`]);
      }
    };

    startStream();

    return () => {
      // Cleanup fetch reader is tricky, but unmounting will generally abort or we just ignore updates.
    };
  }, [query, loops, router]);

  const handleSseData = (data: any) => {
    if (data.node === "__error__") {
      setLogs(prev => [...prev, `[ERROR] ${data.detail}`]);
      return;
    }

    if (data.node === "__done__") {
      setIsDone(true);
      setLogs(prev => [...prev, `[SYSTEM] Research complete. Redirecting to report...`]);
      setTimeout(() => {
        if (data.session_id) {
          router.push(`/report/${data.session_id}`);
        } else {
          router.push("/history");
        }
      }, 2000);
      return;
    }

    // It's a node update
    const cleanNode = data.node.split("_agent")[0].toLowerCase(); // e.g., planner_agent -> planner
    setActiveNode(cleanNode);
    setNodesCompleted(prev => {
      // Determine what nodes came before this one and mark them complete
      const currentIndex = agentNodes.findIndex(n => n.id === cleanNode || cleanNode.includes(n.id));
      if (currentIndex === -1) return prev;
      
      const newCompleted = agentNodes.slice(0, currentIndex).map(n => n.id);
      return newCompleted;
    });

    if (data.metrics_count) setMetricsCount(data.metrics_count);
    if (data.sources_count) setSourcesCount(data.sources_count);
    if (data.iteration) setIteration(data.iteration);

    setLogs(prev => [...prev, `[${data.timestamp}] [${data.node}] ${data.status}`]);
  };

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (!query) return null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <span className="relative flex h-3 w-3 mr-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00D4FF] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-[#00D4FF]"></span>
            </span>
            Live Intelligence Operation
          </h1>
          <p className="text-[#9BA6C3] mt-1 text-sm">Target: <span className="text-white font-medium">{query}</span></p>
        </div>
        
        <button 
          onClick={() => router.push("/dashboard")}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20 rounded-lg transition-colors text-sm font-medium"
        >
          <StopCircle className="w-4 h-4" />
          Abort Operation
        </button>
      </div>

      {/* Metrics Bar */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass p-4 rounded-xl border border-[rgba(255,255,255,0.05)]">
          <p className="text-xs text-[#9BA6C3] uppercase tracking-wider font-semibold mb-1">Sources Collected</p>
          <p className="text-2xl font-bold text-white">{sourcesCount}</p>
        </div>
        <div className="glass p-4 rounded-xl border border-[rgba(255,255,255,0.05)]">
          <p className="text-xs text-[#9BA6C3] uppercase tracking-wider font-semibold mb-1">Data Points</p>
          <p className="text-2xl font-bold text-white">{metricsCount}</p>
        </div>
        <div className="glass p-4 rounded-xl border border-[rgba(255,255,255,0.05)]">
          <p className="text-xs text-[#9BA6C3] uppercase tracking-wider font-semibold mb-1">Loop / Phase</p>
          <p className="text-2xl font-bold text-white">{iteration} <span className="text-sm text-[#9BA6C3] font-normal">/ {loops}</span></p>
        </div>
      </div>

      {/* Workflow Visualization */}
      <div className="glass p-8 rounded-2xl border border-[rgba(255,255,255,0.05)] overflow-x-auto">
        <div className="min-w-[700px] flex items-center justify-between relative">
          {/* Connecting line */}
          <div className="absolute top-1/2 left-0 w-full h-1 bg-[#1e293b] -translate-y-1/2 z-0" />
          
          {agentNodes.map((node, i) => {
            // Fuzzy matching because langgraph might return planner_agent or planner
            const isCompleted = nodesCompleted.some(id => id.includes(node.id) || node.id.includes(id));
            const isActive = activeNode.includes(node.id) || node.id.includes(activeNode);
            
            let stateClass = "bg-[#0D1424] border-[#1e293b] text-[#64748b]";
            if (isCompleted) stateClass = "bg-[#14F195]/20 border-[#14F195] text-[#14F195]";
            if (isActive) stateClass = "bg-[#00D4FF]/20 border-[#00D4FF] text-[#00D4FF] shadow-[0_0_15px_rgba(0,212,255,0.5)]";

            return (
              <div key={node.id} className="relative z-10 flex flex-col items-center gap-3">
                <motion.div 
                  initial={false}
                  animate={isActive ? { scale: [1, 1.1, 1], transition: { repeat: Infinity, duration: 2 } } : {}}
                  className={`w-14 h-14 rounded-full border-2 flex items-center justify-center transition-colors ${stateClass}`}
                >
                  {isCompleted && !isActive ? (
                    <CheckCircle2 className="w-6 h-6" />
                  ) : isActive ? (
                    <Loader2 className="w-6 h-6 animate-spin" />
                  ) : (
                    <node.icon className="w-6 h-6" />
                  )}
                </motion.div>
                <div className={`text-sm font-semibold whitespace-nowrap ${isActive ? 'text-white' : 'text-[#9BA6C3]'}`}>
                  {node.name}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Terminal logs */}
      <div className="glass rounded-2xl border border-[rgba(255,255,255,0.05)] overflow-hidden flex flex-col h-[400px]">
        <div className="bg-[#0D1424] border-b border-[#1e293b] px-4 py-3 flex items-center gap-2">
          <Terminal className="w-4 h-4 text-[#9BA6C3]" />
          <span className="text-sm font-mono text-[#9BA6C3]">Operation Logs</span>
        </div>
        <div className="p-4 overflow-y-auto font-mono text-sm flex-1 bg-black/50">
          {logs.map((log, i) => (
            <div key={i} className="mb-2 text-[#cbd5e1] break-words">
              {log.includes("[ERROR]") ? (
                <span className="text-red-400">{log}</span>
              ) : log.includes("[SYSTEM]") ? (
                <span className="text-[#14F195]">{log}</span>
              ) : (
                <>
                  <span className="text-[#7C5CFF]">{log.split("] ")[0]}]</span>{" "}
                  <span className="text-[#00D4FF]">{log.split("] ")[1]?.split(" ")[0]}</span>{" "}
                  <span className="text-[#cbd5e1]">{log.split("] ").slice(1).join(" ").substring(log.split("] ")[1]?.split(" ")[0]?.length || 0)}</span>
                </>
              )}
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
}
