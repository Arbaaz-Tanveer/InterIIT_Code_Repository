export enum RobotStatus {
  IDLE = 'IDLE',
  MOVING = 'MOVING',
  SCANNING = 'SCANNING',
  ERROR = 'ERROR',
  CHARGING = 'CHARGING',
  OFFLINE = 'OFFLINE'
}

export interface Point {
  x: number;
  y: number;
}

export interface ScannedData {
  id: string;
  rawData: string;      // Full raw scan data (e.g., "R02_S2_ITM430")
  rackId: string;       // Rack ID (e.g., "R02")
  shelfId: string;      // Shelf ID (e.g., "S2")
  itemId: string;       // Item ID (e.g., "ITM430")
  timestamp: string;    // ISO timestamp
  content: string;      // Legacy field for backward compatibility
  category: 'inventory' | 'maintenance' | 'hazard';
}

export interface CommandLogEntry {
  id: string;
  timestamp: number;
  direction: 'OUT' | 'IN';
  command: string;
  payload?: any;
}

export interface RobotState {
  batteryLevel: number;
  position: Point;
  rotation: number; // degrees
  velocity: number;
  status: RobotStatus;
  currentTask: string | null;
  wifiSignal: number;
  autoMode: boolean;
  connected: boolean; // New property for real-time connection status
  commandLog: CommandLogEntry[]; // New: Log of recent commands
}

export interface Rack {
  id: string;
  label: string;
  position: Point;
  width: number;
  height: number;
  scanPointCount?: number;
  pointSpacing?: number; // New: Distance between scan points (cm)
  generatedPoints?: ScanPoint[];
}

export interface NavigationGoal {
  target: Point;
  action: 'move' | 'scan' | 'wait';
}

export interface FilterOptions {
  startDate?: Date;
  endDate?: Date;
  startTime?: string; // HH:MM format
  endTime?: string;   // HH:MM format
  searchQuery?: string;
  category?: 'inventory' | 'maintenance' | 'hazard' | 'all';
}

export interface DeleteResult {
  success: number;
  failed: number;
  errors?: string[];
}

export type RobotMode = 'simulation' | 'real';

export interface RobotConnection {
  url: string;
  connected: boolean;
  lastPing?: number;
}

export interface RosTopicConfig {
  position: string;
  battery: string;
  command: string;
  scan: string;
  wifi?: string;
  autoScan: string;
  status: string; // New: Topic for robot status updates
  restart?: string;
  zscan?: string;
  scanRack?: string;
  restartLocalisation?: string;
  scanData?: string; // New: Topic for real-time scan strings
  rackData?: string; // New: Topic for rack configuration data
}

export interface ScheduleConfig {
  enabled: boolean;
  intervalMinutes: number;
  lastScanTime: number; // timestamp
  nextScanTime: number; // timestamp
  timezone: string;
}

export interface RackWaypoint {
  rackId: string;
  scanPosition: Point; // Where the robot stands to scan this rack
}

export interface SettingsState {
  mode: RobotMode;
  connection: RobotConnection;
  topics: RosTopicConfig;
  updateRate: number;
  debugMode: boolean;
  schedule: ScheduleConfig; // New: Schedule settings
  rackWaypoints: RackWaypoint[]; // New: Custom scan positions
  startPosition: Point; // New: Start position
  stopPosition: Point; // New: Stop position
}

// Map Generator Types
export interface PathSegment {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  direction: number;
}

export interface ScanPoint {
  x: number;
  y: number;
}

export interface MapData {
  id: string;
  name: string;
  userId?: string; // New: Owner of the map
  racks: Rack[];
  pathSegments: PathSegment[];
  scanPoints: ScanPoint[];
  createdAt: number;
  updatedAt: number;
}