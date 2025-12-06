import React, { useState, useEffect, useRef } from 'react';
import { RACKS, WAREHOUSE_HEIGHT, WAREHOUSE_WIDTH } from '../constants';
import { MapData, PathSegment, Rack, ScanPoint } from '../types';
import { mapService } from '../services/mapService';
import { robotService } from '../services/robotService';
import { auth } from '../services/firebase';
import { Save, Upload, Plus, Trash2, Play, Grid, MousePointer, Move, Check, X } from 'lucide-react';

interface MapGeneratorProps {
    onPublish: (map: MapData) => void;
}

export const MapGenerator: React.FC<MapGeneratorProps> = ({ onPublish }) => {
    // State
    const [maps, setMaps] = useState<MapData[]>([]);
    const [currentMap, setCurrentMap] = useState<MapData>({
        id: '',
        name: 'New Map',
        racks: [],
        pathSegments: [],
        scanPoints: [],
        createdAt: Date.now(),
        updatedAt: Date.now()
    });

    const [mode, setMode] = useState<'SELECT' | 'DRAW_PATH' | 'ADD_RACK' | 'BOX_SELECT'>('SELECT');
    const [selectedElement, setSelectedElement] = useState<{ type: 'RACK' | 'PATH' | 'POINT', index: number } | null>(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [drawStart, setDrawStart] = useState<{ x: number, y: number } | null>(null);
    const [mousePos, setMousePos] = useState<{ x: number, y: number }>({ x: 0, y: 0 });

    // Drag State
    const [isDragging, setIsDragging] = useState(false);
    const [dragOffset, setDragOffset] = useState<{ x: number, y: number }>({ x: 0, y: 0 });

    const [defaultRackProps, setDefaultRackProps] = useState({
        width: 80,
        height: 20,
        scanPointCount: 2,
        pointSpacing: 50
    });
    const [showMapSelector, setShowMapSelector] = useState(false);

    // Data Preview & Reordering State
    const [showPreview, setShowPreview] = useState(false);
    const [reorderedScanPoints, setReorderedScanPoints] = useState<ScanPoint[]>([]);
    const [reorderedPathSegments, setReorderedPathSegments] = useState<PathSegment[]>([]);
    const [reorderedRacks, setReorderedRacks] = useState<Rack[]>([]);

    // Zoom & Pan State for Reorder Preview
    const [previewZoom, setPreviewZoom] = useState(1);
    const [previewPan, setPreviewPan] = useState({ x: 0, y: 0 });
    const [isPanning, setIsPanning] = useState(false);
    const [panStart, setPanStart] = useState({ x: 0, y: 0 });


    // Undo History
    const [history, setHistory] = useState<MapData[]>([]);

    // Box Select State
    const [boxSelectStart, setBoxSelectStart] = useState<{ x: number, y: number } | null>(null);
    const [boxSelectEnd, setBoxSelectEnd] = useState<{ x: number, y: number } | null>(null);
    const [selectedItems, setSelectedItems] = useState<{ racks: number[], paths: number[], points: number[] }>({ racks: [], paths: [], points: [] });

    // Default Map
    const [defaultMapId, setDefaultMapId] = useState<string | null>(null);

    // Constants
    const GRID_SIZE = 50; // cm

    // Load Maps on Mount and load default map
    useEffect(() => {
        loadMaps();
        const savedDefaultId = mapService.getDefaultMapId();
        setDefaultMapId(savedDefaultId);
    }, []);

    const loadMaps = async () => {
        const loadedMaps = await mapService.getAllMaps();
        console.log("📍 Loaded maps from Firebase:", loadedMaps);
        console.log("📍 Map IDs:", loadedMaps.map(m => ({ name: m.name, id: m.id })));
        setMaps(loadedMaps);

        // Auto-load default map if set
        const savedDefaultId = mapService.getDefaultMapId();
        if (savedDefaultId) {
            const defaultMap = loadedMaps.find(m => m.id === savedDefaultId);
            if (defaultMap) {
                setCurrentMap(defaultMap);
                console.log("✅ Auto-loaded default map:", defaultMap.name);
            }
        }
    };

    // Coordinate Helpers
    const toScreenX = (x: number) => ((x + WAREHOUSE_WIDTH / 2) / WAREHOUSE_WIDTH) * 100;
    const toScreenY = (y: number) => ((WAREHOUSE_HEIGHT / 2 - y) / WAREHOUSE_HEIGHT) * 100;
    const fromScreenX = (pctX: number) => (pctX / 100 * WAREHOUSE_WIDTH) - (WAREHOUSE_WIDTH / 2);
    const fromScreenY = (pctY: number) => (WAREHOUSE_HEIGHT / 2) - (pctY / 100 * WAREHOUSE_HEIGHT);

    // Snap to Grid
    const snap = (val: number) => Math.round(val / GRID_SIZE) * GRID_SIZE;

    // Helper: Get Rotation from Direction Value (Fixed for correct arrow orientation)
    const getRotation = (dir: number) => {
        switch (dir) {
            case 2: return 180; // Left
            case 3: return 90;  // Front/Up (was 270, now corrected)
            case 4: return 0;   // Right
            case 5: return 270; // Bottom/Down (was 90, now corrected)
            default: return 0;
        }
    };

    // Handlers
    const handleSvgMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
        if (isDragging) return;

        const rect = e.currentTarget.getBoundingClientRect();
        const x = fromScreenX(((e.clientX - rect.left) / rect.width) * 100);
        const y = fromScreenY(((e.clientY - rect.top) / rect.height) * 100);

        const snappedX = snap(x);
        const snappedY = snap(y);

        if (mode === 'BOX_SELECT') {
            // Start box selection
            saveToHistory();
            setBoxSelectStart({ x, y });
            setBoxSelectEnd({ x, y });
        } else if (mode === 'DRAW_PATH') {
            setIsDrawing(true);
            setDrawStart({ x: snappedX, y: snappedY });
            setMousePos({ x, y }); // Initialize mouse pos
        } else if (mode === 'ADD_RACK') {
            saveToHistory();
            const newRack: Rack = {
                id: `rack-${Date.now()}`,
                label: `Rack ${currentMap.racks.length + 1}`,
                position: { x: snappedX, y: snappedY },
                width: defaultRackProps.width,
                height: defaultRackProps.height,
                scanPointCount: defaultRackProps.scanPointCount,
                pointSpacing: defaultRackProps.pointSpacing,
                generatedPoints: []
            };
            setCurrentMap(prev => ({
                ...prev,
                racks: [...prev.racks, newRack]
            }));
        } else if (mode === 'ADD_POINT') {
            saveToHistory();
            const newPoint: ScanPoint = { x: snappedX, y: snappedY };
            setCurrentMap(prev => ({
                ...prev,
                scanPoints: [...prev.scanPoints, newPoint]
            }));
        } else if (mode === 'SELECT') {
            setSelectedElement(null);
        }
    };

    const handleSvgMouseUp = (e: React.MouseEvent<SVGSVGElement>) => {
        if (mode === 'BOX_SELECT' && boxSelectStart) {
            // Box selection complete - keep the selection
            setBoxSelectStart(null);
            setBoxSelectEnd(null);
        } else if (isDrawing && drawStart) {
            const rect = e.currentTarget.getBoundingClientRect();
            const x = fromScreenX(((e.clientX - rect.left) / rect.width) * 100);
            const y = fromScreenY(((e.clientY - rect.top) / rect.height) * 100);
            const snappedX = snap(x);
            const snappedY = snap(y);

            // Only add if length > 0
            if (snappedX !== drawStart.x || snappedY !== drawStart.y) {
                const newSegment: PathSegment = {
                    x1: drawStart.x,
                    y1: drawStart.y,
                    x2: snappedX,
                    y2: snappedY,
                    direction: 4 // Default Right (4)
                };
                setCurrentMap(prev => ({
                    ...prev,
                    pathSegments: [...prev.pathSegments, newSegment]
                }));
            }
        }
        setIsDrawing(false);
        setDrawStart(null);
        setIsDragging(false);
    };

    const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const x = fromScreenX(((e.clientX - rect.left) / rect.width) * 100);
        const y = fromScreenY(((e.clientY - rect.top) / rect.height) * 100);
        setMousePos({ x, y });

        // Box select drag
        if (mode === 'BOX_SELECT' && boxSelectStart) {
            setBoxSelectEnd({ x, y });

            // Calculate selected items
            const box = { x1: boxSelectStart.x, y1: boxSelectStart.y, x2: x, y2: y };
            const selectedRacks: number[] = [];
            const selectedPaths: number[] = [];
            const selectedPoints: number[] = [];

            currentMap.racks.forEach((rack, i) => {
                if (isInBox(rack.position.x, rack.position.y, box)) {
                    selectedRacks.push(i);
                }
            });

            currentMap.pathSegments.forEach((seg, i) => {
                const midX = (seg.x1 + seg.x2) / 2;
                const midY = (seg.y1 + seg.y2) / 2;
                if (isInBox(midX, midY, box)) {
                    selectedPaths.push(i);
                }
            });

            currentMap.scanPoints.forEach((pt, i) => {
                if (isInBox(pt.x, pt.y, box)) {
                    selectedPoints.push(i);
                }
            });

            setSelectedItems({ racks: selectedRacks, paths: selectedPaths, points: selectedPoints });
        }

        if (isDragging && selectedElement?.type === 'RACK') {
            const snappedX = snap(x - dragOffset.x);
            const snappedY = snap(y - dragOffset.y);

            const newRacks = [...currentMap.racks];
            newRacks[selectedElement.index].position = { x: snappedX, y: snappedY };
            setCurrentMap(prev => ({ ...prev, racks: newRacks }));
        }
    };

    const handleRackMouseDown = (index: number, e: React.MouseEvent) => {
        e.stopPropagation(); // Prevent SVG click
        if (mode !== 'SELECT') return;

        setSelectedElement({ type: 'RACK', index });
        setIsDragging(true);
        // Calculate offset from mouse to rack center
        // Simplified: just assume grabbing center for now to avoid complex offset logic with snap
        setDragOffset({ x: 0, y: 0 });
    };

    const handlePathClick = (index: number, e: React.MouseEvent) => {
        e.stopPropagation();
        if (mode !== 'SELECT') return;
        setSelectedElement({ type: 'PATH', index });
    };

    const deleteSelected = () => {
        if (!selectedElement) return;
        if (selectedElement.type === 'RACK') {
            setCurrentMap(prev => ({
                ...prev,
                racks: prev.racks.filter((_, i) => i !== selectedElement.index)
            }));
        } else if (selectedElement.type === 'PATH') {
            setCurrentMap(prev => ({
                ...prev,
                pathSegments: prev.pathSegments.filter((_, i) => i !== selectedElement.index)
            }));
        } else if (selectedElement.type === 'POINT') {
            setCurrentMap(prev => ({
                ...prev,
                scanPoints: prev.scanPoints.filter((_, i) => i !== selectedElement.index)
            }));
        }
        setSelectedElement(null);
    };

    // Logic: Project Points for a specific rack
    const projectPointsForRack = (rackIndex: number) => {
        const rack = currentMap.racks[rackIndex];
        const count = rack.scanPointCount || 1;
        const spacing = rack.pointSpacing || 50; // Default 50cm
        const points: ScanPoint[] = [];

        // 1. Calculate source points along the rack width (X-axis relative to rack)
        for (let i = 0; i < count; i++) {
            // Calculate offset from center
            // Formula: (i - (count - 1) / 2) * spacing
            const offset = (i - (count - 1) / 2) * spacing;

            // Determine orientation based on width/height ratio
            // If width > height, it's horizontal, distribute along X
            // If height > width, it's vertical, distribute along Y
            let sourceX = rack.position.x;
            let sourceY = rack.position.y;

            if (rack.width >= rack.height) {
                sourceX += offset;
            } else {
                sourceY += offset;
            }

            // 2. Find nearest segment and project
            let bestPoint: ScanPoint | null = null;
            let minProjDist = Infinity;

            currentMap.pathSegments.forEach(seg => {
                // Segment endpoints
                const x1 = seg.x1;
                const y1 = seg.y1;
                const x2 = seg.x2;
                const y2 = seg.y2;

                // Project (sourceX, sourceY) onto line segment (x1,y1)-(x2,y2)
                const dx = x2 - x1;
                const dy = y2 - y1;
                if (dx === 0 && dy === 0) return;

                // Vector AP
                const t = ((sourceX - x1) * dx + (sourceY - y1) * dy) / (dx * dx + dy * dy);

                // Check if projection falls within segment (0 <= t <= 1)
                if (t >= 0 && t <= 1) {
                    const projX = x1 + t * dx;
                    const projY = y1 + t * dy;

                    // Distance from source to projection
                    const dist = Math.hypot(sourceX - projX, sourceY - projY);

                    if (dist < minProjDist) {
                        minProjDist = dist;
                        bestPoint = { x: projX, y: projY };
                    }
                }
            });

            if (bestPoint) {
                points.push(bestPoint);
            }
        }

        // Update Rack
        const newRacks = [...currentMap.racks];
        newRacks[rackIndex].generatedPoints = points;
        setCurrentMap(prev => ({ ...prev, racks: newRacks }));
    };

    const removePointsForRack = (rackIndex: number) => {
        const newRacks = [...currentMap.racks];
        newRacks[rackIndex].generatedPoints = [];
        setCurrentMap(prev => ({ ...prev, racks: newRacks }));
    };

    // Save Map to Firebase
    const saveMap = async () => {
        if (!currentMap.name) return alert("Please name your map");
        try {
            // Get current user
            const user = auth.currentUser;
            if (!user) {
                alert("You must be logged in to save maps.");
                return;
            }

            // Remove id from the data to save (Firestore handles document IDs separately)
            const { id, ...mapDataWithoutId } = currentMap;
            const mapToSave = {
                ...mapDataWithoutId,
                userId: user.uid // Add User ID
            };

            if (currentMap.id) {
                await mapService.updateMap(currentMap.id, mapToSave);
                alert("Map Updated!");
            } else {
                const newId = await mapService.saveMap(mapToSave);
                setCurrentMap(prev => ({ ...prev, id: newId, userId: user.uid }));
                alert("Map Saved!");
            }
            loadMaps();
        } catch (e: any) {
            console.error("Save Error:", e);
            alert(`Error saving map: ${e.message || "Unknown error"}`);
        }
    };

    const publishMap = () => {
        // Combine manual points and generated rack points
        const allPoints: ScanPoint[] = [...currentMap.scanPoints];
        currentMap.racks.forEach(rack => {
            if (rack.generatedPoints) {
                rack.generatedPoints.forEach(p => allPoints.push(p));
            }
        });

        // Convert to arrays for ROS if needed, or update robotService to accept objects
        // Assuming robotService needs update or we convert here.
        // Let's convert to arrays for compatibility if robotService expects arrays.
        // But wait, robotService takes ScanPoint[] which is now {x,y}[].
        // I need to check robotService.
        // But wait, robotService takes ScanPoint[] which is now {x,y}[].
        // I need to check robotService.
        robotService.publishMapData(allPoints, currentMap.pathSegments, currentMap.racks);
        alert(`Published ${allPoints.length} scan points, ${currentMap.pathSegments.length} segments, and ${currentMap.racks.length} racks to ROS!`);
    };

    const deleteMap = async (id: string) => {
        console.log("Attempting to delete map with ID:", id);

        if (!id) {
            console.error("❌ Attempted to delete map with no ID");
            return;
        }

        // Check Auth
        const user = auth.currentUser;
        if (!user) {
            console.error("❌ User not logged in. Cannot delete map.");
            alert("You must be logged in to delete maps.");
            return;
        }

        if (confirm("Are you sure you want to delete this map?")) {
            try {
                console.log("Sending delete request to Firebase...");
                await mapService.deleteMap(id);
                console.log("✅ Map deleted successfully from Firebase");

                // Update local state immediately
                setMaps(prev => prev.filter(m => m.id !== id));

                if (currentMap.id === id) {
                    setCurrentMap({
                        id: '',
                        name: 'New Map',
                        racks: [],
                        pathSegments: [],
                        scanPoints: [],
                        createdAt: Date.now(),
                        updatedAt: Date.now()
                    });
                }
            } catch (error: any) {
                console.error("❌ Failed to delete map:", error);
                alert(`Failed to delete map: ${error.message || "Unknown error"}. Check console for details.`);
            }
        }
    };

    // Save to history before making changes
    const saveToHistory = () => {
        setHistory(prev => [...prev.slice(-19), { ...currentMap }]); // Keep last 20 states
    };

    // Undo function
    const undo = () => {
        if (history.length > 0) {
            const previousState = history[history.length - 1];
            setCurrentMap(previousState);
            setHistory(prev => prev.slice(0, -1));
        }
    };

    // Box select helper
    const isInBox = (x: number, y: number, box: { x1: number, y1: number, x2: number, y2: number }) => {
        const minX = Math.min(box.x1, box.x2);
        const maxX = Math.max(box.x1, box.x2);
        const minY = Math.min(box.y1, box.y2);
        const maxY = Math.max(box.y1, box.y2);
        return x >= minX && x <= maxX && y >= minY && y <= maxY;
    };

    // Delete selected items
    const deleteSelectedItems = () => {
        if (selectedItems.racks.length === 0 && selectedItems.paths.length === 0 && selectedItems.points.length === 0) {
            return;
        }

        saveToHistory();
        setCurrentMap(prev => ({
            ...prev,
            racks: prev.racks.filter((_, i) => !selectedItems.racks.includes(i)),
            pathSegments: prev.pathSegments.filter((_, i) => !selectedItems.paths.includes(i)),
            scanPoints: prev.scanPoints.filter((_, i) => !selectedItems.points.includes(i))
        }));
        setSelectedItems({ racks: [], paths: [], points: [] });
        setMode('SELECT');
    };


    // Generate Grid Labels
    const gridLabels = [];
    for (let x = -WAREHOUSE_WIDTH / 2; x <= WAREHOUSE_WIDTH / 2; x += 100) {
        gridLabels.push(<text key={`x-${x}`} x={toScreenX(x)} y="99" fontSize="2" fill="rgba(255,255,255,0.3)" textAnchor="middle">{x}</text>);
    }
    for (let y = -WAREHOUSE_HEIGHT / 2; y <= WAREHOUSE_HEIGHT / 2; y += 100) {
        gridLabels.push(<text key={`y-${y}`} x="1" y={toScreenY(y)} fontSize="2" fill="rgba(255,255,255,0.3)" dominantBaseline="middle">{y}</text>);
    }

    return (
        <div className="flex h-full bg-slate-900 text-white">
            {/* Sidebar Controls */}
            <div className="w-64 bg-slate-800 border-r border-slate-700 p-4 flex flex-col space-y-4 overflow-y-auto">
                <h2 className="text-xl font-bold text-sci-accent">Map Generator</h2>

                {/* Map Selection */}
                <div>
                    <label className="text-xs text-slate-400">Current Map</label>
                    <div className="flex space-x-2">
                        <button
                            onClick={() => setShowMapSelector(true)}
                            className="flex-1 bg-slate-700 hover:bg-slate-600 text-xs py-2 rounded border border-slate-600 truncate px-2"
                        >
                            {currentMap.name || "Select Map..."}
                        </button>
                        <button
                            onClick={() => {
                                setCurrentMap({
                                    id: '',
                                    name: 'New Map',
                                    racks: [],
                                    pathSegments: [],
                                    scanPoints: [],
                                    createdAt: Date.now(),
                                    updatedAt: Date.now()
                                });
                            }}
                            className="bg-sci-accent/20 hover:bg-sci-accent/30 text-sci-accent p-2 rounded border border-sci-accent/50"
                            title="New Map"
                        >
                            <Plus size={16} />
                        </button>
                    </div>
                </div>

                {/* Map Name */}
                <div>
                    <label className="text-xs text-slate-400">Map Name</label>
                    <input
                        type="text"
                        value={currentMap.name}
                        onChange={e => setCurrentMap({ ...currentMap, name: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm"
                    />
                </div>

                <div className="h-px bg-slate-700 my-2" />

                {/* Tools */}
                <div className="grid grid-cols-2 gap-2">
                    <button
                        onClick={() => setMode('SELECT')}
                        className={`p-2 rounded flex flex-col items-center justify-center text-xs ${mode === 'SELECT' ? 'bg-sci-accent text-slate-900' : 'bg-slate-700 hover:bg-slate-600'}`}
                    >
                        <MousePointer size={16} className="mb-1" /> Select
                    </button>
                    <button
                        onClick={() => setMode('DRAW_PATH')}
                        className={`p-2 rounded flex flex-col items-center justify-center text-xs ${mode === 'DRAW_PATH' ? 'bg-sci-accent text-slate-900' : 'bg-slate-700 hover:bg-slate-600'}`}
                    >
                        <Move size={16} className="mb-1" /> Draw Path
                    </button>
                    <button
                        onClick={() => setMode('ADD_RACK')}
                        className={`p-2 rounded flex flex-col items-center justify-center text-xs ${mode === 'ADD_RACK' ? 'bg-sci-accent text-slate-900' : 'bg-slate-700 hover:bg-slate-600'}`}
                    >
                        <Plus size={16} className="mb-1" /> Add Rack
                    </button>
                    <button
                        onClick={() => setMode('ADD_POINT')}
                        className={`p-2 rounded flex flex-col items-center justify-center text-xs ${mode === 'ADD_POINT' ? 'bg-sci-accent text-slate-900' : 'bg-slate-700 hover:bg-slate-600'}`}
                    >
                        <Grid size={16} className="mb-1" /> Add Point
                    </button>
                    <button
                        onClick={() => {
                            setMode('BOX_SELECT');
                            setSelectedItems({ racks: [], paths: [], points: [] });
                        }}
                        className={`p-2 rounded flex flex-col items-center justify-center text-xs ${mode === 'BOX_SELECT' ? 'bg-sci-accent text-slate-900' : 'bg-slate-700 hover:bg-slate-600'}`}
                    >
                        <span className="mb-1">📦</span> Box Select
                    </button>
                    <button
                        onClick={undo}
                        disabled={history.length === 0}
                        className="p-2 rounded flex flex-col items-center justify-center text-xs bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <span className="mb-1">↶</span> Undo
                    </button>
                    <button
                        onClick={deleteSelected}
                        disabled={!selectedElement}
                        className="col-span-2 p-2 rounded flex flex-col items-center justify-center text-xs bg-red-900/50 text-red-400 hover:bg-red-900/80 disabled:opacity-50"
                    >
                        <Trash2 size={16} className="mb-1" /> Delete Selected
                    </button>
                </div>

                {/* Box Select Actions */}
                {mode === 'BOX_SELECT' && (selectedItems.racks.length > 0 || selectedItems.paths.length > 0 || selectedItems.points.length > 0) && (
                    <div className="bg-purple-900/30 border border-purple-500/50 rounded p-2 mt-2">
                        <div className="text-xs text-purple-300 mb-2">
                            Selected: {selectedItems.racks.length} racks, {selectedItems.paths.length} paths, {selectedItems.points.length} points
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                            <button
                                onClick={deleteSelectedItems}
                                className="p-2 rounded text-xs bg-red-600 hover:bg-red-500 text-white font-bold"
                            >
                                Delete All
                            </button>
                            <button
                                onClick={() => {
                                    setSelectedItems({ racks: [], paths: [], points: [] });
                                    setMode('SELECT');
                                }}
                                className="p-2 rounded text-xs bg-slate-700 hover:bg-slate-600"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                )}

                {/* Default Properties (Visible when Adding Rack) */}
                {mode === 'ADD_RACK' && (
                    <div className="bg-slate-700/50 p-2 rounded border border-slate-600">
                        <h3 className="text-xs font-bold text-slate-300 mb-2">New Rack Defaults</h3>
                        <div className="grid grid-cols-2 gap-2">
                            <div>
                                <label className="text-[10px] text-slate-400">Width</label>
                                <input type="number" value={defaultRackProps.width} onChange={e => setDefaultRackProps({ ...defaultRackProps, width: parseInt(e.target.value) })} className="w-full bg-slate-800 rounded px-1 text-xs" />
                            </div>
                            <div>
                                <label className="text-[10px] text-slate-400">Height</label>
                                <input type="number" value={defaultRackProps.height} onChange={e => setDefaultRackProps({ ...defaultRackProps, height: parseInt(e.target.value) })} className="w-full bg-slate-800 rounded px-1 text-xs" />
                            </div>
                            <div>
                                <label className="text-[10px] text-slate-400">Scan Points</label>
                                <input type="number" value={defaultRackProps.scanPointCount} onChange={e => setDefaultRackProps({ ...defaultRackProps, scanPointCount: parseInt(e.target.value) })} className="w-full bg-slate-800 rounded px-1 text-xs" />
                            </div>
                            <div>
                                <label className="text-[10px] text-slate-400">Point Spacing</label>
                                <input type="number" value={defaultRackProps.pointSpacing} onChange={e => setDefaultRackProps({ ...defaultRackProps, pointSpacing: parseInt(e.target.value) })} className="w-full bg-slate-800 rounded px-1 text-xs" />
                            </div>
                        </div>
                    </div>
                )}

                <div className="h-px bg-slate-700 my-2" />

                {/* Actions */}
                <button
                    onClick={saveMap}
                    className="w-full py-2 bg-green-600 hover:bg-green-500 rounded text-sm font-medium flex items-center justify-center space-x-2"
                >
                    <Save size={16} /> <span>Save Map</span>
                </button>

                {/* Set as Default Button */}
                {currentMap.id && (
                    <button
                        onClick={() => {
                            mapService.setDefaultMap(currentMap.id);
                            setDefaultMapId(currentMap.id);
                            alert(`✅ "${currentMap.name}" is now the default map!`);
                        }}
                        className={`w-full py-2 rounded text-sm font-medium flex items-center justify-center space-x-2 ${defaultMapId === currentMap.id
                                ? 'bg-yellow-600 hover:bg-yellow-500'
                                : 'bg-slate-600 hover:bg-slate-500'
                            }`}
                    >
                        <span>{defaultMapId === currentMap.id ? '⭐' : '☆'}</span>
                        <span>{defaultMapId === currentMap.id ? 'Default Map' : 'Set as Default'}</span>
                    </button>
                )}

                <button
                    onClick={publishMap}
                    className="w-full py-2 bg-sci-accent text-slate-900 hover:bg-sci-accent/90 rounded text-sm font-bold flex items-center justify-center space-x-2"
                >
                    <Upload size={16} /> <span>Publish to ROS</span>
                </button>

                {/* Reorder Points Button & Modal */}
                <div className="mt-4">
                    <button
                        onClick={() => {
                            setShowPreview(true);
                            // Initialize reordered arrays
                            const allPoints: ScanPoint[] = [...currentMap.scanPoints];
                            currentMap.racks.forEach(rack => {
                                if (rack.generatedPoints) {
                                    rack.generatedPoints.forEach(p => allPoints.push(p));
                                }
                            });
                            setReorderedScanPoints(allPoints);
                            setReorderedPathSegments([...currentMap.pathSegments]);
                            setReorderedRacks([...currentMap.racks]);
                        }}
                        className="w-full py-2 bg-purple-600 hover:bg-purple-500 rounded text-sm font-bold flex items-center justify-center space-x-2"
                    >
                        <span>🔄 Reorder Points</span>
                    </button>
                </div>

                {/* Reorder Modal */}
                {
                    showPreview && (
                        <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-6">
                            <div className="bg-slate-800 rounded-lg w-full max-w-6xl h-[90vh] flex flex-col">
                                {/* Header */}
                                <div className="flex justify-between items-center p-4 border-b border-slate-700">
                                    <h2 className="text-xl font-bold text-white">🔄 Reorder Points & Paths</h2>
                                    <div className="flex space-x-2">
                                        <button
                                            onClick={() => {
                                                // Apply reordered data
                                                setCurrentMap(prev => ({
                                                    ...prev,
                                                    scanPoints: reorderedScanPoints.filter((_, i) => i < prev.scanPoints.length),
                                                    pathSegments: reorderedPathSegments,
                                                    racks: reorderedRacks
                                                }));
                                                setShowPreview(false);
                                            }}
                                            className="px-4 py-2 bg-sci-accent text-slate-900 rounded font-bold hover:bg-sci-accent/90"
                                        >
                                            Apply Order
                                        </button>
                                        <button
                                            onClick={() => setShowPreview(false)}
                                            className="px-4 py-2 bg-slate-700 text-white rounded hover:bg-slate-600"
                                        >
                                            <X size={20} />
                                        </button>
                                    </div>
                                </div>

                                {/* Content */}
                                <div className="flex-1 overflow-hidden flex">
                                    {/* Lists Panel */}
                                    <div className="w-1/2 p-4 overflow-y-auto space-y-4 border-r border-slate-700">
                                        {/* Scan Points */}
                                        <div>
                                            <h3 className="text-sm font-bold text-sci-accent mb-2">
                                                Scan Points ({reorderedScanPoints.length})
                                            </h3>
                                            <div className="space-y-1">
                                                {reorderedScanPoints.map((pt, i) => (
                                                    <div
                                                        key={`reorder-scan-${i}`}
                                                        draggable
                                                        onDragStart={(e) => {
                                                            e.dataTransfer.effectAllowed = 'move';
                                                            e.dataTransfer.setData('type', 'scan');
                                                            e.dataTransfer.setData('index', i.toString());
                                                        }}
                                                        onDragOver={(e) => e.preventDefault()}
                                                        onDrop={(e) => {
                                                            e.preventDefault();
                                                            const type = e.dataTransfer.getData('type');
                                                            if (type === 'scan') {
                                                                const fromIndex = parseInt(e.dataTransfer.getData('index'));
                                                                const toIndex = i;
                                                                const newPoints = [...reorderedScanPoints];
                                                                const [moved] = newPoints.splice(fromIndex, 1);
                                                                newPoints.splice(toIndex, 0, moved);
                                                                setReorderedScanPoints(newPoints);
                                                            }
                                                        }}
                                                        className="text-xs bg-slate-700 p-2 rounded cursor-move hover:bg-slate-600 flex justify-between items-center"
                                                    >
                                                        <div className="flex items-center space-x-2">
                                                            <span className="text-slate-400">⋮⋮</span>
                                                            <span className="text-white font-mono">#{i + 1}</span>
                                                            <span className="text-slate-300">({pt.x}, {pt.y})</span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Path Segments */}
                                        <div>
                                            <h3 className="text-sm font-bold text-sci-accent mb-2">
                                                Path Segments ({reorderedPathSegments.length})
                                            </h3>
                                            <div className="space-y-1">
                                                {reorderedPathSegments.map((seg, i) => (
                                                    <div
                                                        key={`reorder-path-${i}`}
                                                        draggable
                                                        onDragStart={(e) => {
                                                            e.dataTransfer.effectAllowed = 'move';
                                                            e.dataTransfer.setData('type', 'path');
                                                            e.dataTransfer.setData('index', i.toString());
                                                        }}
                                                        onDragOver={(e) => e.preventDefault()}
                                                        onDrop={(e) => {
                                                            e.preventDefault();
                                                            const type = e.dataTransfer.getData('type');
                                                            if (type === 'path') {
                                                                const fromIndex = parseInt(e.dataTransfer.getData('index'));
                                                                const toIndex = i;
                                                                const newSegments = [...reorderedPathSegments];
                                                                const [moved] = newSegments.splice(fromIndex, 1);
                                                                newSegments.splice(toIndex, 0, moved);
                                                                setReorderedPathSegments(newSegments);
                                                            }
                                                        }}
                                                        className="text-xs bg-slate-700 p-2 rounded cursor-move hover:bg-slate-600"
                                                    >
                                                        <div className="flex items-center space-x-2">
                                                            <span className="text-slate-400">⋮⋮</span>
                                                            <span className="text-white font-mono">#{i + 1}</span>
                                                            <span className="text-slate-300">Dir: {seg.direction}</span>
                                                        </div>
                                                        <div className="text-slate-500 text-[10px] mt-1 ml-6">
                                                            ({seg.x1}, {seg.y1}) → ({seg.x2}, {seg.y2})
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Racks */}
                                        <div>
                                            <h3 className="text-sm font-bold text-sci-accent mb-2">
                                                Racks ({reorderedRacks.length})
                                            </h3>
                                            <div className="space-y-1">
                                                {reorderedRacks.map((rack, i) => (
                                                    <div
                                                        key={`reorder-rack-${i}`}
                                                        draggable
                                                        onDragStart={(e) => {
                                                            e.dataTransfer.effectAllowed = 'move';
                                                            e.dataTransfer.setData('type', 'rack');
                                                            e.dataTransfer.setData('index', i.toString());
                                                        }}
                                                        onDragOver={(e) => e.preventDefault()}
                                                        onDrop={(e) => {
                                                            e.preventDefault();
                                                            const type = e.dataTransfer.getData('type');
                                                            if (type === 'rack') {
                                                                const fromIndex = parseInt(e.dataTransfer.getData('index'));
                                                                const toIndex = i;
                                                                const newRacks = [...reorderedRacks];
                                                                const [moved] = newRacks.splice(fromIndex, 1);
                                                                newRacks.splice(toIndex, 0, moved);
                                                                setReorderedRacks(newRacks);
                                                            }
                                                        }}
                                                        className="text-xs bg-slate-700 p-2 rounded cursor-move hover:bg-slate-600"
                                                    >
                                                        <div className="flex items-center space-x-2">
                                                            <span className="text-slate-400">⋮⋮</span>
                                                            <span className="text-white font-semibold">#{i + 1} {rack.label}</span>
                                                        </div>
                                                        <div className="text-slate-500 text-[10px] mt-1 ml-6">
                                                            {rack.width}×{rack.height} at ({rack.position.x}, {rack.position.y})
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Preview Panel */}
                                    <div className="w-1/2 p-4 bg-slate-900">
                                        <div className="flex justify-between items-center mb-2">
                                            <h3 className="text-sm font-bold text-white">Preview (Zoomable)</h3>
                                            <div className="flex items-center space-x-2">
                                                <button
                                                    onClick={() => setPreviewZoom(prev => Math.max(0.5, prev * 0.8))}
                                                    className="text-xs px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded font-bold"
                                                    title="Zoom Out"
                                                >
                                                    −
                                                </button>
                                                <span className="text-xs text-slate-400 min-w-[3rem] text-center">{Math.round(previewZoom * 100)}%</span>
                                                <button
                                                    onClick={() => setPreviewZoom(prev => Math.min(5, prev * 1.25))}
                                                    className="text-xs px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded font-bold"
                                                    title="Zoom In"
                                                >
                                                    +
                                                </button>
                                                <button
                                                    onClick={() => {
                                                        setPreviewZoom(1);
                                                        setPreviewPan({ x: 0, y: 0 });
                                                    }}
                                                    className="text-xs px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded"
                                                >
                                                    Reset
                                                </button>
                                            </div>
                                        </div>
                                        <div
                                            className="bg-slate-950 rounded h-full flex items-center justify-center overflow-hidden relative cursor-move touch-none"
                                            onWheel={(e) => {
                                                e.preventDefault();
                                                e.stopPropagation();
                                                const delta = e.deltaY > 0 ? 0.9 : 1.1;
                                                setPreviewZoom(prev => Math.max(0.5, Math.min(5, prev * delta)));
                                            }}
                                            onMouseDown={(e) => {
                                                e.preventDefault();
                                                setIsPanning(true);
                                                setPanStart({ x: e.clientX - previewPan.x, y: e.clientY - previewPan.y });
                                            }}
                                            onMouseMove={(e) => {
                                                if (isPanning) {
                                                    e.preventDefault();
                                                    setPreviewPan({
                                                        x: e.clientX - panStart.x,
                                                        y: e.clientY - panStart.y
                                                    });
                                                }
                                            }}
                                            onMouseUp={(e) => {
                                                e.preventDefault();
                                                setIsPanning(false);
                                            }}
                                            onMouseLeave={() => setIsPanning(false)}
                                            onTouchStart={(e) => {
                                                if (e.touches.length === 1) {
                                                    setIsPanning(true);
                                                    setPanStart({
                                                        x: e.touches[0].clientX - previewPan.x,
                                                        y: e.touches[0].clientY - previewPan.y
                                                    });
                                                } else if (e.touches.length === 2) {
                                                    setIsPanning(false);
                                                    const touch1 = e.touches[0];
                                                    const touch2 = e.touches[1];
                                                    const dist = Math.hypot(
                                                        touch2.clientX - touch1.clientX,
                                                        touch2.clientY - touch1.clientY
                                                    );
                                                    setPanStart({ x: 0, y: 0, initialDist: dist });
                                                }
                                            }}
                                            onTouchMove={(e) => {
                                                e.preventDefault();
                                                if (e.touches.length === 1 && isPanning) {
                                                    setPreviewPan({
                                                        x: e.touches[0].clientX - panStart.x,
                                                        y: e.touches[0].clientY - panStart.y
                                                    });
                                                } else if (e.touches.length === 2 && panStart.initialDist) {
                                                    const touch1 = e.touches[0];
                                                    const touch2 = e.touches[1];
                                                    const dist = Math.hypot(
                                                        touch2.clientX - touch1.clientX,
                                                        touch2.clientY - touch1.clientY
                                                    );
                                                    const scale = dist / panStart.initialDist;
                                                    setPreviewZoom(prev => Math.max(0.5, Math.min(5, prev * scale)));
                                                    setPanStart(prev => ({ ...prev, initialDist: dist }));
                                                }
                                            }}
                                            onTouchEnd={() => {
                                                setIsPanning(false);
                                                setPanStart({ x: 0, y: 0 });
                                            }}
                                        >
                                            <div
                                                style={{
                                                    transform: `translate(${previewPan.x}px, ${previewPan.y}px) scale(${previewZoom})`,
                                                    transformOrigin: 'center',
                                                    transition: isPanning ? 'none' : 'transform 0.1s ease-out'
                                                }}
                                            >
                                                <svg viewBox="0 0 100 100" className="w-full h-full" style={{ width: '600px', height: '600px' }}>
                                                    <rect width="100" height="100" fill="#0a0e1a" />

                                                    {/* Paths */}
                                                    {reorderedPathSegments.map((seg, i) => (
                                                        <g key={`preview-path-${i}`}>
                                                            <line
                                                                x1={toScreenX(seg.x1)}
                                                                y1={toScreenY(seg.y1)}
                                                                x2={toScreenX(seg.x2)}
                                                                y2={toScreenY(seg.y2)}
                                                                stroke="#94a3b8"
                                                                strokeWidth="0.5"
                                                            />
                                                            <text
                                                                x={toScreenX((seg.x1 + seg.x2) / 2)}
                                                                y={toScreenY((seg.y1 + seg.y2) / 2)}
                                                                fill="#22d3ee"
                                                                fontSize="2"
                                                                textAnchor="middle"
                                                            >
                                                                {i + 1}
                                                            </text>
                                                        </g>
                                                    ))}

                                                    {/* Scan Points */}
                                                    {reorderedScanPoints.map((pt, i) => (
                                                        <g key={`preview-scan-${i}`}>
                                                            <circle
                                                                cx={toScreenX(pt.x)}
                                                                cy={toScreenY(pt.y)}
                                                                r="0.5"
                                                                fill="#f59e0b"
                                                            />
                                                            <text
                                                                x={toScreenX(pt.x)}
                                                                y={toScreenY(pt.y) - 1.2}
                                                                fill="#fbbf24"
                                                                fontSize="1.2"
                                                                fontWeight="bold"
                                                                textAnchor="middle"
                                                                dominantBaseline="middle"
                                                            >
                                                                {i + 1}
                                                            </text>
                                                        </g>
                                                    ))}

                                                    {/* Racks */}
                                                    {reorderedRacks.map((rack, i) => (
                                                        <g key={`preview-rack-${i}`}>
                                                            <rect
                                                                x={toScreenX(rack.position.x) - ((rack.width / WAREHOUSE_WIDTH) * 100) / 2}
                                                                y={toScreenY(rack.position.y) - ((rack.height / WAREHOUSE_HEIGHT) * 100) / 2}
                                                                width={(rack.width / WAREHOUSE_WIDTH) * 100}
                                                                height={(rack.height / WAREHOUSE_HEIGHT) * 100}
                                                                fill="rgba(51, 65, 85, 0.8)"
                                                                stroke="#475569"
                                                                strokeWidth="0.3"
                                                            />
                                                            <text
                                                                x={toScreenX(rack.position.x)}
                                                                y={toScreenY(rack.position.y)}
                                                                fill="white"
                                                                fontSize="1.5"
                                                                textAnchor="middle"
                                                                dominantBaseline="middle"
                                                            >
                                                                {i + 1}
                                                            </text>
                                                        </g>
                                                    ))}
                                                </svg>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )
                }

                {/* Selected Item Properties */}
                {
                    selectedElement && (
                        <div className="bg-slate-900/50 p-2 rounded border border-slate-700 mt-4 space-y-2">
                            <h3 className="text-xs font-bold text-slate-400 mb-2">Properties</h3>

                            {selectedElement.type === 'PATH' && (
                                <>
                                    <div className="grid grid-cols-2 gap-2">
                                        <div>
                                            <label className="text-[10px] text-slate-500">X1</label>
                                            <input type="number" value={currentMap.pathSegments[selectedElement.index].x1}
                                                onChange={(e) => {
                                                    const newSegments = [...currentMap.pathSegments];
                                                    newSegments[selectedElement.index].x1 = parseInt(e.target.value);
                                                    setCurrentMap({ ...currentMap, pathSegments: newSegments });
                                                }}
                                                className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs" />
                                        </div>
                                        <div>
                                            <label className="text-[10px] text-slate-500">Y1</label>
                                            <input type="number" value={currentMap.pathSegments[selectedElement.index].y1}
                                                onChange={(e) => {
                                                    const newSegments = [...currentMap.pathSegments];
                                                    newSegments[selectedElement.index].y1 = parseInt(e.target.value);
                                                    setCurrentMap({ ...currentMap, pathSegments: newSegments });
                                                }}
                                                className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs" />
                                        </div>
                                        <div>
                                            <label className="text-[10px] text-slate-500">X2</label>
                                            <input type="number" value={currentMap.pathSegments[selectedElement.index].x2}
                                                onChange={(e) => {
                                                    const newSegments = [...currentMap.pathSegments];
                                                    newSegments[selectedElement.index].x2 = parseInt(e.target.value);
                                                    setCurrentMap({ ...currentMap, pathSegments: newSegments });
                                                }}
                                                className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs" />
                                        </div>
                                        <div>
                                            <label className="text-[10px] text-slate-500">Y2</label>
                                            <input type="number" value={currentMap.pathSegments[selectedElement.index].y2}
                                                onChange={(e) => {
                                                    const newSegments = [...currentMap.pathSegments];
                                                    newSegments[selectedElement.index].y2 = parseInt(e.target.value);
                                                    setCurrentMap({ ...currentMap, pathSegments: newSegments });
                                                }}
                                                className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs" />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="text-[10px] text-slate-500">Direction</label>
                                        <select
                                            value={currentMap.pathSegments[selectedElement.index].direction}
                                            onChange={(e) => {
                                                const newSegments = [...currentMap.pathSegments];
                                                newSegments[selectedElement.index].direction = parseInt(e.target.value);
                                                setCurrentMap({ ...currentMap, pathSegments: newSegments });
                                            }}
                                            className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-white"
                                        >
                                            <option value={4}>Right (4)</option>
                                            <option value={3}>Front/Up (3)</option>
                                            <option value={2}>Left (2)</option>
                                            <option value={5}>Bottom/Down (5)</option>
                                        </select>
                                    </div>
                                </>
                            )}

                            {selectedElement.type === 'RACK' && (
                                <div className="space-y-2">
                                    <div>
                                        <label className="text-[10px] text-slate-500">Label</label>
                                        <input
                                            type="text"
                                            value={currentMap.racks[selectedElement.index].label}
                                            onChange={(e) => {
                                                const newRacks = [...currentMap.racks];
                                                newRacks[selectedElement.index].label = e.target.value;
                                                setCurrentMap({ ...currentMap, racks: newRacks });
                                            }}
                                            className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs"
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-2">
                                        <div>
                                            <label className="text-[10px] text-slate-500">X</label>
                                            <input
                                                type="number"
                                                value={currentMap.racks[selectedElement.index].position.x}
                                                onChange={(e) => {
                                                    const newRacks = [...currentMap.racks];
                                                    newRacks[selectedElement.index].position.x = parseInt(e.target.value);
                                                    setCurrentMap({ ...currentMap, racks: newRacks });
                                                }}
                                                className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] text-slate-500">Y</label>
                                            <input
                                                type="number"
                                                value={currentMap.racks[selectedElement.index].position.y}
                                                onChange={(e) => {
                                                    const newRacks = [...currentMap.racks];
                                                    newRacks[selectedElement.index].position.y = parseInt(e.target.value);
                                                    setCurrentMap({ ...currentMap, racks: newRacks });
                                                }}
                                                className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] text-slate-500">Width</label>
                                            <input
                                                type="number"
                                                value={currentMap.racks[selectedElement.index].width}
                                                onChange={(e) => {
                                                    const newRacks = [...currentMap.racks];
                                                    newRacks[selectedElement.index].width = parseInt(e.target.value);
                                                    setCurrentMap({ ...currentMap, racks: newRacks });
                                                }}
                                                className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] text-slate-500">Height</label>
                                            <input
                                                type="number"
                                                value={currentMap.racks[selectedElement.index].height}
                                                onChange={(e) => {
                                                    const newRacks = [...currentMap.racks];
                                                    newRacks[selectedElement.index].height = parseInt(e.target.value);
                                                    setCurrentMap({ ...currentMap, racks: newRacks });
                                                }}
                                                className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] text-slate-500">Scan Points</label>
                                            <input
                                                type="number"
                                                value={currentMap.racks[selectedElement.index].scanPointCount || 4}
                                                onChange={(e) => {
                                                    const newRacks = [...currentMap.racks];
                                                    newRacks[selectedElement.index].scanPointCount = parseInt(e.target.value);
                                                    setCurrentMap({ ...currentMap, racks: newRacks });
                                                }}
                                                className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] text-slate-500">Point Spacing (cm)</label>
                                            <input
                                                type="number"
                                                value={currentMap.racks[selectedElement.index].pointSpacing || 50}
                                                onChange={(e) => {
                                                    const newRacks = [...currentMap.racks];
                                                    newRacks[selectedElement.index].pointSpacing = parseInt(e.target.value);
                                                    setCurrentMap({ ...currentMap, racks: newRacks });
                                                }}
                                                className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs"
                                            />
                                        </div>
                                    </div>
                                    <div className="flex space-x-2 pt-2">
                                        <button
                                            onClick={() => {
                                                const newRacks = [...currentMap.racks];
                                                const rack = newRacks[selectedElement.index];
                                                // Swap width and height
                                                const temp = rack.width;
                                                rack.width = rack.height;
                                                rack.height = temp;
                                                setCurrentMap({ ...currentMap, racks: newRacks });
                                            }}
                                            className="flex-1 bg-slate-700 hover:bg-slate-600 text-[10px] py-1 rounded"
                                        >
                                            Rotate
                                        </button>
                                        <button
                                            onClick={() => projectPointsForRack(selectedElement.index)}
                                            className="flex-1 bg-blue-600 hover:bg-blue-500 text-[10px] py-1 rounded"
                                        >
                                            Project Points
                                        </button>
                                        <button
                                            onClick={() => removePointsForRack(selectedElement.index)}
                                            className="flex-1 bg-slate-700 hover:bg-slate-600 text-[10px] py-1 rounded"
                                        >
                                            Clear Points
                                        </button>
                                    </div>
                                </div>
                            )}

                            {selectedElement.type === 'POINT' && (
                                <div className="grid grid-cols-2 gap-2">
                                    <div>
                                        <label className="text-[10px] text-slate-500">X</label>
                                        <input
                                            type="number"
                                            value={currentMap.scanPoints[selectedElement.index].x}
                                            onChange={(e) => {
                                                const newPoints = [...currentMap.scanPoints];
                                                newPoints[selectedElement.index].x = parseInt(e.target.value);
                                                setCurrentMap({ ...currentMap, scanPoints: newPoints });
                                            }}
                                            className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-[10px] text-slate-500">Y</label>
                                        <input
                                            type="number"
                                            value={currentMap.scanPoints[selectedElement.index].y}
                                            onChange={(e) => {
                                                const newPoints = [...currentMap.scanPoints];
                                                newPoints[selectedElement.index].y = parseInt(e.target.value);
                                                setCurrentMap({ ...currentMap, scanPoints: newPoints });
                                            }}
                                            className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs"
                                        />
                                    </div>
                                </div>
                            )}
                        </div>
                    )
                }
            </div >

            {/* Canvas Area */}
            < div className="flex-1 relative bg-[#0f172a] overflow-hidden" >
                <svg
                    className="w-full h-full cursor-crosshair"
                    viewBox="0 0 100 100"
                    preserveAspectRatio="none"
                    onMouseDown={handleSvgMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleSvgMouseUp}
                    onMouseLeave={handleSvgMouseUp}
                >
                    {/* Enhanced Grid Background */}
                    <defs>
                        {/* Fine grid */}
                        <pattern id="grid-fine" width="5" height="5" patternUnits="userSpaceOnUse">
                            <path d="M 5 0 L 0 0 0 5" fill="none" stroke="rgba(6,182,212,0.08)" strokeWidth="0.05" />
                        </pattern>
                        {/* Medium grid */}
                        <pattern id="grid-medium" width="12.5" height="12.5" patternUnits="userSpaceOnUse">
                            <rect width="12.5" height="12.5" fill="url(#grid-fine)" />
                            <path d="M 12.5 0 L 0 0 0 12.5" fill="none" stroke="rgba(6,182,212,0.12)" strokeWidth="0.08" />
                        </pattern>
                        {/* Large grid with glow */}
                        <pattern id="grid-large" width="25" height="25" patternUnits="userSpaceOnUse">
                            <rect width="25" height="25" fill="url(#grid-medium)" />
                            <path d="M 25 0 L 0 0 0 25" fill="none" stroke="rgba(6,182,212,0.2)" strokeWidth="0.15" filter="url(#glow)" />
                        </pattern>
                        {/* Glow filter */}
                        <filter id="glow">
                            <feGaussianBlur stdDeviation="0.3" result="coloredBlur" />
                            <feMerge>
                                <feMergeNode in="coloredBlur" />
                                <feMergeNode in="SourceGraphic" />
                            </feMerge>
                        </filter>
                    </defs>
                    <rect width="100" height="100" fill="#0a0e1a" />
                    <rect width="100" height="100" fill="url(#grid-large)" />

                    {/* Grid Labels */}
                    {gridLabels}

                    {/* Axes */}
                    <line x1="50" y1="0" x2="50" y2="100" stroke="rgba(255,255,255,0.2)" strokeWidth="0.2" />
                    <line x1="0" y1="50" x2="100" y2="50" stroke="rgba(255,255,255,0.2)" strokeWidth="0.2" />

                    {/* Path Segments */}
                    {currentMap.pathSegments.map((seg, i) => (
                        <g
                            key={`path-${i}`}
                            onClick={(e) => handlePathClick(i, e)}
                            className="cursor-pointer"
                            style={{ pointerEvents: mode === 'ADD_POINT' ? 'none' : 'auto' }}
                        >
                            {/* Invisible Hit Area (Thicker) */}
                            <line
                                x1={toScreenX(seg.x1)}
                                y1={toScreenY(seg.y1)}
                                x2={toScreenX(seg.x2)}
                                y2={toScreenY(seg.y2)}
                                stroke="transparent"
                                strokeWidth="2"
                            />
                            {/* Visible Line */}
                            <line
                                x1={toScreenX(seg.x1)}
                                y1={toScreenY(seg.y1)}
                                x2={toScreenX(seg.x2)}
                                y2={toScreenY(seg.y2)}
                                stroke={selectedElement?.type === 'PATH' && selectedElement.index === i ? '#22d3ee' : '#94a3b8'}
                                strokeWidth="0.5"
                                className="hover:stroke-white transition-colors"
                            />
                            {/* Direction Arrow */}
                            <g transform={`translate(${toScreenX((seg.x1 + seg.x2) / 2)}, ${toScreenY((seg.y1 + seg.y2) / 2)}) rotate(${-getRotation(seg.direction)})`}>
                                {/* Arrow size adjusted for 100x100 viewbox */}
                                <path d="M -1 -1 L 1 0 L -1 1 Z" fill="#06b6d4" stroke="white" strokeWidth="0.1" />
                            </g>
                        </g>
                    ))}

                    {/* Drawing Line Preview */}
                    {isDrawing && drawStart && (
                        <line
                            x1={toScreenX(drawStart.x)}
                            y1={toScreenY(drawStart.y)}
                            x2={toScreenX(snap(mousePos.x))}
                            y2={toScreenY(snap(mousePos.y))}
                            stroke="#22d3ee"
                            strokeWidth="0.5"
                            strokeDasharray="1,1"
                        />
                    )}

                    {/* Box Select Rectangle */}
                    {boxSelectStart && boxSelectEnd && (
                        <rect
                            x={Math.min(toScreenX(boxSelectStart.x), toScreenX(boxSelectEnd.x))}
                            y={Math.min(toScreenY(boxSelectStart.y), toScreenY(boxSelectEnd.y))}
                            width={Math.abs(toScreenX(boxSelectEnd.x) - toScreenX(boxSelectStart.x))}
                            height={Math.abs(toScreenY(boxSelectEnd.y) - toScreenY(boxSelectStart.y))}
                            fill="rgba(168, 85, 247, 0.1)"
                            stroke="#a855f7"
                            strokeWidth="0.3"
                            strokeDasharray="1,1"
                        />
                    )}

                    {/* Racks */}
                    {currentMap.racks.map((rack, i) => (
                        <g key={rack.id} onMouseDown={(e) => handleRackMouseDown(i, e)} onClick={(e) => e.stopPropagation()} style={{ cursor: 'move' }}>
                            <rect
                                x={toScreenX(rack.position.x) - ((rack.width / WAREHOUSE_WIDTH) * 100) / 2}
                                y={toScreenY(rack.position.y) - ((rack.height / WAREHOUSE_HEIGHT) * 100) / 2}
                                width={(rack.width / WAREHOUSE_WIDTH) * 100}
                                height={(rack.height / WAREHOUSE_HEIGHT) * 100}
                                fill={
                                    selectedItems.racks.includes(i) ? 'rgba(168, 85, 247, 0.3)' :
                                        selectedElement?.type === 'RACK' && selectedElement.index === i ? 'rgba(34, 211, 238, 0.2)' :
                                            'rgba(51, 65, 85, 0.8)'
                                }
                                stroke={
                                    selectedItems.racks.includes(i) ? '#a855f7' :
                                        selectedElement?.type === 'RACK' && selectedElement.index === i ? '#22d3ee' :
                                            '#475569'
                                }
                                strokeWidth="0.3"
                            />
                            <text
                                x={toScreenX(rack.position.x)}
                                y={toScreenY(rack.position.y)}
                                textAnchor="middle"
                                dominantBaseline="middle"
                                fill="white"
                                fontSize="2"
                                className="pointer-events-none select-none"
                            >
                                {rack.label}
                            </text>
                            {/* Render Rack's Generated Points */}
                            {rack.generatedPoints?.map((pt, j) => (
                                <circle
                                    key={`rack-pt-${i}-${j}`}
                                    cx={toScreenX(pt.x)}
                                    cy={toScreenY(pt.y)}
                                    r="0.5"
                                    fill="#22c55e"
                                />
                            ))}
                        </g>
                    ))}

                    {/* Manual Scan Points */}
                    {currentMap.scanPoints.map((pt, i) => (
                        <circle
                            key={`scan-${i}`}
                            cx={toScreenX(pt.x)}
                            cy={toScreenY(pt.y)}
                            r={selectedElement?.type === 'POINT' && selectedElement.index === i ? "1" : "0.5"}
                            fill={selectedElement?.type === 'POINT' && selectedElement.index === i ? "#fbbf24" : "#f59e0b"}
                            className="cursor-pointer hover:fill-yellow-300"
                            onClick={(e) => {
                                e.stopPropagation();
                                setSelectedElement({ type: 'POINT', index: i });
                            }}
                        />
                    ))}

                </svg>

                {/* Mouse Info */}
                <div className="absolute bottom-4 right-4 bg-black/70 px-2 py-1 rounded text-xs font-mono text-slate-400 pointer-events-none">
                    X: {Math.round(snap(fromScreenX((mousePos.x + 400) / 800 * 100)))} Y: {Math.round(snap(fromScreenY((mousePos.y + 300) / 600 * 100)))}
                </div>
            </div >
            {/* Map Selector Modal */}
            {
                showMapSelector && (
                    <div className="absolute inset-0 bg-black/80 z-50 flex items-center justify-center p-10">
                        <div className="bg-slate-800 rounded-lg p-6 w-full max-w-4xl h-full max-h-[80vh] flex flex-col">
                            <div className="flex justify-between items-center mb-4">
                                <h2 className="text-xl font-bold text-white">Select Map</h2>
                                <button onClick={() => setShowMapSelector(false)} className="text-slate-400 hover:text-white">
                                    <X size={24} />
                                </button>
                            </div>

                            {/* Map Grid in Modal */}
                            <div className="grid grid-cols-3 gap-4 overflow-y-auto p-2">
                                {maps.map(map => (
                                    <div
                                        key={map.id}
                                        className="bg-slate-900 border border-slate-700 rounded-lg p-2 hover:border-sci-accent group relative"
                                    >
                                        {/* Mini Preview - Click to Select */}
                                        <div
                                            className="w-full h-32 bg-slate-950 rounded mb-2 overflow-hidden relative cursor-pointer"
                                            onClick={() => {
                                                setCurrentMap(map);
                                                setShowMapSelector(false);
                                            }}
                                        >
                                            <svg viewBox="0 0 100 100" className="w-full h-full opacity-50 group-hover:opacity-100 transition-opacity pointer-events-none">
                                                {map.pathSegments.map((seg, i) => (
                                                    <line key={i} x1={toScreenX(seg.x1)} y1={toScreenY(seg.y1)} x2={toScreenX(seg.x2)} y2={toScreenY(seg.y2)} stroke="#94a3b8" strokeWidth="2" />
                                                ))}
                                                {map.racks.map((rack, i) => (
                                                    <rect key={i}
                                                        x={toScreenX(rack.position.x) - ((rack.width / WAREHOUSE_WIDTH) * 100) / 2}
                                                        y={toScreenY(rack.position.y) - ((rack.height / WAREHOUSE_HEIGHT) * 100) / 2}
                                                        width={(rack.width / WAREHOUSE_WIDTH) * 100}
                                                        height={(rack.height / WAREHOUSE_HEIGHT) * 100}
                                                        fill="#334155"
                                                    />
                                                ))}
                                            </svg>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            {/* Name - Click to Select */}
                                            <span
                                                className="font-bold text-sm truncate cursor-pointer hover:text-sci-accent"
                                                onClick={() => {
                                                    setCurrentMap(map);
                                                    setShowMapSelector(false);
                                                }}
                                            >
                                                {map.name}
                                            </span>
                                            <div className="flex items-center space-x-2">
                                                <span className="text-[10px] text-slate-500">{new Date(map.updatedAt).toLocaleDateString()}</span>
                                                {/* Delete Button - Isolated */}
                                                <button
                                                    onClick={(e) => {
                                                        e.preventDefault();
                                                        e.stopPropagation();
                                                        console.log("Delete button clicked for map:", map.id);
                                                        deleteMap(map.id);
                                                    }}
                                                    className="p-1.5 bg-slate-800 hover:bg-red-900/50 text-slate-400 hover:text-red-400 rounded border border-slate-700 hover:border-red-500/50 transition-colors z-10"
                                                    title="Delete Map"
                                                    type="button"
                                                >
                                                    <Trash2 size={14} className="pointer-events-none" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                                {maps.length === 0 && (
                                    <div className="col-span-3 text-center text-slate-500 py-8">
                                        No saved maps found.
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )
            }



        </div >
    )
}
