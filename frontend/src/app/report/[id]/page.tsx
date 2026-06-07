"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Download, Loader2, Target, BarChart2, Zap, BookOpen, FileText } from "lucide-react";
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

const COLORS = ['#00D4FF', '#7C5CFF', '#14F195', '#F59E0B', '#EF4444'];

export default function ReportPage() {
  const { id } = useParams();
  const router = useRouter();
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("executive");

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const data = await api.get(`/sessions/${id}`);
        setReport(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    if (id) fetchReport();
  }, [id]);

  const handleDownload = async (type: "pdf" | "md") => {
    try {
      const endpoint = `/sessions/${id}/${type}`;
      // Need a direct fetch to handle blobs
      const res = await fetch(`http://localhost:8000/api${endpoint}`, {
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("dsmi_token")}`
        }
      });
      if (!res.ok) throw new Error("Download failed");
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `DSMI_Report_${(id as string).substring(0,8)}.${type}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      console.error(err);
      alert("Download failed.");
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-[60vh]">
        <Loader2 className="w-10 h-10 animate-spin text-[#00D4FF]" />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="glass p-12 rounded-2xl text-center">
        <p className="text-xl text-white">Report not found.</p>
        <button onClick={() => router.push("/history")} className="mt-4 text-[#00D4FF] underline">Return to History</button>
      </div>
    );
  }

  const tabs = [
    { id: "executive", name: "Executive Summary", icon: Target },
    { id: "data", name: "Data & Charts", icon: BarChart2 },
    { id: "swot", name: "SWOT Analysis", icon: Zap },
    { id: "sources", name: "Sources", icon: BookOpen },
    { id: "full", name: "Full Document", icon: FileText },
  ];

  // Parse charts safely
  let chartsData: any[] = [];
  try {
    if (typeof report.charts_data === "string") {
      chartsData = JSON.parse(report.charts_data);
    } else if (Array.isArray(report.charts_data)) {
      chartsData = report.charts_data;
    }
  } catch(e) {}

  return (
    <div className="space-y-6 pb-20">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 glass p-6 rounded-2xl border border-[rgba(255,255,255,0.05)]">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white mb-2">{report.title}</h1>
          <div className="flex flex-wrap items-center gap-4 text-sm text-[#9BA6C3]">
            <span className="bg-[#1e293b] px-2.5 py-1 rounded-md">ID: {(id as string).substring(0,8)}</span>
            <span>Created: {new Date(report.created_at).toLocaleString()}</span>
            {report.quality_score !== null && (
              <span className={`px-2.5 py-1 rounded-md font-bold text-xs ${
                report.quality_score >= 0.8 ? 'bg-[#14F195]/10 text-[#14F195]' :
                report.quality_score >= 0.6 ? 'bg-yellow-500/10 text-yellow-500' :
                'bg-red-500/10 text-red-500'
              }`}>
                Q-SCORE: {(report.quality_score * 100).toFixed(0)}
              </span>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-3 shrink-0">
          <button 
            onClick={() => handleDownload("md")}
            className="flex items-center gap-2 px-4 py-2 bg-[#1e293b] text-white rounded-lg hover:bg-[#334155] transition-colors text-sm font-medium border border-[rgba(255,255,255,0.1)]"
          >
            <Download className="w-4 h-4" /> Markdown
          </button>
          <button 
            onClick={() => handleDownload("pdf")}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#00D4FF] to-[#3b82f6] text-black rounded-lg hover:opacity-90 transition-opacity text-sm font-bold"
          >
            <Download className="w-4 h-4" /> PDF Report
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex overflow-x-auto gap-2 pb-2 border-b border-[#1e293b] scrollbar-hide">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-3 rounded-t-lg font-medium text-sm transition-colors whitespace-nowrap ${
                isActive 
                  ? "bg-[#0D1424] text-[#00D4FF] border-t border-l border-r border-[#1e293b]" 
                  : "text-[#9BA6C3] hover:text-white hover:bg-[rgba(255,255,255,0.05)]"
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.name}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="bg-[#0D1424] rounded-b-2xl rounded-tr-2xl border border-[#1e293b] p-6 md:p-8 min-h-[500px]">
        
        {activeTab === "executive" && (
          <div className="prose prose-invert prose-cyan max-w-none">
            {report.executive_summary ? (
              <div dangerouslySetInnerHTML={{ __html: report.executive_summary.replace(/\n/g, '<br/>') }} />
            ) : (
              <p className="text-[#9BA6C3]">No executive summary generated.</p>
            )}
          </div>
        )}

        {activeTab === "data" && (
          <div className="space-y-12">
            {/* Metrics Grid */}
            {report.metrics && report.metrics.length > 0 && (
              <div>
                <h3 className="text-lg font-bold text-white mb-6 border-b border-[#1e293b] pb-2">Quantitative Findings</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                  {report.metrics.map((m: any, i: number) => (
                    <div key={i} className="bg-[#131C31] p-5 rounded-xl border border-[rgba(255,255,255,0.05)]">
                      <p className="text-xs text-[#9BA6C3] font-medium mb-1 line-clamp-1" title={m.name}>{m.name}</p>
                      <p className="text-2xl font-bold text-[#00D4FF]">{m.value}</p>
                      <div className="mt-2 flex justify-between items-center text-[10px] text-[#64748b]">
                        <span>Year: {m.year || "N/A"}</span>
                        <span>Conf: {m.confidence}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Charts using Recharts */}
            {chartsData.length > 0 && (
              <div>
                <h3 className="text-lg font-bold text-white mb-6 border-b border-[#1e293b] pb-2">Visualizations</h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {chartsData.map((chart, i) => (
                    <div key={i} className="bg-[#131C31] p-6 rounded-xl border border-[rgba(255,255,255,0.05)]">
                      <h4 className="text-base font-medium text-white mb-6 text-center">{chart.title || `Chart ${i+1}`}</h4>
                      <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          {chart.type === "bar" ? (
                            <BarChart data={chart.data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                              <XAxis dataKey={Object.keys(chart.data[0])[0]} stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                              <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                              <RechartsTooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ backgroundColor: '#0D1424', borderColor: '#1e293b', borderRadius: '8px' }} />
                              <Bar dataKey={Object.keys(chart.data[0])[1]} fill="#00D4FF" radius={[4, 4, 0, 0]} />
                            </BarChart>
                          ) : chart.type === "line" ? (
                            <LineChart data={chart.data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                              <XAxis dataKey={Object.keys(chart.data[0])[0]} stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                              <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                              <RechartsTooltip contentStyle={{ backgroundColor: '#0D1424', borderColor: '#1e293b', borderRadius: '8px' }} />
                              <Line type="monotone" dataKey={Object.keys(chart.data[0])[1]} stroke="#7C5CFF" strokeWidth={3} dot={{ r: 4, fill: "#7C5CFF" }} activeDot={{ r: 6 }} />
                            </LineChart>
                          ) : chart.type === "pie" ? (
                            <PieChart>
                              <Pie data={chart.data} dataKey={Object.keys(chart.data[0])[1]} nameKey={Object.keys(chart.data[0])[0]} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={5}>
                                {chart.data.map((_: any, index: number) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                              </Pie>
                              <RechartsTooltip contentStyle={{ backgroundColor: '#0D1424', borderColor: '#1e293b', borderRadius: '8px' }} />
                            </PieChart>
                          ) : (
                            <div className="flex items-center justify-center h-full text-[#64748b]">Unsupported chart type: {chart.type}</div>
                          )}
                        </ResponsiveContainer>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "swot" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-[rgba(20,241,149,0.05)] border border-[#14F195]/20 p-6 rounded-xl">
              <h3 className="text-[#14F195] font-bold mb-4 flex items-center gap-2">💪 STRENGTHS</h3>
              <ul className="space-y-2">
                {report.swot_analysis?.strengths?.map((s: string, i: number) => (
                  <li key={i} className="text-[#cbd5e1] text-sm flex gap-2">
                    <span className="text-[#14F195]">•</span> <span>{s}</span>
                  </li>
                )) || <p className="text-[#64748b] text-sm">No data available.</p>}
              </ul>
            </div>
            
            <div className="bg-[rgba(239,68,68,0.05)] border border-[#EF4444]/20 p-6 rounded-xl">
              <h3 className="text-[#EF4444] font-bold mb-4 flex items-center gap-2">⚠️ WEAKNESSES</h3>
              <ul className="space-y-2">
                {report.swot_analysis?.weaknesses?.map((s: string, i: number) => (
                  <li key={i} className="text-[#cbd5e1] text-sm flex gap-2">
                    <span className="text-[#EF4444]">•</span> <span>{s}</span>
                  </li>
                )) || <p className="text-[#64748b] text-sm">No data available.</p>}
              </ul>
            </div>

            <div className="bg-[rgba(0,212,255,0.05)] border border-[#00D4FF]/20 p-6 rounded-xl">
              <h3 className="text-[#00D4FF] font-bold mb-4 flex items-center gap-2">🚀 OPPORTUNITIES</h3>
              <ul className="space-y-2">
                {report.swot_analysis?.opportunities?.map((s: string, i: number) => (
                  <li key={i} className="text-[#cbd5e1] text-sm flex gap-2">
                    <span className="text-[#00D4FF]">•</span> <span>{s}</span>
                  </li>
                )) || <p className="text-[#64748b] text-sm">No data available.</p>}
              </ul>
            </div>

            <div className="bg-[rgba(245,158,11,0.05)] border border-[#F59E0B]/20 p-6 rounded-xl">
              <h3 className="text-[#F59E0B] font-bold mb-4 flex items-center gap-2">🔥 THREATS</h3>
              <ul className="space-y-2">
                {report.swot_analysis?.threats?.map((s: string, i: number) => (
                  <li key={i} className="text-[#cbd5e1] text-sm flex gap-2">
                    <span className="text-[#F59E0B]">•</span> <span>{s}</span>
                  </li>
                )) || <p className="text-[#64748b] text-sm">No data available.</p>}
              </ul>
            </div>
          </div>
        )}

        {activeTab === "sources" && (
          <div className="space-y-4">
            {report.sources?.map((src: any, i: number) => (
              <div key={i} className="bg-[#131C31] p-5 rounded-xl border border-[rgba(255,255,255,0.05)]">
                <a href={src.url} target="_blank" rel="noopener noreferrer" className="text-[#00D4FF] font-medium hover:underline text-lg">
                  {i+1}. {src.title || "Unknown Source"}
                </a>
                {src.snippet && (
                  <p className="text-[#9BA6C3] text-sm mt-3 border-l-2 border-[#1e293b] pl-4 italic">
                    "{src.snippet}"
                  </p>
                )}
                <div className="mt-3 flex items-center gap-4 text-xs text-[#64748b] font-mono break-all">
                  <span>{src.url}</span>
                </div>
              </div>
            )) || <p className="text-[#9BA6C3]">No sources recorded.</p>}
          </div>
        )}

        {activeTab === "full" && (
          <div className="prose prose-invert prose-cyan max-w-none prose-pre:bg-[#131C31] prose-pre:border prose-pre:border-[#1e293b] prose-headings:text-white prose-a:text-[#00D4FF]">
            {/* Very simple markdown renderer using dangerouslySetInnerHTML. 
                In a real production app, use react-markdown. */}
            <div dangerouslySetInnerHTML={{ __html: report.final_report.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br/>').replace(/^# (.*$)/gim, '<h1>$1</h1>').replace(/^## (.*$)/gim, '<h2>$1</h2>').replace(/^### (.*$)/gim, '<h3>$1</h3>').replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>') }} />
          </div>
        )}

      </div>
    </div>
  );
}
