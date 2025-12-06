import { Rack } from './types';

export const WAREHOUSE_WIDTH = 800;
export const WAREHOUSE_HEIGHT = 600;

// Mock Warehouse Layout
// Mock Warehouse Layout (Center is 0,0)
export const RACKS = [
  { id: 'rack1', label: 'Rack 1', position: { x: -300, y: 200 }, width: 80, height: 20 },
  { id: 'rack2', label: 'Rack 2', position: { x: -100, y: 200 }, width: 80, height: 20 },
  { id: 'rack3', label: 'Rack 3', position: { x: 100, y: 200 }, width: 80, height: 20 },
  { id: 'rack4', label: 'Rack 4', position: { x: 300, y: 200 }, width: 80, height: 20 },
  { id: 'rack5', label: 'Rack 5', position: { x: -300, y: -100 }, width: 80, height: 20 },
];

export const POSITIONS = {
  START: { x: -350, y: -250 },
  STOP: { x: 350, y: -250 }
};

export const DEMO_LOGS = [
  { id: '1', rackId: 'R-A1', timestamp: new Date(Date.now() - 100000).toISOString(), content: 'Box-772-Alpha', category: 'inventory' },
  { id: '2', rackId: 'R-A2', timestamp: new Date(Date.now() - 200000).toISOString(), content: 'Err-Motor-Check', category: 'maintenance' },
  { id: '3', rackId: 'R-B1', timestamp: new Date(Date.now() - 50000).toISOString(), content: 'Hazmat-Class-2', category: 'hazard' },
] as const;
