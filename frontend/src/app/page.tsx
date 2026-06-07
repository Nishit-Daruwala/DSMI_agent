"use client";

import { motion } from "framer-motion";
import { ArrowRight, BrainCircuit, LineChart, ShieldCheck } from "lucide-react";
import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 text-center">
      
      {/* Top Nav (simplified for landing) */}
      <nav className="absolute top-0 w-full p-6 flex justify-between items-center max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <BrainCircuit className="w-8 h-8 text-[#00D4FF]" />
          <span className="font-bold text-xl tracking-tight text-white">DSMI Agent</span>
        </div>
        <Link 
          href="/login" 
          className="px-6 py-2 rounded-full border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] transition-colors backdrop-blur-md font-medium"
        >
          Login
        </Link>
      </nav>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="max-w-4xl mt-20"
      >
        <div className="inline-block px-4 py-1.5 rounded-full border border-[#00D4FF]/30 bg-[#00D4FF]/10 text-[#00D4FF] font-medium text-sm mb-8 backdrop-blur-md">
          Deep Strategic Market Intelligence v2.0
        </div>
        
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-b from-white to-white/60">
          The institutional-grade <br /> AI research operating system.
        </h1>
        
        <p className="text-xl text-[#9BA6C3] mb-12 max-w-2xl mx-auto leading-relaxed">
          Uncover deep market insights, generate strategic scenarios, and produce executive-ready intelligence with our multi-agent architecture.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link href="/login">
            <button className="flex items-center gap-2 bg-gradient-to-r from-[#00D4FF] to-[#3b82f6] text-black font-semibold px-8 py-4 rounded-xl hover:opacity-90 transition-opacity">
              Start Researching
              <ArrowRight className="w-5 h-5" />
            </button>
          </Link>
          <button className="flex items-center gap-2 border border-[#1e293b] bg-[#131C31]/50 backdrop-blur-md text-white font-medium px-8 py-4 rounded-xl hover:bg-[#131C31] transition-colors">
            View Capabilities
          </button>
        </div>
      </motion.div>

      {/* Feature grid */}
      <motion.div 
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.2 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-24 max-w-5xl w-full"
      >
        {[
          { icon: BrainCircuit, title: "Multi-Agent Orchestration", desc: "Planner, Researcher, Analyst, Critic, and Publisher working in tandem." },
          { icon: LineChart, title: "Strategic Scenarios", desc: "Automated Bull, Base, and Bear case modeling with quantitative driver analysis." },
          { icon: ShieldCheck, title: "Contrarian Intelligence", desc: "Automated debate and critique loops to eliminate bias and ensure robust findings." },
        ].map((feature, i) => (
          <div key={i} className="glass p-8 rounded-2xl text-left border border-[rgba(255,255,255,0.05)] hover:border-[#00D4FF]/30 transition-colors">
            <feature.icon className="w-10 h-10 text-[#00D4FF] mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">{feature.title}</h3>
            <p className="text-[#9BA6C3] text-sm leading-relaxed">{feature.desc}</p>
          </div>
        ))}
      </motion.div>
    </div>
  );
}
