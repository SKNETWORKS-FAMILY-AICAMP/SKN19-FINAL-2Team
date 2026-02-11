"use client";

import { useRef, useEffect } from "react";

type Evaluation = {
    verdict: string;
    issue_type: string | null;
    severity: string | null;
    expected_output: string;
    suggestion: string;
    target_agent: string | null;
    affected_file: string | null;
};

interface TestPanelProps {
    evaluations: Evaluation[];
    logs: string[];
    onExport: (format: "csv" | "xlsx" | "md") => void;
}

export default function TestPanel({ evaluations, logs, onExport }: TestPanelProps) {
    const logsEndRef = useRef<HTMLDivElement>(null);

    // 로그가 추가될 때마다 자동 스크롤
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [logs]);

    const failCount = evaluations.filter(e => e.verdict === "FAIL").length;
    const warnCount = evaluations.filter(e => e.verdict === "WARNING").length;
    const passCount = evaluations.filter(e => e.verdict === "PASS").length;

    const getVerdictStyle = (verdict: string) => {
        switch (verdict) {
            case "FAIL": return "bg-red-50 border-red-200 text-red-800";
            case "WARNING": return "bg-yellow-50 border-yellow-200 text-yellow-800";
            case "PASS": return "bg-green-50 border-green-200 text-green-800";
            default: return "bg-gray-50 border-gray-200 text-gray-800";
        }
    };

    return (
        // [수정] 너비를 w-[50rem] 등으로 대폭 늘리고, 내부를 grid-cols-2로 나눔
        <div className="w-[50rem] border-l border-gray-100 bg-white flex flex-col">

            {/* Header Area */}
            <div className="flex border-b border-gray-100 bg-gray-50/50">
                <div className="flex-1 py-3 px-4 border-r border-gray-100 flex items-center justify-between">
                    <span className="text-sm font-bold text-gray-700">📺 실시간 로그 모니터</span>
                    <span className="text-[10px] bg-gray-200 text-gray-600 px-1.5 rounded">LIVE</span>
                </div>
                <div className="flex-1 py-3 px-4 flex items-center justify-between">
                    <span className="text-sm font-bold text-gray-700">📊 테스트 평가 결과</span>
                    <div className="flex gap-1 text-[10px] font-bold">
                        <span className="text-green-600">P:{passCount}</span>
                        <span className="text-red-500">F:{failCount}</span>
                    </div>
                </div>
            </div>

            {/* Content Area (Split View) */}
            <div className="flex-1 overflow-hidden flex divide-x divide-gray-100 h-full">

                {/* [Left Column] Live Logs */}
                <div className="flex-1 bg-[#1e1e1e] flex flex-col min-w-0">
                    <div className="flex-1 overflow-y-auto p-4 text-green-400 font-mono text-sm leading-relaxed custom-scrollbar">
                        {logs.length === 0 ? (
                            <div className="h-full flex items-center justify-center text-gray-500 italic text-sm">
                                대기 중...
                            </div>
                        ) : (
                            <div className="space-y-1.5">
                                {logs.map((log, i) => (
                                    <div key={i} className="break-all border-l-2 border-gray-600 pl-3 py-0.5 hover:bg-gray-800/50 transition-colors">
                                        <span className="opacity-50 select-none mr-2 text-xs">[{new Date().toLocaleTimeString().split(' ')[0]}]</span>
                                        {log}
                                    </div>
                                ))}
                                <div ref={logsEndRef} />
                            </div>
                        )}
                    </div>
                </div>

                {/* [Right Column] Evaluation Results */}
                <div className="flex-1 bg-gray-50/10 flex flex-col min-w-0">
                    {/* Summary Dashboard */}
                    <div className="flex gap-2 p-3 border-b border-gray-50">
                        <div className="flex-1 bg-white border border-gray-100 rounded p-2 text-center shadow-sm">
                            <div className="text-[10px] text-gray-400">PASS</div>
                            <div className="text-lg font-bold text-green-600 leading-none">{passCount}</div>
                        </div>
                        <div className="flex-1 bg-white border border-gray-100 rounded p-2 text-center shadow-sm">
                            <div className="text-[10px] text-gray-400">WARN</div>
                            <div className="text-lg font-bold text-yellow-600 leading-none">{warnCount}</div>
                        </div>
                        <div className="flex-1 bg-white border border-gray-100 rounded p-2 text-center shadow-sm">
                            <div className="text-[10px] text-gray-400">FAIL</div>
                            <div className="text-lg font-bold text-red-600 leading-none">{failCount}</div>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-3 space-y-3">
                        {evaluations.length === 0 ? (
                            <div className="h-full flex items-center justify-center text-gray-400 text-xs">
                                평가 결과 대기 중...
                            </div>
                        ) : (
                            evaluations.slice().reverse().map((e, i) => ( // 최신순
                                <div key={i} className={`p-3 rounded border ${getVerdictStyle(e.verdict)} shadow-sm bg-white`}>
                                    <div className="flex justify-between items-start mb-1.5">
                                        <span className="font-bold text-xs">{e.verdict}</span>
                                        {e.issue_type && (
                                            <span className="text-[9px] px-1 py-0.5 rounded border border-current opacity-70">
                                                {e.issue_type}
                                            </span>
                                        )}
                                    </div>

                                    <p className="text-xs font-medium mb-1.5 leading-snug">{e.suggestion}</p>

                                    {(e.target_agent || e.affected_file) && (
                                        <div className="text-[10px] opacity-60 pt-1.5 border-t border-current/10 truncate">
                                            {e.target_agent && <span className="mr-2">🎯 {e.target_agent}</span>}
                                            {e.affected_file && <span title={e.affected_file}>📂 {e.affected_file.split('/').pop()}</span>}
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>

            {/* Footer Actions */}
            <div className="p-3 border-t border-gray-100 bg-white flex items-center justify-between">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Reports</span>
                <div className="flex gap-2">
                    <button onClick={() => onExport("csv")} className="px-3 py-1.5 bg-white border border-gray-200 text-gray-600 rounded text-xs font-bold hover:bg-gray-50 hover:border-gray-300 transition">CSV</button>
                    <button onClick={() => onExport("xlsx")} className="px-3 py-1.5 bg-white border border-gray-200 text-gray-600 rounded text-xs font-bold hover:bg-gray-50 hover:border-gray-300 transition">Excel</button>
                    <button onClick={() => onExport("md")} className="px-3 py-1.5 bg-white border border-gray-200 text-gray-600 rounded text-xs font-bold hover:bg-gray-50 hover:border-gray-300 transition">Markdown</button>
                </div>
            </div>
        </div>
    );
}