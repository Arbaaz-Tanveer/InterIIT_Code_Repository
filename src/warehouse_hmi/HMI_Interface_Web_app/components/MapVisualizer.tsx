import React, { useState, useEffect } from 'react';
import { RobotState, Rack } from '../types';
import { WAREHOUSE_HEIGHT, WAREHOUSE_WIDTH } from '../constants';
import { robotService } from '../services/robotService';
import { mapService } from '../services/mapService';
import { Play, Square, Crosshair, Zap, Wifi } from 'lucide-react';

interface MapVisualizerProps {
    state: RobotState;
    onMapClick?: (point: { x: number; y: number }) => void;
    settings?: any; // Optional for now to avoid breaking other usages immediately, but ideally typed
}

export const MapVisualizer: React.FC<MapVisualizerProps> = ({ state, settings, onMapClick }) => {
    const [racks, setRacks] = useState<Rack[]>([]);
    const [scanPoints, setScanPoints] = useState<{ x: number, y: number }[]>([]);

    // Load racks and scan points from default map
    useEffect(() => {
        const loadDefaultMapData = async () => {
            const defaultMapId = mapService.getDefaultMapId();
            if (defaultMapId) {
                const maps = await mapService.getAllMaps();
                const defaultMap = maps.find(m => m.id === defaultMapId);
                if (defaultMap) {
                    if (defaultMap.racks) {
                        setRacks(defaultMap.racks);
                        console.log('✅ Loaded racks from default map:', defaultMap.name, defaultMap.racks.length);
                    }
                    if (defaultMap.scanPoints) {
                        setScanPoints(defaultMap.scanPoints);
                        console.log('✅ Loaded scan points from default map:', defaultMap.name, defaultMap.scanPoints.length);
                    }
                }
            }
        };
        loadDefaultMapData();
    }, []);

    // Coordinate Transformation Helpers
    // Internal: Center (0,0), Y-Up, Width 800, Height 600
    // Screen: Top-Left (0,0), Y-Down
    const toScreenX = (x: number) => ((x + WAREHOUSE_WIDTH / 2) / WAREHOUSE_WIDTH) * 100;
    const toScreenY = (y: number) => ((WAREHOUSE_HEIGHT / 2 - y) / WAREHOUSE_HEIGHT) * 100;

    // Width/Height percentage
    const toScreenW = (w: number) => (w / WAREHOUSE_WIDTH) * 100;
    const toScreenH = (h: number) => (h / WAREHOUSE_HEIGHT) * 100;

    const handleMapClick = (e: React.MouseEvent<HTMLDivElement>) => {
        if (!onMapClick) return;

        const rect = e.currentTarget.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const clickY = e.clientY - rect.top;

        // Convert screen pixels to percentage (0-1)
        const pctX = clickX / rect.width;
        const pctY = clickY / rect.height;

        // Convert percentage to Cartesian
        // x = (pctX * WIDTH) - WIDTH/2
        // y = HEIGHT/2 - (pctY * HEIGHT)
        const x = (pctX * WAREHOUSE_WIDTH) - (WAREHOUSE_WIDTH / 2);
        const y = (WAREHOUSE_HEIGHT / 2) - (pctY * WAREHOUSE_HEIGHT);

        onMapClick({ x, y });
    };

    const toggleAutoScan = () => {
        if (state.autoMode) {
            robotService.sendCommand('STOP_AUTO_SCAN');
        } else {
            robotService.sendCommand('START_AUTO_SCAN');
        }
    };

    return (
        <div className="relative rounded-xl overflow-hidden border border-slate-600 shadow-2xl bg-[#0f172a]">
            {/* Control Bar Overlay */}
            <div className="absolute top-4 left-4 z-30 flex space-x-2">
                <button
                    onClick={toggleAutoScan}
                    className={`flex items-center space-x-2 px-4 py-2 rounded font-medium transition-colors border ${state.autoMode
                        ? 'bg-sci-warning/20 border-sci-warning text-sci-warning hover:bg-sci-warning/30'
                        : 'bg-sci-accent/20 border-sci-accent text-sci-accent hover:bg-sci-accent/30'
                        }`}
                >
                    {state.autoMode ? (
                        <>
                            <Square size={16} fill="currentColor" />
                            <span>Stop Auto Scan</span>
                        </>
                    ) : (
                        <>
                            <Play size={16} fill="currentColor" />
                            <span>Start Auto Scan</span>
                        </>
                    )}
                </button>
            </div>

            <div
                className="relative cursor-crosshair overflow-hidden"
                style={{
                    width: '100%',
                    height: '100%',
                    minHeight: '500px',
                    aspectRatio: `${WAREHOUSE_WIDTH}/${WAREHOUSE_HEIGHT}`,
                    // Grid Background
                    backgroundImage: `
                        linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px),
                        linear-gradient(rgba(255, 255, 255, 0.1) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px)
                    `,
                    backgroundSize: '20px 20px, 20px 20px, 100px 100px, 100px 100px',
                    backgroundPosition: 'center center'
                }}
                onClick={handleMapClick}
            >
                {/* Center Axes */}
                <div className="absolute top-0 bottom-0 left-1/2 w-px bg-white/20 pointer-events-none" />
                <div className="absolute left-0 right-0 top-1/2 h-px bg-white/20 pointer-events-none" />

                {/* Grid Labels (Every 100 units) */}
                {/* X Axis Labels */}
                {[-300, -200, -100, 100, 200, 300].map(x => (
                    <div key={`x-${x}`} className="absolute top-1/2 mt-1 text-[10px] text-slate-500 font-mono -translate-x-1/2 pointer-events-none" style={{ left: `${toScreenX(x)}%` }}>
                        {x}
                    </div>
                ))}
                {/* Y Axis Labels */}
                {[-200, -100, 100, 200].map(y => (
                    <div key={`y-${y}`} className="absolute left-1/2 ml-1 text-[10px] text-slate-500 font-mono -translate-y-1/2 pointer-events-none" style={{ top: `${toScreenY(y)}%` }}>
                        {y}
                    </div>
                ))}
                {/* Origin Label */}
                <div className="absolute top-1/2 left-1/2 mt-1 ml-1 text-[10px] text-white/50 font-mono pointer-events-none">0,0</div>
                <div className="absolute bottom-2 right-2 text-[10px] text-slate-500 font-mono pointer-events-none">Grid Unit: cm</div>

                {/* Racks from Default Map */}
                {racks.map((rack) => (
                    <div
                        key={rack.id}
                        className="absolute bg-slate-700 border border-slate-500 flex items-center justify-center text-xs text-slate-300 font-mono shadow-lg"
                        style={{
                            left: `${toScreenX(rack.position.x)}%`,
                            top: `${toScreenY(rack.position.y)}%`,
                            width: `${toScreenW(rack.width)}%`,
                            height: `${toScreenH(rack.height)}%`,
                            transform: 'translate(-50%, -50%)'
                        }}
                    >
                        <div className="text-center">
                            <div className="font-bold text-sci-accent">{rack.label}</div>
                            <div className="text-[10px] opacity-50">{rack.id}</div>
                        </div>
                    </div>
                ))}

                {/* Start Position (First Scan Point) */}
                {scanPoints.length > 0 && (
                    <div
                        className="absolute w-6 h-6 bg-green-500/50 border border-green-400 rounded-full flex items-center justify-center text-[10px] text-white font-bold shadow-[0_0_10px_rgba(34,197,94,0.5)] z-10"
                        style={{
                            left: `${toScreenX(scanPoints[0].x)}%`,
                            top: `${toScreenY(scanPoints[0].y)}%`,
                            transform: 'translate(-50%, -50%)'
                        }}
                    >
                        S
                    </div>
                )}

                {/* Stop Position (Last Scan Point) */}
                {scanPoints.length > 0 && (
                    <div
                        className="absolute w-6 h-6 bg-red-500/50 border border-red-400 rounded-full flex items-center justify-center text-[10px] text-white font-bold shadow-[0_0_10px_rgba(239,68,68,0.5)] z-10"
                        style={{
                            left: `${toScreenX(scanPoints[scanPoints.length - 1].x)}%`,
                            top: `${toScreenY(scanPoints[scanPoints.length - 1].y)}%`,
                            transform: 'translate(-50%, -50%)'
                        }}
                    >
                        E
                    </div>
                )}

                {/* Waypoint Marker (Target) */}
                {state.status === 'MOVING' && state.status !== 'IDLE' && ( // Check logic
                    // Actually state.target is not in state, it's private in service. 
                    // But we might want to visualize it if we had it. 
                    // The original code used a hardcoded ping? No, it used state.position?
                    // Ah, original code: {state.status === 'MOVING' && ( ... position ... )}
                    // That was putting a ping AT THE ROBOT? No, that's weird.
                    // Let's just keep the robot.
                    null
                )}

                {/* Robot Entity */}
                <div
                    className="absolute w-12 h-12 transition-all duration-75 ease-linear z-20"
                    style={{
                        left: `${toScreenX(state.position.x)}%`,
                        top: `${toScreenY(state.position.y)}%`,
                        transform: `translate(-50%, -50%) rotate(${-state.rotation}deg)` // Rotate negative because Y-axis flip flips rotation direction?
                        // Standard Angle: CCW is positive.
                        // Screen Angle: CW is positive (usually).
                        // If we have 90 deg (Up) in Cartesian.
                        // Screen: Up is -90? Or 270?
                        // CSS rotate(90deg) is CW (Right -> Down).
                        // We want 90 deg (Up).
                        // If rotation is 0 (Right). CSS rotate(0) is Right.
                        // If rotation is 90 (Up). CSS rotate(-90) is Up.
                        // So yes, negate rotation.
                    }}
                >
                    {/* Robot Body */}
                    <div className={`w-full h-full rounded-full border-2 flex items-center justify-center relative shadow-[0_0_20px_rgba(14,165,233,0.4)] ${state.status === 'ERROR' ? 'bg-sci-danger/20 border-sci-danger' : 'bg-sci-accent/20 border-sci-accent'
                        }`}>
                        {/* Direction Indicator */}
                        <div className="absolute right-0 w-2 h-2 bg-white rounded-full translate-x-1/2" />
                        <div className="w-6 h-6 bg-current rounded-sm opacity-50" />
                    </div>

                    {/* Scanning Beam Effect */}
                    {state.status === 'SCANNING' && (
                        <div className="absolute top-1/2 left-1/2 w-32 h-32 -translate-y-1/2 bg-sci-success/20 rounded-full animate-pulse blur-xl pointer-events-none" />
                    )}
                </div>

                {/* Overlay Info */}
                <div className="absolute bottom-4 left-4 bg-black/70 backdrop-blur px-3 py-1 rounded border border-slate-700 text-xs font-mono text-slate-300 pointer-events-none flex items-center space-x-4">
                    <div>
                        POS: X:{state.position.x.toFixed(0)} Y:{state.position.y.toFixed(0)} <br />
                        HDG: {state.rotation.toFixed(1)}°
                    </div>
                    <div className="h-6 w-px bg-slate-600"></div>
                    <div className="flex items-center space-x-2">
                        <Wifi size={14} className={state.wifiSignal > 50 ? "text-green-400" : "text-red-400"} />
                        <span>{Math.round(state.wifiSignal)}%</span>
                    </div>
                    <div className="flex items-center space-x-2">
                        <Zap size={14} className={state.batteryLevel > 20 ? "text-yellow-400" : "text-red-400"} />
                        <span>{Math.round(state.batteryLevel)}%</span>
                    </div>
                </div>

                <div className="absolute top-4 right-4 bg-black/70 backdrop-blur px-3 py-1 rounded border border-slate-700 text-xs font-mono text-slate-300 pointer-events-none flex items-center space-x-2">
                    <Crosshair size={12} />
                    <span>CLICK TO NAVIGATE</span>
                </div>
            </div>
        </div>
    );
};
