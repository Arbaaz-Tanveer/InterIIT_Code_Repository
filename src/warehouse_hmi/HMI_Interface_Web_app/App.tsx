import React, { useState, useEffect } from 'react';
import { Activity, Battery, Wifi, Map as MapIcon, Database, Settings as SettingsIcon, LogOut, User, Command, Shield, Clock } from 'lucide-react';
import { loginWithGoogle, logoutUser } from './services/firebase';
import { robotService } from './services/robotService';
import { RobotState, RobotStatus, SettingsState } from './types';
import { Sidebar } from './components/Sidebar';
import { MapVisualizer } from './components/MapVisualizer';
import { SmartCommand } from './components/SmartCommand';
import { DataLog } from './components/DataLog';
import { Settings } from './components/Settings';
import { RosGuide } from './components/RosGuide';
import { ManualControl } from './components/ManualControl';
import { CommandLogger } from './components/CommandLogger';
import { MapGenerator } from './components/MapGenerator';
import { RACKS } from './constants';

// Default settings
const DEFAULT_SETTINGS: SettingsState = {
    mode: 'simulation',
    connection: {
        url: 'ws://localhost:9090',
        connected: false,
        lastPing: 0
    },
    topics: {
        position: '/robot_pose',
        battery: '/battery_state',
        command: '/cmdvel_manual',
        scan: '/scan_result',
        wifi: '/wifi_signal',
        autoScan: '/auto_scan',
        status: '/robot_status',
        zscan: '/zscan_manual',
        restart: '/restart',
        scanRack: '/scan_rack',
        restartLocalisation: '/restart_localisation',
        restartLocalisation: '/restart_localisation',
        scanData: '/scan_data',
        speak: '/speak'
    },
    updateRate: 20,
    debugMode: false,
    schedule: {
        enabled: false,
        intervalMinutes: 30,
        lastScanTime: 0,
        nextScanTime: 0,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
    },
    rackWaypoints: RACKS.map(r => ({ rackId: r.id, scanPosition: { ...r.position } })),
    startPosition: { x: -350, y: -250 },
    stopPosition: { x: 350, y: -250 }
};

