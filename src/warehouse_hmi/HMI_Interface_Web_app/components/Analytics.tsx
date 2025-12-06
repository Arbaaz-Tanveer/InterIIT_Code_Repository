import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts';

const BATTERY_DATA = [
    { time: '10:00', level: 100 },
    { time: '10:15', level: 95 },
    { time: '10:30', level: 88 },
    { time: '10:45', level: 82 },
    { time: '11:00', level: 75 },
    { time: '11:15', level: 68 },
    { time: '11:30', level: 60 },
];

const SCAN_EFFICIENCY = [
    { name: 'Rack A', scans: 45 },
    { name: 'Rack B', scans: 32 },
    { name: 'Rack C', scans: 12 },
    { name: 'Dock', scans: 5 },
];

export const Analytics: React.FC = () => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
      <div className="bg-sci-panel p-6 rounded-xl border border-slate-700">
        <h3 className="text-lg font-semibold mb-6 text-slate-200">Battery Discharge Rate</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={BATTERY_DATA}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', borderColor: '#475569', color: '#f1f5f9' }}
              />
              <Line type="monotone" dataKey="level" stroke="#10b981" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-sci-panel p-6 rounded-xl border border-slate-700">
        <h3 className="text-lg font-semibold mb-6 text-slate-200">Scan Efficiency by Zone</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={SCAN_EFFICIENCY}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', borderColor: '#475569', color: '#f1f5f9' }}
              />
              <Legend />
              <Bar dataKey="scans" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
