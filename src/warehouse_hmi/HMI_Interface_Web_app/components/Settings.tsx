import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Wifi, WifiOff, Save, RotateCcw, ChevronDown, ChevronUp, Clock, MapPin, Calendar } from 'lucide-react';
import { SettingsState, RobotMode, RackWaypoint } from '../types';
import { RACKS } from '../constants';

const DEFAULT_SETTINGS: SettingsState = {
    mode: 'simulation',
    connection: {
        url: 'ws://localhost:9090',
        connected: false
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
        restartLocalisation: '/restart_localisation'
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

interface SettingsProps {
    onSettingsChange: (settings: SettingsState) => void;
    currentSettings: SettingsState;
}

export const Settings: React.FC<SettingsProps> = ({ onSettingsChange, currentSettings }) => {
    // Merge current settings with defaults to ensure new fields exist
    // FORCE UPDATE: If the rack waypoints look like they are from the old system (all positive), reset them.
    // Old system: X > 0, Y > 0. New system: Center 0,0 (some negative).
    // Simple check: If RACKS[0] is negative but currentSettings has positive, reset.
    const currentWaypoints = currentSettings.rackWaypoints;
    const needsReset = currentWaypoints && currentWaypoints.length > 0 &&
        currentWaypoints[0].scanPosition.x > 0 && RACKS[0].position.x < 0;

    const [settings, setSettings] = useState<SettingsState>({
        ...DEFAULT_SETTINGS,
        ...currentSettings,
        schedule: { ...DEFAULT_SETTINGS.schedule, ...currentSettings.schedule },
        topics: { ...DEFAULT_SETTINGS.topics, ...currentSettings.topics },
        // Use defaults if needs reset or empty
        rackWaypoints: (needsReset || !currentSettings.rackWaypoints?.length)
            ? DEFAULT_SETTINGS.rackWaypoints
            : currentSettings.rackWaypoints
    });

    const [showAdvanced, setShowAdvanced] = useState(false);
    const [hasChanges, setHasChanges] = useState(false);

    useEffect(() => {
        setHasChanges(JSON.stringify(settings) !== JSON.stringify(currentSettings));
    }, [settings, currentSettings]);

    const handleModeChange = (mode: RobotMode) => {
        setSettings({ ...settings, mode });
    };

    const handleUrlChange = (url: string) => {
        setSettings({
            ...settings,
            connection: { ...settings.connection, url }
        });
    };

    const handleTopicChange = (topic: keyof typeof settings.topics, value: string) => {
        setSettings({
            ...settings,
            topics: { ...settings.topics, [topic]: value }
        });
    };

    const handleScheduleChange = (field: keyof typeof settings.schedule, value: any) => {
        setSettings({
            ...settings,
            schedule: { ...settings.schedule, [field]: value }
        });
    };

    const handleSave = () => {
        onSettingsChange(settings);
        setHasChanges(false);
    };

    const handleReset = () => {
        setSettings(DEFAULT_SETTINGS);
    };

    return (
        <div className="max-w-4xl mx-auto pb-20">
            <div className="bg-sci-panel rounded-xl border border-slate-700 overflow-hidden">
                {/* Header */}
                <div className="p-6 border-b border-slate-700">
                    <div className="flex items-center space-x-3">
                        <SettingsIcon className="text-sci-accent" size={24} />
                        <h2 className="text-2xl font-bold text-white">Settings</h2>
                    </div>
                    <p className="text-slate-400 text-sm mt-2">
                        Configure robot connection, scheduling, and system preferences
                    </p>
                </div>

                {/* Content */}
                <div className="p-6 space-y-8">
                    {/* Robot Mode */}
                    <div>
                        <h3 className="text-lg font-semibold text-white mb-3">Robot Mode</h3>
                        <div className="space-y-3">
                            <label className="flex items-center space-x-3 p-4 bg-slate-800/50 rounded-lg border border-slate-700 cursor-pointer hover:border-sci-accent transition-colors">
                                <input
                                    type="radio"
                                    name="mode"
                                    checked={settings.mode === 'simulation'}
                                    onChange={() => handleModeChange('simulation')}
                                    className="w-4 h-4 text-sci-accent"
                                />
                                <div className="flex-1">
                                    <div className="font-medium text-white">Simulation Mode</div>
                                    <div className="text-sm text-slate-400">
                                        Use simulated robot data for testing and development
                                    </div>
                                </div>
                            </label>

                            <label className="flex items-center space-x-3 p-4 bg-slate-800/50 rounded-lg border border-slate-700 cursor-pointer hover:border-sci-accent transition-colors">
                                <input
                                    type="radio"
                                    name="mode"
                                    checked={settings.mode === 'real'}
                                    onChange={() => handleModeChange('real')}
                                    className="w-4 h-4 text-sci-accent"
                                />
                                <div className="flex-1">
                                    <div className="font-medium text-white">Real Robot Mode</div>
                                    <div className="text-sm text-slate-400">
                                        Connect to a real robot via ROS bridge WebSocket
                                    </div>
                                </div>
                            </label>
                        </div>
                    </div>

                    {/* Scheduling Section */}
                    <div>
                        <div className="flex items-center space-x-2 mb-3">
                            <Calendar className="text-sci-accent" size={20} />
                            <h3 className="text-lg font-semibold text-white">Auto Scan Schedule</h3>
                        </div>
                        <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700 space-y-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <div className="font-medium text-white">Enable Scheduled Scanning</div>
                                    <div className="text-sm text-slate-400">Automatically start scanning rounds at set intervals</div>
                                </div>
                                <label className="relative inline-flex items-center cursor-pointer">
                                    <input
                                        type="checkbox"
                                        className="sr-only peer"
                                        checked={settings.schedule.enabled}
                                        onChange={(e) => handleScheduleChange('enabled', e.target.checked)}
                                    />
                                    <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-sci-accent"></div>
                                </label>
                            </div>

                            {settings.schedule.enabled && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-700">
                                    <div>
                                        <label className="text-sm text-slate-400 block mb-2">Scan Interval (Minutes)</label>
                                        <input
                                            type="number"
                                            min="5"
                                            value={settings.schedule.intervalMinutes}
                                            onChange={(e) => handleScheduleChange('intervalMinutes', parseInt(e.target.value) || 30)}
                                            className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white focus:outline-none focus:border-sci-accent"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-sm text-slate-400 block mb-2">Timezone</label>
                                        <select
                                            value={settings.schedule.timezone}
                                            onChange={(e) => handleScheduleChange('timezone', e.target.value)}
                                            className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white focus:outline-none focus:border-sci-accent"
                                        >
                                            {Intl.supportedValuesOf('timeZone').map(tz => (
                                                <option key={tz} value={tz}>{tz}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Connection Settings (only show in real mode) */}
                    {settings.mode === 'real' && (
                        <div>
                            <h3 className="text-lg font-semibold text-white mb-3">Connection</h3>
                            <div className="space-y-3">
                                <div>
                                    <label className="text-sm text-slate-400 block mb-2">
                                        WebSocket URL
                                    </label>
                                    <input
                                        type="text"
                                        value={settings.connection.url}
                                        onChange={(e) => handleUrlChange(e.target.value)}
                                        placeholder="ws://robot.example.com:9090"
                                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-sci-accent transition-colors"
                                    />
                                </div>

                                <div className="flex items-center justify-between p-4 bg-slate-800/30 rounded-lg border border-slate-700">
                                    <div className="flex items-center space-x-3">
                                        {currentSettings.connection.connected ? (
                                            <>
                                                <Wifi className="text-sci-success" size={20} />
                                                <div>
                                                    <div className="text-sm font-medium text-sci-success">Connected</div>
                                                    <div className="text-xs text-slate-400">
                                                        Robot is online and responding
                                                    </div>
                                                </div>
                                            </>
                                        ) : (
                                            <>
                                                <WifiOff className="text-slate-500" size={20} />
                                                <div>
                                                    <div className="text-sm font-medium text-slate-400">Disconnected</div>
                                                    <div className="text-xs text-slate-500">
                                                        Not connected to robot
                                                    </div>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Advanced Settings */}
                    <div>
                        <button
                            onClick={() => setShowAdvanced(!showAdvanced)}
                            className="flex items-center justify-between w-full p-4 bg-slate-800/50 rounded-lg border border-slate-700 hover:border-sci-accent transition-colors"
                        >
                            <h3 className="text-lg font-semibold text-white">Advanced Settings</h3>
                            {showAdvanced ? (
                                <ChevronUp className="text-slate-400" size={20} />
                            ) : (
                                <ChevronDown className="text-slate-400" size={20} />
                            )}
                        </button>

                        {showAdvanced && (
                            <div className="mt-3 p-4 bg-slate-800/30 rounded-lg border border-slate-700 space-y-6">
                                {/* ROS Topics */}
                                <div>
                                    <h4 className="text-sm font-semibold text-white mb-3">ROS Topic Names</h4>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <label className="text-xs text-slate-400 block mb-1">Position Topic</label>
                                            <input
                                                type="text"
                                                value={settings.topics.position}
                                                onChange={(e) => handleTopicChange('position', e.target.value)}
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-sci-accent"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-slate-400 block mb-1">Battery Topic</label>
                                            <input
                                                type="text"
                                                value={settings.topics.battery}
                                                onChange={(e) => handleTopicChange('battery', e.target.value)}
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-sci-accent"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-slate-400 block mb-1">Manual Cmd Topic</label>
                                            <input
                                                type="text"
                                                value={settings.topics.command}
                                                onChange={(e) => handleTopicChange('command', e.target.value)}
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-sci-accent"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-slate-400 block mb-1">Z-Scan Manual</label>
                                            <input
                                                type="text"
                                                value={settings.topics.zscan}
                                                onChange={(e) => handleTopicChange('zscan', e.target.value)}
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-sci-accent"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-slate-400 block mb-1">Auto Scan Topic</label>
                                            <input
                                                type="text"
                                                value={settings.topics.autoScan}
                                                onChange={(e) => handleTopicChange('autoScan', e.target.value)}
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-sci-accent"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-slate-400 block mb-1">Scan Rack Topic</label>
                                            <input
                                                type="text"
                                                value={settings.topics.scanRack}
                                                onChange={(e) => handleTopicChange('scanRack', e.target.value)}
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-sci-accent"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-slate-400 block mb-1">Restart Topic</label>
                                            <input
                                                type="text"
                                                value={settings.topics.restart}
                                                onChange={(e) => handleTopicChange('restart', e.target.value)}
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-sci-accent"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-slate-400 block mb-1">Status Topic</label>
                                            <input
                                                type="text"
                                                value={settings.topics.status}
                                                onChange={(e) => handleTopicChange('status', e.target.value)}
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-sci-accent"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-slate-400 block mb-1">Restart Localisation</label>
                                            <input
                                                type="text"
                                                value={settings.topics.restartLocalisation}
                                                onChange={(e) => handleTopicChange('restartLocalisation', e.target.value)}
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-sci-accent"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-slate-400 block mb-1">Scan Data (Real)</label>
                                            <input
                                                type="text"
                                                value={settings.topics.scanData || ''}
                                                onChange={(e) => handleTopicChange('scanData', e.target.value)}
                                                placeholder="/scan_data"
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-sci-accent"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-slate-400 block mb-1">Rack Data</label>
                                            <input
                                                type="text"
                                                value={settings.topics.rackData || ''}
                                                onChange={(e) => handleTopicChange('rackData', e.target.value)}
                                                placeholder="/rack_data"
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-sci-accent"
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* Rack Waypoints */}
                                {/* Update Rate */}
                                <div>
                                    <label className="text-xs text-slate-400 block mb-1">Update Rate (Hz)</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="100"
                                        value={settings.updateRate}
                                        onChange={(e) => setSettings({ ...settings, updateRate: parseInt(e.target.value) || 20 })}
                                        className="w-32 bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-sci-accent"
                                    />
                                </div>

                                {/* Debug Mode */}
                                <label className="flex items-center space-x-3 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={settings.debugMode}
                                        onChange={(e) => setSettings({ ...settings, debugMode: e.target.checked })}
                                        className="w-4 h-4 text-sci-accent rounded"
                                    />
                                    <div>
                                        <div className="text-sm font-medium text-white">Debug Mode</div>
                                        <div className="text-xs text-slate-400">
                                            Show detailed logs in browser console
                                        </div>
                                    </div>
                                </label>
                            </div>
                        )}
                    </div>
                </div>

                {/* Footer Actions */}
                <div className="p-6 bg-slate-800/30 border-t border-slate-700 flex justify-between items-center">
                    <button
                        onClick={handleReset}
                        className="flex items-center space-x-2 px-4 py-2 text-slate-400 hover:text-white transition-colors"
                    >
                        <RotateCcw size={16} />
                        <span>Reset to Defaults</span>
                    </button>

                    <button
                        onClick={handleSave}
                        disabled={!hasChanges}
                        className={`flex items-center space-x-2 px-6 py-2 rounded-lg font-medium transition-colors ${hasChanges
                            ? 'bg-sci-accent text-white hover:bg-sci-accent/80'
                            : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                            }`}
                    >
                        <Save size={16} />
                        <span>Save Settings</span>
                    </button>
                </div>
            </div>

            {/* Help Section */}
            <div className="mt-6 p-4 bg-sci-warning/10 border border-sci-warning/20 rounded-lg">
                <h4 className="text-sm font-semibold text-sci-warning mb-2">Connection Troubleshooting</h4>
                <div className="text-xs text-slate-400 space-y-2">
                    <p>
                        If you cannot connect to a remote robot, ensure <strong>rosbridge_server</strong> is listening on all interfaces.
                        Run this command on the robot:
                    </p>
                    <code className="block bg-black/30 p-2 rounded text-sci-accent font-mono select-all">
                        roslaunch rosbridge_server rosbridge_websocket.launch address:=0.0.0.0
                    </code>
                    <p>
                        Also check that port <strong>9090</strong> is open on the robot's firewall.
                    </p>
                </div>
            </div>
        </div>
    );
};
