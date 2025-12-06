import React, { useState, useEffect } from 'react';
import { Download, Search, Filter, Cloud, Loader2, Trash2, Calendar, X } from 'lucide-react';
import { ScannedData } from '../types';
import { subscribeToLogs, deleteScans, deleteScansByDateRange } from '../services/firebase';

export const DataLog: React.FC = () => {
  const [allLogs, setAllLogs] = useState<ScannedData[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<ScannedData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Filter states
  const [showFilters, setShowFilters] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [startTime, setStartTime] = useState('00:00');
  const [endTime, setEndTime] = useState('23:59');
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<'all' | 'inventory' | 'maintenance' | 'hazard'>('all');

  // Subscribe to Firestore on mount
  useEffect(() => {
    const unsubscribe = subscribeToLogs((data) => {
      setAllLogs(data);
      setFilteredLogs(data);
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  // Apply filters whenever filter criteria or logs change
  useEffect(() => {
    let filtered = [...allLogs];

    // Date/Time filtering
    if (startDate || endDate) {
      filtered = filtered.filter(log => {
        const logDate = new Date(log.timestamp);

        if (startDate && endDate) {
          const start = new Date(`${startDate}T${startTime}`);
          const end = new Date(`${endDate}T${endTime}`);
          return logDate >= start && logDate <= end;
        } else if (startDate) {
          const start = new Date(`${startDate}T${startTime}`);
          return logDate >= start;
        } else if (endDate) {
          const end = new Date(`${endDate}T${endTime}`);
          return logDate <= end;
        }
        return true;
      });
    }

    // Search filtering
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(log =>
        log.rackId.toLowerCase().includes(query) ||
        log.content.toLowerCase().includes(query)
      );
    }

    // Category filtering
    if (categoryFilter !== 'all') {
      filtered = filtered.filter(log => log.category === categoryFilter);
    }

    setFilteredLogs(filtered);
  }, [allLogs, startDate, endDate, startTime, endTime, searchQuery, categoryFilter]);

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(filteredLogs.map(log => log.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleSelectOne = (id: string, checked: boolean) => {
    const newSelected = new Set(selectedIds);
    if (checked) {
      newSelected.add(id);
    } else {
      newSelected.delete(id);
    }
    setSelectedIds(newSelected);
  };

  const handleDeleteSelected = async () => {
    if (selectedIds.size === 0) return;

    const confirmed = window.confirm(`Are you sure you want to delete ${selectedIds.size} selected scan(s)? This action cannot be undone.`);
    if (!confirmed) return;

    const result = await deleteScans(Array.from(selectedIds));
    if (result.success > 0) {
      alert(`Successfully deleted ${result.success} scan(s)`);
      setSelectedIds(new Set());
    } else {
      alert('Failed to delete scans. Check console for errors.');
    }
  };

  const handleDeleteByDateRange = async () => {
    if (!startDate || !endDate) {
      alert('Please select both start and end dates to delete by date range.');
      return;
    }

    const start = new Date(`${startDate}T${startTime}`);
    const end = new Date(`${endDate}T${endTime}`);

    const confirmed = window.confirm(
      `Are you sure you want to delete ALL scans between ${start.toLocaleString()} and ${end.toLocaleString()}? This action cannot be undone.`
    );
    if (!confirmed) return;

    const result = await deleteScansByDateRange(start, end);
    if (result.success > 0) {
      alert(`Successfully deleted ${result.success} scan(s)`);
      clearFilters();
    } else {
      alert('Failed to delete scans. Check console for errors.');
    }
  };

  const clearFilters = () => {
    setStartDate('');
    setEndDate('');
    setStartTime('00:00');
    setEndTime('23:59');
    setSearchQuery('');
    setCategoryFilter('all');
    setSelectedIds(new Set());
  };

  const downloadCSV = () => {
    const logsToExport = selectedIds.size > 0
      ? filteredLogs.filter(log => selectedIds.has(log.id))
      : filteredLogs;

    if (logsToExport.length === 0) {
      alert('No data to export');
      return;
    }

    const headers = ['Raw Data', 'Rack ID', 'Shelf ID', 'Item ID', 'Date', 'Time', 'Category'];
    const rows = logsToExport.map(log => {
      const date = new Date(log.timestamp);

      // Handle legacy data that doesn't have shelfId/itemId
      let rawData = log.rawData || '';
      let shelfId = log.shelfId || '';
      let itemId = log.itemId || '';

      // If shelfId or itemId is missing, try to parse from rawData or content
      if (!shelfId || !itemId) {
        // Try parsing rawData first (format: "R02_S2_ITM430")
        if (rawData && rawData.includes('_')) {
          const parts = rawData.split('_');
          if (parts.length >= 3) {
            shelfId = shelfId || parts[1];
            itemId = itemId || parts[2];
          }
        }
        // If still missing, try parsing from content (format: "S2 - ITM430")
        else if (log.content && log.content.includes(' - ')) {
          const parts = log.content.split(' - ');
          if (parts.length >= 2) {
            shelfId = shelfId || parts[0];
            itemId = itemId || parts[1];
          }
        }
        // Reconstruct rawData if it's missing
        if (!rawData && log.rackId) {
          rawData = `${log.rackId}_${shelfId}_${itemId}`;
        }
      }

      return [
        rawData,
        log.rackId,
        shelfId,
        itemId,
        date.toLocaleDateString(),  // Date only
        date.toLocaleTimeString(),  // Time only
        log.category
      ];
    });

    const csvContent = "data:text/csv;charset=utf-8,"
      + headers.join(",") + "\n"
      + rows.map(e => e.join(",")).join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);

    // Generate filename with filter info
    let filename = "robot_scan_data";
    if (startDate || endDate) {
      filename += `_${startDate || 'start'}_to_${endDate || 'end'}`;
    }
    if (selectedIds.size > 0) {
      filename += `_selected_${selectedIds.size}`;
    }
    filename += ".csv";

    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="bg-sci-panel rounded-xl border border-slate-700 overflow-hidden flex flex-col h-full">
      <div className="p-4 border-b border-slate-700 flex justify-between items-center">
        <h3 className="font-semibold flex items-center space-x-2">
          <Cloud size={18} className="text-sci-accent" />
          <span>Cloud Registry</span>
          <span className="text-xs text-slate-500">({filteredLogs.length} records)</span>
        </h3>
        <div className="flex space-x-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 rounded transition-colors ${showFilters ? 'bg-sci-accent text-white' : 'hover:bg-slate-800 text-slate-400'}`}
          >
            <Filter size={18} />
          </button>
          <button
            onClick={downloadCSV}
            className="flex items-center space-x-2 px-3 py-1.5 bg-sci-accent/10 text-sci-accent border border-sci-accent/20 rounded hover:bg-sci-accent hover:text-white transition-colors text-sm font-medium"
          >
            <Download size={16} />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="p-4 bg-slate-800/30 border-b border-slate-700 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-sci-accent"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Start Time</label>
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-sci-accent"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-sci-accent"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">End Time</label>
              <input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-sci-accent"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Search</label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by rack or content..."
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-sci-accent"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Category</label>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value as any)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-sci-accent"
              >
                <option value="all">All Categories</option>
                <option value="inventory">Inventory</option>
                <option value="maintenance">Maintenance</option>
                <option value="hazard">Hazard</option>
              </select>
            </div>
          </div>

          <div className="flex justify-between items-center pt-2">
            <button
              onClick={clearFilters}
              className="flex items-center space-x-1 px-3 py-1.5 text-slate-400 hover:text-white text-sm transition-colors"
            >
              <X size={14} />
              <span>Clear Filters</span>
            </button>
            {startDate && endDate && (
              <button
                onClick={handleDeleteByDateRange}
                className="flex items-center space-x-1 px-3 py-1.5 bg-sci-danger/10 text-sci-danger border border-sci-danger/20 rounded hover:bg-sci-danger hover:text-white transition-colors text-sm"
              >
                <Trash2 size={14} />
                <span>Delete Date Range</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Selection Actions */}
      {selectedIds.size > 0 && (
        <div className="px-4 py-2 bg-sci-accent/10 border-b border-sci-accent/20 flex justify-between items-center">
          <span className="text-sm text-sci-accent font-medium">
            {selectedIds.size} item(s) selected
          </span>
          <button
            onClick={handleDeleteSelected}
            className="flex items-center space-x-1 px-3 py-1.5 bg-sci-danger/10 text-sci-danger border border-sci-danger/20 rounded hover:bg-sci-danger hover:text-white transition-colors text-sm"
          >
            <Trash2 size={14} />
            <span>Delete Selected</span>
          </button>
        </div>
      )}

      <div className="overflow-auto flex-1">
        {loading ? (
          <div className="flex items-center justify-center h-full text-slate-500 space-x-2">
            <Loader2 className="animate-spin" />
            <span>Syncing with Firestore...</span>
          </div>
        ) : (
          <table className="w-full text-left text-sm text-slate-400">
            <thead className="bg-slate-800/50 text-slate-200 uppercase font-mono text-xs sticky top-0">
              <tr>
                <th className="px-4 py-3 w-12">
                  <input
                    type="checkbox"
                    checked={filteredLogs.length > 0 && selectedIds.size === filteredLogs.length}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    className="cursor-pointer"
                  />
                </th>
                <th className="px-6 py-3">Timestamp</th>
                <th className="px-6 py-3">Rack</th>
                <th className="px-6 py-3">Category</th>
                <th className="px-6 py-3">Data Payload</th>
                <th className="px-6 py-3 w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {filteredLogs.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                    {allLogs.length === 0 ? 'No scans recorded yet.' : 'No scans match your filters.'}
                  </td>
                </tr>
              )}
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="px-4 py-4">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(log.id)}
                      onChange={(e) => handleSelectOne(log.id, e.target.checked)}
                      className="cursor-pointer"
                    />
                  </td>
                  <td className="px-6 py-4 font-mono text-xs text-slate-500">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-white">{log.rackId}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase ${log.category === 'hazard' ? 'bg-sci-danger/20 text-sci-danger' :
                      log.category === 'maintenance' ? 'bg-sci-warning/20 text-sci-warning' :
                        'bg-sci-success/20 text-sci-success'
                      }`}>
                      {log.category}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-mono text-slate-300">{log.content}</td>
                  <td className="px-6 py-4">
                    <button
                      onClick={async () => {
                        if (window.confirm('Delete this scan?')) {
                          await deleteScans([log.id]);
                        }
                      }}
                      className="p-1.5 text-sci-danger hover:bg-sci-danger/10 rounded transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};