function App() {
    const [activeTab, setActiveTab] = useState('dashboard');
    const [robotState, setRobotState] = useState<RobotState>({
        batteryLevel: 85,
        position: { x: 650, y: 500 },
        rotation: 0,
        velocity: 0,
        status: RobotStatus.IDLE,
        currentTask: null,
        wifiSignal: 90,
        autoMode: false
    });
    const [user, setUser] = useState<any>(null);
    const [settings, setSettings] = useState<SettingsState>(() => {
        const saved = localStorage.getItem('robot_settings');
        if (saved) {
            const parsed = JSON.parse(saved);

            // MIGRATION: Check for old coordinate system (positive X/Y for racks)
            // If detected, force reset of rackWaypoints to new defaults
            const currentWaypoints = parsed.rackWaypoints;
            const needsReset = currentWaypoints && currentWaypoints.length > 0 &&
                currentWaypoints[0].scanPosition.x > 0 && RACKS[0].position.x < 0;

            // Merge with default to ensure new fields exist
            return {
                ...DEFAULT_SETTINGS,
                ...parsed,
                schedule: {
                    ...DEFAULT_SETTINGS.schedule,
                    ...parsed.schedule,
                    enabled: false // Force disabled on startup as per user request
                },
                rackWaypoints: (needsReset || !parsed.rackWaypoints)
                    ? DEFAULT_SETTINGS.rackWaypoints
                    : parsed.rackWaypoints
            };
        }
        return DEFAULT_SETTINGS;
    });
    const [currentTime, setCurrentTime] = useState(new Date());

    useEffect(() => {
        // Subscribe to robot state updates
        const unsubscribe = robotService.subscribe(setRobotState);

        // Initialize service with current settings
        robotService.updateSettings(settings);

        // Clock timer
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);

        return () => {
            unsubscribe();
            clearInterval(timer);
        };
    }, []);

    const handleGoogleLogin = async () => {
        try {
            const user = await loginWithGoogle();
            setUser(user);
        } catch (error: any) {
            alert(`Login failed: ${error.message}`);
        }
    };

    const handleLogout = async () => {
        await logoutUser();
        setUser(null);
    };

    const handleSettingsChange = (newSettings: SettingsState) => {
        setSettings(newSettings);
        localStorage.setItem('robot_settings', JSON.stringify(newSettings));
        robotService.updateSettings(newSettings);
    };

    const handleMapClick = (point: { x: number; y: number }) => {
        robotService.sendCommand('GOTO', point);
    };

    // Localisation Modal State
    const [showLocModal, setShowLocModal] = useState(false);
    const [locParams, setLocParams] = useState({ x: 0, y: 0, theta: 0 });

    const handleLocSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        robotService.sendRestartLocalisationCommand(
            Number(locParams.x),
            Number(locParams.y),
            Number(locParams.theta)
        );
        setShowLocModal(false);
        // alert(`Localisation reset to X:${locParams.x}, Y:${locParams.y}, θ:${locParams.theta}`);
    };

    if (!user) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
                <div className="bg-sci-panel border border-slate-700 p-8 rounded-2xl max-w-md w-full text-center relative overflow-hidden group">
                    <div className="absolute inset-0 bg-gradient-to-br from-sci-accent/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                    <div className="relative z-10">
                        <img
                            src="/eternal-logo.png"
                            alt="Eternal Logo"
                            className="w-24 h-24 mx-auto mb-6 object-contain animate-pulse-slow drop-shadow-[0_0_15px_rgba(14,165,233,0.5)]"
                        />

                        <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Eternal</h1>
                        <p className="text-slate-400 mb-8">Advanced Robot Control System</p>

                        <button
                            onClick={handleGoogleLogin}
                            className="w-full bg-white text-slate-900 py-3 px-4 rounded-lg font-semibold hover:bg-slate-200 transition-all transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center space-x-2"
                        >
                            <img src="https://www.google.com/favicon.ico" alt="Google" className="w-5 h-5" />
                            <span>Sign in with Google</span>
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex h-screen bg-slate-950 text-slate-200 overflow-hidden font-sans selection:bg-sci-accent/30">
            <Sidebar activeTab={activeTab} onTabChange={setActiveTab} onLogout={handleLogout} />

            <main className="flex-1 overflow-auto relative">
                {/* Header */}
                <header className="bg-slate-900/50 backdrop-blur-md border-b border-slate-800 sticky top-0 z-20 px-8 py-4 flex justify-between items-center">
                    <div>
                        <h2 className="text-2xl font-bold text-white tracking-tight">
                            {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}
                        </h2>
                        <p className="text-slate-400 text-sm">
                            {activeTab === 'dashboard' ? 'Real-time monitoring & control' :
                                activeTab === 'map' ? 'Warehouse navigation & mapping' :
                                    activeTab === 'data' ? 'System logs & analytics' :
                                        activeTab === 'system' ? 'ROS Bridge & System Status' :
                                            'System configuration'}
                        </p>
                    </div>

                    <div className="flex items-center space-x-6">
                        {/* Real-time Clock */}
                        <div className="flex items-center space-x-2 text-slate-400 font-mono text-sm border-r border-slate-800 pr-6">
                            <Clock size={16} />
                            <span>
                                {currentTime.toLocaleTimeString('en-US', {
                                    timeZone: settings.schedule?.timezone || 'UTC',
                                    hour12: false
                                })}
                            </span>
                        </div>

                        <div className="flex items-center space-x-2 px-3 py-1.5 bg-slate-800 rounded-full border border-slate-700">
                            <div className={`w-2 h-2 rounded-full ${settings.mode === 'simulation' ? 'bg-slate-500' : (robotState.connected ? 'bg-sci-success animate-pulse' : 'bg-sci-danger')}`} />
                            <span className="text-xs font-medium text-slate-300">
                                {settings.mode === 'simulation' ? 'SIMULATION' : (robotState.connected ? 'ONLINE' : 'OFFLINE')}
                            </span>
                        </div>

                        <div className="flex items-center space-x-4 text-sm font-mono text-slate-400">
                            <div className="flex items-center space-x-2">
                                <Battery size={16} className={robotState.batteryLevel < 20 ? 'text-sci-warning' : 'text-sci-success'} />
                                <span>{Math.round(robotState.batteryLevel)}%</span>
                            </div>
                            <div className="flex items-center space-x-2">
                                <Wifi size={16} className="text-sci-accent" />
                                <span>{Math.round(robotState.wifiSignal)}%</span>
                            </div>
                        </div>

                        <div className="flex items-center space-x-3 pl-6 border-l border-slate-800">
                            <div className="group relative flex items-center space-x-3 cursor-pointer">
                                <div className="text-right hidden md:block opacity-0 group-hover:opacity-100 transition-opacity duration-300 absolute right-12 whitespace-nowrap bg-slate-900/90 px-3 py-1 rounded border border-slate-700">
                                    <div className="text-sm font-medium text-white">
                                        {user.displayName || 'User'}
                                    </div>
                                    <div className="text-xs text-slate-400">
                                        {user.email}
                                    </div>
                                </div>
                                <div className="w-8 h-8 bg-gradient-to-br from-sci-accent to-purple-600 rounded-full flex items-center justify-center text-white font-bold shadow-lg shadow-sci-accent/20 z-10">
                                    {user.email?.[0].toUpperCase()}
                                </div>
                            </div>

                            <button
                                onClick={handleLogout}
                                className="p-2 bg-sci-danger/10 text-sci-danger rounded-lg border border-sci-danger/20 hover:bg-sci-danger/20 transition-colors"
                                title="Sign Out"
                            >
                                <LogOut size={18} />
                            </button>
                        </div>
                    </div>
                </header>

                <div className="p-8">
                    {activeTab === 'dashboard' && (
                        <div className="h-[calc(100vh-8rem)] flex flex-col items-center justify-center relative overflow-hidden">
                            {/* Sci-Fi Background Elements */}
                            <div className="absolute inset-0 z-0 opacity-20 pointer-events-none">
                                <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-sci-accent/20 rounded-full blur-[100px] animate-pulse-slow"></div>
                                <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-[100px] animate-pulse-slow delay-1000"></div>
                                <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-10"></div>
                            </div>

                            {/* Central Rotating Logo */}
                            <div className="relative z-10 flex flex-col items-center mb-12 group">
                                <div className="relative w-64 h-64 flex items-center justify-center">
                                    {/* Outer Rings */}
                                    <div className="absolute inset-0 border-2 border-sci-accent/30 rounded-full animate-[spin_10s_linear_infinite]"></div>
                                    <div className="absolute inset-2 border border-purple-500/30 rounded-full animate-[spin_15s_linear_infinite_reverse]"></div>
                                    <div className="absolute inset-0 rounded-full bg-gradient-to-b from-sci-accent/5 to-transparent blur-md"></div>

                                    {/* The Logo */}
                                    <img
                                        src="/eternal-logo.png"
                                        alt="Eternal System"
                                        className="w-48 h-48 object-contain drop-shadow-[0_0_30px_rgba(14,165,233,0.6)] animate-[spin_20s_linear_infinite]"
                                    />
                                </div>
                                <h1 className="mt-8 text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-sci-accent to-purple-400 tracking-wider">
                                    ETERNAL
                                </h1>
                                <div className="mt-2 flex items-center space-x-2 text-sci-accent/60 font-mono text-sm tracking-[0.2em]">
                                    <Activity size={12} className="animate-pulse" />
                                    <span>SYSTEM ONLINE</span>
                                    <Activity size={12} className="animate-pulse" />
                                </div>
                            </div>

                            {/* Speak Message Display */}
                            <div className="z-10 w-full max-w-2xl text-center mb-12 min-h-[4rem]">
                                {robotState.latestSpeakMessage && (
                                    <div className="animate-fade-in-up">
                                        <p className="text-sci-accent text-sm font-mono mb-2 uppercase tracking-widest border-b border-sci-accent/20 inline-block px-4 pb-1">
                                            System Message
                                        </p>
                                        <p className="text-2xl text-white font-light leading-relaxed drop-shadow-md">
                                            "{robotState.latestSpeakMessage}"
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* Controls */}
                            <div className="z-10 flex items-center space-x-8">
                                <button
                                    onClick={() => robotService.sendCommand('START_AUTO_SCAN')}
                                    disabled={robotState.autoMode}
                                    className={`
                                        group relative px-8 py-4 bg-slate-900 border border-sci-accent/50 rounded-xl overflow-hidden transition-all duration-300
                                        ${robotState.autoMode ? 'opacity-50 cursor-not-allowed' : 'hover:border-sci-accent hover:shadow-[0_0_30px_rgba(14,165,233,0.3)] hover:-translate-y-1'}
                                    `}
                                >
                                    <div className="absolute inset-0 bg-sci-accent/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
                                    <div className="relative flex items-center space-x-3">
                                        <div className={`p-2 rounded-lg bg-sci-accent/20 text-sci-accent ${robotState.autoMode ? 'animate-pulse' : ''}`}>
                                            <MapIcon size={24} />
                                        </div>
                                        <div className="text-left">
                                            <div className="text-xs text-sci-accent/70 uppercase tracking-widest font-semibold">Initiate</div>
                                            <div className="text-xl font-bold text-white">AUTO SCAN</div>
                                        </div>
                                    </div>
                                </button>

                                <button
                                    onClick={() => robotService.sendCommand('STOP_AUTO_SCAN')}
                                    disabled={!robotState.autoMode}
                                    className={`
                                        group relative px-8 py-4 bg-slate-900 border border-red-500/50 rounded-xl overflow-hidden transition-all duration-300
                                        ${!robotState.autoMode ? 'opacity-50 cursor-not-allowed' : 'hover:border-red-500 hover:shadow-[0_0_30px_rgba(239,68,68,0.3)] hover:-translate-y-1'}
                                    `}
                                >
                                    <div className="absolute inset-0 bg-red-500/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
                                    <div className="relative flex items-center space-x-3">
                                        <div className="p-2 rounded-lg bg-red-500/20 text-red-500">
                                            <LogOut size={24} />
                                        </div>
                                        <div className="text-left">
                                            <div className="text-xs text-red-500/70 uppercase tracking-widest font-semibold">Terminate</div>
                                            <div className="text-xl font-bold text-white">STOP SCAN</div>
                                        </div>
                                    </div>
                                </button>
                            </div>

                            {/* Manual Override Hint */}
                            <div className="fixed bottom-8 text-slate-600 text-xs font-mono tracking-wider">
                                COMMAND CENTER v2.0 // CONNECTED: {settings.connection.url}
                            </div>
                        </div>
                    )}

                    {activeTab === 'map' && (
                        <div className="h-[calc(100vh-2rem)]">
                            <MapGenerator onPublish={() => { }} />
                        </div>
                    )}

                    {activeTab === 'data' && (
                        <div className="h-full">
                            <DataLog />
                        </div>
                    )}
                    {activeTab === 'scan-data' && (
                        <div className="h-full">
                            <DataLog />
                        </div>
                    )}

                    {activeTab === 'system' && (
                        <RosGuide />
                    )}

                    {activeTab === 'manual' && (
                        <ManualControl state={robotState} />
                    )}

                    {activeTab === 'settings' && (
                        <Settings
                            currentSettings={settings}
                            onSettingsChange={handleSettingsChange}
                        />
                    )}
                </div>
            </main>


            {/* Localisation Modal */}
            {
                showLocModal && (
                    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                        <div className="bg-sci-panel border border-slate-700 rounded-xl p-6 max-w-sm w-full shadow-2xl">
                            <h3 className="text-xl font-bold text-white mb-4 flex items-center">
                                <MapIcon className="mr-2 text-sci-accent" />
                                Restart Localisation
                            </h3>
                            <form onSubmit={handleLocSubmit} className="space-y-4">
                                <div>
                                    <label className="block text-sm text-slate-400 mb-1">X Coordinate</label>
                                    <input
                                        type="number"
                                        step="any"
                                        value={locParams.x}
                                        onChange={e => setLocParams({ ...locParams, x: parseFloat(e.target.value) })}
                                        className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white focus:border-sci-accent focus:outline-none"
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-slate-400 mb-1">Y Coordinate</label>
                                    <input
                                        type="number"
                                        step="any"
                                        value={locParams.y}
                                        onChange={e => setLocParams({ ...locParams, y: parseFloat(e.target.value) })}
                                        className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white focus:border-sci-accent focus:outline-none"
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-slate-400 mb-1">Theta (Orientation)</label>
                                    <input
                                        type="number"
                                        step="any"
                                        value={locParams.theta}
                                        onChange={e => setLocParams({ ...locParams, theta: parseFloat(e.target.value) })}
                                        className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white focus:border-sci-accent focus:outline-none"
                                        required
                                    />
                                </div>
                                <div className="flex space-x-3 pt-2">
                                    <button
                                        type="button"
                                        onClick={() => setShowLocModal(false)}
                                        className="flex-1 py-2 bg-slate-800 text-slate-300 rounded hover:bg-slate-700 transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        className="flex-1 py-2 bg-sci-accent text-slate-900 font-bold rounded hover:bg-sci-accent/90 transition-colors"
                                    >
                                        Send
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )
            }
        </div >
    );
}

export default App;
