"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FileUploader } from '@/components/layer1/FileUploader';

export default function LandingPage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  
  const handleStart = (e: React.FormEvent) => {
    e.preventDefault();
    // In a real app, this would POST the initial data/prompt to create a run ID
    // For this demo, we immediately route to the active pipeline
    router.push('/run/turing-active-run');
  };

  return (
    <main className="h-screen overflow-y-auto bg-[#F5F5F5] tab-pane-bg font-sans text-black selection:bg-orange-500 selection:text-white flex flex-col items-center py-20 px-10">
      
      {/* Header */}
      <div className="max-w-5xl w-full flex justify-between items-end border-b-4 border-black pb-6 mb-12 bg-white px-8 pt-8 brutal-box">
        <div>
          <h1 className="text-4xl font-bold tracking-tighter uppercase font-sans flex items-center gap-4">
            <div className="w-6 h-6 bg-orange-500 rounded-full animate-pulse" />
            Turing <span className="text-orange-500 ml-2">ENGINE</span>
          </h1>
          <p className="font-mono text-xs text-gray-500 mt-3 font-bold tracking-widest uppercase">
            Autonomous Causal Discovery & Cross-Domain Abstraction
          </p>
        </div>
        <div className="font-mono text-[10px] font-bold text-gray-400 text-right">
          SYSTEM STATUS: <span className="text-green-500">ONLINE</span><br/>
          ENGINE: V4_ALPHA
        </div>
      </div>

      <div className="max-w-5xl w-full grid grid-cols-3 gap-10">
        
        {/* Main Interface */}
        <div className="col-span-2 flex flex-col gap-8">
          
          {/* Explanation */}
          <div className="brutal-box p-8 bg-white border-2 border-black shadow-[8px_8px_0px_rgba(0,0,0,1)]">
            <h2 className="font-mono font-bold text-sm tracking-widest mb-4 uppercase text-black">System Objective</h2>
            <p className="text-sm leading-relaxed text-gray-700 font-sans">
              TURING is a next-generation AI pipeline that ingests your raw datasets, autonomously maps the causal topology, mathematically strips away domain-specific semantics, and scans external domains (e.g., biology, supply chain, physics) to find isomorphic structural solutions to your bottlenecks. It also performs dynamic system simulations to validate the proposed interventions.
            </p>
          </div>

          {/* New Run Form */}
          <div className="brutal-box p-8 bg-white border-2 border-black shadow-[8px_8px_0px_#FF4500]">
            <h2 className="font-mono font-bold text-sm tracking-widest mb-6 uppercase flex items-center gap-3">
              Initialize Discovery Pipeline
            </h2>
            
            <form onSubmit={handleStart} className="flex flex-col gap-6">
              
              {/* File Upload */}
              <div>
                <label className="block font-mono text-xs font-bold text-gray-500 mb-2 uppercase">Dataset / Timeseries Upload (CSV/XLSX)</label>
                <div className="w-full">
                  <FileUploader />
                </div>
              </div>

              {/* Text Prompt */}
              <div className="mt-4">
                <label className="block font-mono text-xs font-bold text-gray-500 mb-2 uppercase">Research Hypothesis / Objective</label>
                <textarea 
                  className="w-full border-2 border-black p-4 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 min-h-[120px] resize-y bg-gray-50 placeholder-gray-400"
                  placeholder="Describe the system bottleneck or optimization target..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  required
                />
              </div>

              {/* Submit */}
              <button 
                type="submit"
                className="mt-4 w-full bg-black text-white hover:bg-orange-500 hover:text-black transition-colors py-5 font-mono font-bold tracking-widest uppercase flex justify-center items-center gap-2 group border-2 border-black shadow-[4px_4px_0px_rgba(0,0,0,0.2)]"
              >
                Launch Pipeline 
                <span className="transform group-hover:translate-x-1 transition-transform">➔</span>
              </button>

            </form>
          </div>
        </div>

        {/* Sidebar: History */}
        <div className="col-span-1 flex flex-col gap-6">
          <div className="brutal-box p-6 bg-white border-2 border-black shadow-[4px_4px_0px_rgba(0,0,0,1)] h-full">
            <h2 className="font-mono font-bold text-xs tracking-widest mb-6 uppercase border-b-2 border-black pb-3">Research Logs</h2>
            
            <div className="flex flex-col gap-5">
              
              {/* Dynamically populated from backend in production */}
              <div className="text-left opacity-50 p-2 -ml-2">
                <div className="font-mono text-[10px] text-gray-400 font-bold mb-1">WAITING FOR INGESTION</div>
                <div className="font-bold font-sans text-sm text-black italic">No active runs</div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </main>
  );
}
