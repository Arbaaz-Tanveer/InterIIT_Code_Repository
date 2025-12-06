import React, { useState, useEffect, useRef } from 'react';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight, RotateCw, RotateCcw, Gamepad2, Zap } from 'lucide-react';
import { robotService } from '../services/robotService';
import { RobotState } from '../types';
import { MapVisualizer } from './MapVisualizer';

interface ManualControlProps {
    state: RobotState;
}

export const ManualControl: React.FC<ManualControlProps> = ({ state }) => {
    const [speed, setSpeed] = useState(0.5); // m/s
    const [zHeight, setZHeight] = useState(0); // cm
    const [activeKeys, setActiveKeys] = useState<Set<string>>(new Set());
    const loopRef = useRef<number | null>(null);

    // Handle Keyboard Input
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            const key = e.key.toLowerCase();
            if (['w', 'a', 's', 'd', 'q', 'e'].includes(key)) {
                setActiveKeys(prev => {
                    const newSet = new Set(prev);
                    newSet.add(key);
                    return newSet;
                });
            }
        };

        const handleKeyUp = (e: KeyboardEvent) => {
            const key = e.key.toLowerCase();
            if (['w', 'a', 's', 'd', 'q', 'e'].includes(key)) {
                setActiveKeys(prev => {
                    const newSet = new Set(prev);
                    newSet.delete(key);
                    return newSet;
                });
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('keyup', handleKeyUp);

        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('keyup', handleKeyUp);
        };
    }, []);

    // Control Loop
    useEffect(() => {
        const updateVelocity = () => {
            let linearX = 0;
            let linearY = 0;
            let angular = 0;

            if (activeKeys.has('w')) linearX += speed;
            if (activeKeys.has('s')) linearX -= speed;
            if (activeKeys.has('a')) linearY += speed; // Left (Strafing)
            if (activeKeys.has('d')) linearY -= speed; // Right (Strafing)
            if (activeKeys.has('q')) angular += 1.0;   // Rotate Left (CCW)
            if (activeKeys.has('e')) angular -= 1.0;   // Rotate Right (CW)

            robotService.sendVelocityCommand(linearX, linearY, angular);
        };

        // Run loop only if keys are active or was just active (to stop)
        // Actually, we need to run it constantly to maintain state or just when keys change?
        // Better to run a loop when keys are active to allow smooth updates if we add acceleration later.
        // For now, simple state change trigger is enough? 
        // No, let's use an interval for smoother feel if we hold keys.

        if (activeKeys.size > 0) {
            if (!loopRef.current) {
                // Start loop
                updateVelocity(); // Run immediately once
                loopRef.current = window.setInterval(updateVelocity, 50);
            }
        } else {
            // Stop loop and send stop command
            if (loopRef.current) {
                clearInterval(loopRef.current);
                loopRef.current = null;
            }
            // Always send stop when keys are empty, just to be safe
            robotService.sendVelocityCommand(0, 0, 0);
        }

        return () => {
            if (loopRef.current) {
                clearInterval(loopRef.current);
                loopRef.current = null;
            }
        };
    }, [activeKeys, speed]);

    // Touch Handlers
    const handleTouchStart = (key: string) => {
        setActiveKeys(prev => {
            const newSet = new Set(prev);
            newSet.add(key);
            return newSet;
        });
    };

    const handleTouchEnd = (key: string) => {
        setActiveKeys(prev => {
            const newSet = new Set(prev);
            newSet.delete(key);
            return newSet;
        });
    };

    return (
        <div className="h-full flex flex-col lg:flex-row gap-6">
            {/* Left Panel: Controls */}
            <div className="flex-1 flex flex-col space-y-6">

                {/* Header */}
                <div className="bg-sci-panel p-6 rounded-xl border border-slate-700">
                    <div className="flex items-center space-x-3 mb-4">
                        <Gamepad2 className="text-sci-accent" size={24} />
                        <h2 className="text-2xl font-bold text-white">Manual Control</h2>
                    </div>
                    <p className="text-slate-400">
                        Use <span className="text-white font-mono bg-slate-800 px-1 rounded">WASD</span> to move and <span className="text-white font-mono bg-slate-800 px-1 rounded">Q/E</span> to rotate.
                        Or use the on-screen controls.
                    </p>
                </div>

                {/* Speed Control */}
                <div className="bg-sci-panel p-6 rounded-xl border border-slate-700 space-y-6">
                    {/* Movement Speed */}
                    <div>
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center space-x-2">
                                <Zap className="text-sci-warning" size={20} />
                                <h3 className="font-semibold text-white">Movement Speed</h3>
                            </div>
                            <span className="text-sci-accent font-mono">{speed.toFixed(1)} m/s</span>
                        </div>
                        <input
                            type="range"
                            min="0.1"
                            max="2.0"
                            step="0.1"
                            value={speed}
                            onChange={(e) => setSpeed(parseFloat(e.target.value))}
                            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-sci-accent"
                        />
                        <div className="flex justify-between text-xs text-slate-500 mt-2 font-mono">
                            <span>SLOW</span>
                            <span>FAST</span>
                        </div>
                    </div>

                    {/* Z-Scan Height */}
                    <div>
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center space-x-2">
                                <ArrowUp className="text-sci-success" size={20} />
                                <h3 className="font-semibold text-white">Camera Height (Z)</h3>
                            </div>
                            <div className="flex items-center space-x-2">
                                <input
                                    type="number"
                                    min="0"
                                    max="100"
                                    step="0.1"
                                    defaultValue={zHeight}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') {
                                            const val = parseFloat(e.currentTarget.value);
                                            setZHeight(val);
                                            robotService.sendZScanCommand(val);
                                        }
                                    }}
                                    onBlur={(e) => {
                                        const val = parseFloat(e.target.value);
                                        setZHeight(val);
                                        robotService.sendZScanCommand(val);
                                    }}
                                    className="w-20 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-white font-mono focus:outline-none focus:border-sci-accent text-right"
                                />
                                <span className="text-sci-accent font-mono">cm</span>
                            </div>
                        </div>
                        <input
                            type="range"
                            min="0"
                            max="100"
                            step="0.1"
                            value={zHeight}
                            onChange={(e) => {
                                const val = parseFloat(e.target.value);
                                setZHeight(val);
                                robotService.sendZScanCommand(val);
                            }}
                            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-sci-success"
                        />
                        <div className="flex justify-between text-xs text-slate-500 mt-2 font-mono">
                            <span>0 cm</span>
                            <span>100 cm</span>
                        </div>
                    </div>
                </div>

                {/* D-Pad Controls */}
                <div className="flex-1 bg-sci-panel p-6 rounded-xl border border-slate-700 flex items-center justify-center min-h-[300px]">
                    <div className="relative w-64 h-64">
                        {/* UP */}
                        <button
                            className={`absolute top-0 left-1/2 -translate-x-1/2 w-16 h-16 rounded-xl border-2 flex items-center justify-center transition-all ${activeKeys.has('w')
                                ? 'bg-sci-accent text-white border-sci-accent shadow-[0_0_20px_rgba(14,165,233,0.5)] scale-95'
                                : 'bg-slate-800 text-slate-400 border-slate-600 hover:border-sci-accent hover:text-white'
                                }`}
                            onMouseDown={() => handleTouchStart('w')}
                            onMouseUp={() => handleTouchEnd('w')}
                            onTouchStart={() => handleTouchStart('w')}
                            onTouchEnd={() => handleTouchEnd('w')}
                        >
                            <ArrowUp size={32} />
                        </button>

                        {/* DOWN */}
                        <button
                            className={`absolute bottom-0 left-1/2 -translate-x-1/2 w-16 h-16 rounded-xl border-2 flex items-center justify-center transition-all ${activeKeys.has('s')
                                ? 'bg-sci-accent text-white border-sci-accent shadow-[0_0_20px_rgba(14,165,233,0.5)] scale-95'
                                : 'bg-slate-800 text-slate-400 border-slate-600 hover:border-sci-accent hover:text-white'
                                }`}
                            onMouseDown={() => handleTouchStart('s')}
                            onMouseUp={() => handleTouchEnd('s')}
                            onTouchStart={() => handleTouchStart('s')}
                            onTouchEnd={() => handleTouchEnd('s')}
                        >
                            <ArrowDown size={32} />
                        </button>

                        {/* LEFT (Strafing) */}
                        <button
                            className={`absolute top-1/2 left-0 -translate-y-1/2 w-16 h-16 rounded-xl border-2 flex items-center justify-center transition-all ${activeKeys.has('a')
                                ? 'bg-sci-accent text-white border-sci-accent shadow-[0_0_20px_rgba(14,165,233,0.5)] scale-95'
                                : 'bg-slate-800 text-slate-400 border-slate-600 hover:border-sci-accent hover:text-white'
                                }`}
                            onMouseDown={() => handleTouchStart('a')}
                            onMouseUp={() => handleTouchEnd('a')}
                            onTouchStart={() => handleTouchStart('a')}
                            onTouchEnd={() => handleTouchEnd('a')}
                        >
                            <ArrowLeft size={32} />
                        </button>

                        {/* RIGHT (Strafing) */}
                        <button
                            className={`absolute top-1/2 right-0 -translate-y-1/2 w-16 h-16 rounded-xl border-2 flex items-center justify-center transition-all ${activeKeys.has('d')
                                ? 'bg-sci-accent text-white border-sci-accent shadow-[0_0_20px_rgba(14,165,233,0.5)] scale-95'
                                : 'bg-slate-800 text-slate-400 border-slate-600 hover:border-sci-accent hover:text-white'
                                }`}
                            onMouseDown={() => handleTouchStart('d')}
                            onMouseUp={() => handleTouchEnd('d')}
                            onTouchStart={() => handleTouchStart('d')}
                            onTouchEnd={() => handleTouchEnd('d')}
                        >
                            <ArrowRight size={32} />
                        </button>

                        {/* Center Decor */}
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-20 h-20 bg-slate-900 rounded-full border border-slate-700 flex items-center justify-center">
                            <div className="w-2 h-2 bg-sci-accent rounded-full animate-pulse" />
                        </div>
                    </div>
                </div>

                {/* Rotation Controls (Touch) */}
                <div className="flex justify-center space-x-8 pb-4">
                    <button
                        className={`w-16 h-16 rounded-full border-2 flex items-center justify-center transition-all ${activeKeys.has('q')
                            ? 'bg-sci-accent text-white border-sci-accent shadow-[0_0_20px_rgba(14,165,233,0.5)] scale-95'
                            : 'bg-slate-800 text-slate-400 border-slate-600 hover:border-sci-accent hover:text-white'
                            }`}
                        onMouseDown={() => handleTouchStart('q')}
                        onMouseUp={() => handleTouchEnd('q')}
                        onTouchStart={() => handleTouchStart('q')}
                        onTouchEnd={() => handleTouchEnd('q')}
                    >
                        <RotateCcw size={24} />
                    </button>
                    <div className="flex items-center text-slate-500 font-mono text-xs">ROTATION</div>
                    <button
                        className={`w-16 h-16 rounded-full border-2 flex items-center justify-center transition-all ${activeKeys.has('e')
                            ? 'bg-sci-accent text-white border-sci-accent shadow-[0_0_20px_rgba(14,165,233,0.5)] scale-95'
                            : 'bg-slate-800 text-slate-400 border-slate-600 hover:border-sci-accent hover:text-white'
                            }`}
                        onMouseDown={() => handleTouchStart('e')}
                        onMouseUp={() => handleTouchEnd('e')}
                        onTouchStart={() => handleTouchStart('e')}
                        onTouchEnd={() => handleTouchEnd('e')}
                    >
                        <RotateCw size={24} />
                    </button>
                </div>
            </div>

            {/* Right Panel: Mini Map */}
            <div className="flex-1 bg-sci-panel rounded-xl border border-slate-700 overflow-hidden flex flex-col">
                <div className="p-4 border-b border-slate-700 bg-slate-900/50">
                    <h3 className="font-semibold text-white">Live Position</h3>
                </div>
                <div className="flex-1 relative min-h-[400px]">
                    <MapVisualizer state={state} />
                </div>
            </div>
        </div>
    );
};
