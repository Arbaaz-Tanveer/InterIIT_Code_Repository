import React, { useRef, useEffect } from 'react';
import { Terminal, ArrowUpRight, ArrowDownLeft, Clock } from 'lucide-react';
import { CommandLogEntry } from '../types';

interface CommandLoggerProps {
    logs: CommandLogEntry[];
}

export const CommandLogger: React.FC<CommandLoggerProps> = ({ logs }) => {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <div className="bg-sci-panel border border-slate-700 rounded-xl p-4 h-[300px] flex flex-col">
            <h3 className="font-semibold text-white mb-4 flex items-center">
                <Terminal size={18} className="mr-2 text-sci-accent" />
                Command Log
            </h3>

            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto space-y-2 pr-2 font-mono text-xs"
            >
                {logs.length === 0 ? (
                    <div className="text-slate-500 text-center py-8 italic">
                        No commands logged yet
                    </div>
                ) : (
                    logs.map((log) => (
                        <div
                            key={log.id}
                            className={`p-2 rounded border ${log.direction === 'OUT'
                                    ? 'bg-slate-800/50 border-slate-700'
                                    : 'bg-sci-accent/10 border-sci-accent/20'
                                }`}
                        >
                            <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center space-x-2">
                                    {log.direction === 'OUT' ? (
                                        <ArrowUpRight size={12} className="text-sci-warning" />
                                    ) : (
                                        <ArrowDownLeft size={12} className="text-sci-success" />
                                    )}
                                    <span className={`font-bold ${log.direction === 'OUT' ? 'text-sci-warning' : 'text-sci-success'
                                        }`}>
                                        {log.command}
                                    </span>
                                </div>
                                <div className="flex items-center text-slate-500">
                                    <Clock size={10} className="mr-1" />
                                    <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                                </div>
                            </div>

                            {log.payload && (
                                <div className="mt-1 pl-5 text-slate-400 break-all">
                                    {typeof log.payload === 'object'
                                        ? JSON.stringify(log.payload)
                                        : String(log.payload)}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};
