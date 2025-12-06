import { RobotState, RobotStatus, Point, SettingsState, RobotMode, ScanPoint, PathSegment } from '../types';
import { saveScanLog } from './firebase';
import { WAREHOUSE_HEIGHT } from '../constants';
import * as ROSLIB from 'roslib';

export class RobotService {
  private state: RobotState = {
    batteryLevel: 85,
    position: { x: 250, y: -200 }, // Start at dock
    rotation: 0,
    velocity: 0,
    status: RobotStatus.IDLE,
    currentTask: null,
    wifiSignal: 90,
    autoMode: false,
    connected: false,
    commandLog: []
  };

  private subscribers: ((state: RobotState) => void)[] = [];
  private simulationInterval: number | null = null;
  private systemInterval: number | null = null;

  // Simulation physics
  private target: Point | null = null;
  private autoScanIndex: number = 0;

  // ROS Bridge
  private ros: ROSLIB.Ros | null = null;
  private mode: RobotMode = 'simulation';
  private settings: SettingsState | null = null;
  private rosTopics: Map<string, ROSLIB.Topic<any>> = new Map();

  constructor() {
    // Restore simulation state
    // Restore simulation state
    // const savedAutoMode = localStorage.getItem('sim_auto_mode');
    // if (savedAutoMode === 'true') {
    //   this.state.autoMode = true;
    //   this.state.status = RobotStatus.MOVING;
    //   this.processAutoScanStep();
    // }
    // User requested auto-scan to be OFF by default
    this.state.autoMode = false;
    localStorage.setItem('sim_auto_mode', 'false');

    this.startSimulationLoop();
    this.startSystemLoop();
  }

  public subscribe(callback: (state: RobotState) => void): () => void {
    this.subscribers.push(callback);
    callback({ ...this.state });
    return () => {
      this.subscribers = this.subscribers.filter(s => s !== callback);
    };
  }

  private notify() {
    this.subscribers.forEach(cb => cb({ ...this.state }));
  }

  public updateSettings(newSettings: SettingsState): void {
    const previousMode = this.mode;
    this.mode = newSettings.mode;
    this.settings = newSettings;

    // Mode changed
    if (previousMode !== this.mode) {
      if (this.mode === 'real') {
        this.connectToRobot(newSettings.connection.url);
      } else {
        this.disconnectFromRobot();
      }
    } else if (this.mode === 'real' && this.ros) {
      if (this.ros.isConnected && this.settings.connection.url !== newSettings.connection.url) {
        this.disconnectFromRobot();
        this.connectToRobot(newSettings.connection.url);
      }
    }

    // Check if we need to restore auto mode state from settings (if persisted)
    // For now, we assume the app passes the correct state
  }

  // ... ROS Connection methods (connectToRobot, disconnectFromRobot) ...
  // ... ROS Connection methods ...
  private reconnectInterval: number | null = null;

  private connectToRobot(url: string): void {
    if (this.ros) {
      // If already connected to the same URL, do nothing
      if (this.ros.isConnected && (this.ros as any).socket.url === url) return;
      this.disconnectFromRobot();
    }

    console.log(`🔌 Connecting to robot at ${url}...`);
    this.ros = new ROSLIB.Ros({ url: url });

    this.ros.on('connection', () => {
      console.log('✅ Connected to robot!');
      this.state.connected = true;
      if (this.settings) {
        this.settings.connection.connected = true;
        this.settings.connection.lastPing = Date.now();
      }
      this.subscribeToRosTopics();
      this.notify();

      // Clear reconnect interval if connected
      if (this.reconnectInterval) {
        window.clearInterval(this.reconnectInterval);
        this.reconnectInterval = null;
      }
    });

    this.ros.on('error', (error: any) => {
      // console.error('❌ ROS connection error:', error); // Reduce noise
      this.state.connected = false;
      if (this.settings) this.settings.connection.connected = false;
      this.notify();
      this.ensureReconnectStrategy(url);
    });

    this.ros.on('close', () => {
      console.log('🔌 Disconnected from robot');
      this.state.connected = false;
      if (this.settings) this.settings.connection.connected = false;
      this.notify();
      this.ensureReconnectStrategy(url);
    });
  }

  private ensureReconnectStrategy(url: string) {
    if (this.mode === 'real' && !this.reconnectInterval) {
      console.log('🔄 Starting auto-reconnect strategy...');
      this.reconnectInterval = window.setInterval(() => {
        if (this.mode === 'real' && (!this.ros || !this.ros.isConnected)) {
          // console.log('🔄 Retrying connection...');
          this.connectToRobot(url);
        }
      }, 5000); // Retry every 5 seconds
    }
  }

  private disconnectFromRobot(): void {
    if (this.reconnectInterval) {
      window.clearInterval(this.reconnectInterval);
      this.reconnectInterval = null;
    }
    if (this.ros) {
      this.rosTopics.forEach(topic => topic.unsubscribe());
      this.rosTopics.clear();
      this.ros.close();
      this.ros = null;
      this.state.connected = false;
      if (this.settings) this.settings.connection.connected = false;
    }
  }

  private subscribeToRosTopics(): void {
    if (!this.ros || !this.settings) return;
    const topics = this.settings.topics;

    // Position
    const positionTopic = new ROSLIB.Topic({
      ros: this.ros,
      name: topics.position,
      messageType: 'geometry_msgs/PoseStamped'
    });
    positionTopic.subscribe((message: any) => {
      if (message.pose) {
        this.state.position = {
          x: message.pose.position.x * 100,
          y: message.pose.position.y * 100 // Assuming robot sends meters, we convert to pixels
        };
        // Rotation logic...
        const q = message.pose.orientation;
        const siny_cosp = 2 * (q.w * q.z + q.x * q.y);
        const cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z);
        this.state.rotation = Math.atan2(siny_cosp, cosy_cosp) * (180 / Math.PI);
      }
      this.notify();
    });
    this.rosTopics.set('position', positionTopic);

    // Battery
    const batteryTopic = new ROSLIB.Topic({
      ros: this.ros,
      name: topics.battery,
      messageType: 'sensor_msgs/BatteryState'
    });
    batteryTopic.subscribe((message: any) => {
      if (message.percentage !== undefined) this.state.batteryLevel = message.percentage * 100;
      this.notify();
    });
    this.rosTopics.set('battery', batteryTopic);

    // WiFi
    if (topics.wifi) {
      const wifiTopic = new ROSLIB.Topic({
        ros: this.ros,
        name: topics.wifi,
        messageType: 'std_msgs/Float32'
      });
      wifiTopic.subscribe((message: any) => {
        if (message.data !== undefined) this.state.wifiSignal = message.data;
        this.notify();
      });
      this.rosTopics.set('wifi', wifiTopic);
    }

    // Auto Scan Status (New)
    if (topics.autoScan) {
      const autoScanTopic = new ROSLIB.Topic({
        ros: this.ros,
        name: topics.autoScan,
        messageType: 'std_msgs/String'
      });
      // We publish to this, but could also subscribe if robot echoes
    }

    // Status Sync Topic (New)
    if (topics.status) {
      const statusTopic = new ROSLIB.Topic({
        ros: this.ros,
        name: topics.status,
        messageType: 'std_msgs/String' // Expecting JSON string
      });
      statusTopic.subscribe((message: any) => {
        this.logCommand('IN', 'STATUS_UPDATE', message.data);
        try {
          const statusData = JSON.parse(message.data);
          if (statusData.status) this.state.status = statusData.status;
          if (statusData.autoMode !== undefined) this.state.autoMode = statusData.autoMode;
          if (statusData.currentTask) this.state.currentTask = statusData.currentTask;
          this.notify();
        } catch (e) {
          console.warn('Failed to parse status update:', e);
        }
      });
      this.rosTopics.set('status', statusTopic);
    }

    // Real-time Scan Data (New)
    if (topics.scanData) {
      const scanDataTopic = new ROSLIB.Topic({
        ros: this.ros,
        name: topics.scanData,
        messageType: 'std_msgs/String'
      });
      scanDataTopic.subscribe(async (message: any) => {
        const rawData = message.data; // Expected: "R03_S2_ITM430"
        this.logCommand('IN', 'SCAN_DATA', rawData);

        try {
          // Parse format: RackID_ShelfID_ItemID
          const parts = rawData.split('_');
          if (parts.length >= 3) {
            const rackId = parts[0];
            const shelfId = parts[1];
            const itemId = parts[2]; // e.g., ITM430

            // Determine category based on Item ID prefix or other logic
            let category: 'inventory' | 'maintenance' | 'hazard' = 'inventory';
            if (itemId.startsWith('HAZ')) category = 'hazard';
            else if (itemId.startsWith('MNT')) category = 'maintenance';

            const scanEntry = {
              rawData: rawData,           // Full raw data
              rackId: rackId,             // e.g., "R02"
              shelfId: shelfId,           // e.g., "S2"
              itemId: itemId,             // e.g., "ITM430"
              content: `${shelfId} - ${itemId}`, // Legacy field
              category: category,
              timestamp: new Date().toISOString()
            };

            // Save to Firebase
            await saveScanLog(scanEntry);
            console.log(`📦 Processed Scan: ${rackId} -> ${itemId} (Saved to DB)`);
          } else {
            console.warn('Invalid scan data format:', rawData);
          }
        } catch (e) {
          console.error('Error processing scan data:', e);
        }
      });
      this.rosTopics.set('scanData', scanDataTopic);
    }

  }

  private logCommand(direction: 'OUT' | 'IN', command: string, payload?: any) {
    const entry = {
      id: Math.random().toString(36).substring(7),
      timestamp: Date.now(),
      direction,
      command,
      payload
    };
    this.state.commandLog = [entry, ...this.state.commandLog].slice(0, 50); // Keep last 50
    this.notify();
  }

  public async sendCommand(command: string, payload?: any): Promise<void> {
    this.logCommand('OUT', command, payload);
    if (this.mode === 'real' && this.ros && this.settings) {
      this.sendRosCommand(command, payload);
    } else {
      this.sendSimulationCommand(command, payload);
    }
  }

  public sendVelocityCommand(linearX: number, linearY: number, angular: number): void {
    // Linear X: m/s (forward/backward)
    // Linear Y: m/s (left/right - strafing)
    // Angular: rad/s (left/right rotation)

    if (this.mode === 'real' && this.ros && this.settings) {
      const cmdVel = new ROSLIB.Topic({
        ros: this.ros,
        name: this.settings.topics.command,
        messageType: 'geometry_msgs/Twist'
      });

      // ROSLIB.Topic.publish accepts a plain JSON object matching the message type
      const twist = {
        linear: { x: linearX, y: linearY, z: 0 },
        angular: { x: 0, y: 0, z: angular }
      };

      cmdVel.publish(twist);
      this.state.status = (linearX !== 0 || linearY !== 0 || angular !== 0) ? RobotStatus.MOVING : RobotStatus.IDLE;
      this.state.velocity = Math.sqrt(linearX * linearX + linearY * linearY); // Magnitude
    } else {
      // Simulation Physics
      // We'll update the state directly in the simulation loop based on these values
      // But we need to store them somewhere. Let's add a currentVelocity target to the class.
      this.simulationVelocity = { linearX, linearY, angular };
      this.state.status = (linearX !== 0 || linearY !== 0 || angular !== 0) ? RobotStatus.MOVING : RobotStatus.IDLE;
      this.state.velocity = Math.sqrt(linearX * linearX + linearY * linearY);
    }
    this.notify();
  }

  // Simulation velocity state
  private simulationVelocity = { linearX: 0, linearY: 0, angular: 0 };

  private sendRosCommand(command: string, payload?: any): void {
    if (!this.ros || !this.settings) return;

    switch (command) {
      case 'GOTO':
        if (payload && typeof payload.x === 'number' && typeof payload.y === 'number') {
          const goalTopic = new ROSLIB.Topic({
            ros: this.ros,
            name: '/goal_pose',
            messageType: 'geometry_msgs/PoseStamped'
          });
          const goalMsg = {
            header: { stamp: { secs: 0, nsecs: 0 }, frame_id: 'map' },
            pose: {
              position: {
                x: payload.x / 100,
                y: payload.y / 100, // Standard Cartesian, no inversion needed
                z: 0
              },
              orientation: { x: 0, y: 0, z: 0, w: 1 }
            }
          };
          goalTopic.publish(goalMsg);
          this.state.currentTask = `Moving to (${payload.x}, ${payload.y})`;
          this.state.status = RobotStatus.MOVING;
        }
        break;

      case 'START_AUTO_SCAN':
        const startTopic = new ROSLIB.Topic({
          ros: this.ros,
          name: this.settings.topics.autoScan || '/auto_scan',
          messageType: 'std_msgs/String'
        });
        startTopic.publish({ data: 'START' });
        this.state.autoMode = true;
        this.state.status = RobotStatus.MOVING;
        break;

      case 'STOP_AUTO_SCAN':
        const stopTopic = new ROSLIB.Topic({
          ros: this.ros,
          name: this.settings.topics.autoScan || '/auto_scan',
          messageType: 'std_msgs/String'
        });
        stopTopic.publish({ data: 'STOP' });
        this.state.autoMode = false;
        this.state.status = RobotStatus.IDLE;
        break;

      case 'STOP':
      case 'ESTOP':
        // ... existing stop logic ...
        break;
    }
    this.notify();
  }

  public sendRestartCommand(): void {
    if (this.mode === 'real' && this.ros && this.settings) {
      const restartTopic = new ROSLIB.Topic({
        ros: this.ros,
        name: this.settings.topics.restart || '/restart',
        messageType: 'std_msgs/Bool'
      });
      restartTopic.publish({ data: true });
    }
    this.logCommand('OUT', 'RESTART');
  }

  public sendZScanCommand(height: number): void {
    if (this.mode === 'real' && this.ros && this.settings) {
      const zscanTopic = new ROSLIB.Topic({
        ros: this.ros,
        name: this.settings.topics.zscan || '/zscan_manual',
        messageType: 'std_msgs/Float32'
      });
      zscanTopic.publish({ data: height });
    }
    this.logCommand('OUT', 'Z-SCAN', { height });
  }

  public sendScanRackCommand(racks: number[]): void {
    if (this.mode === 'real' && this.ros && this.settings) {
      const scanRackTopic = new ROSLIB.Topic({
        ros: this.ros,
        name: this.settings.topics.scanRack || '/scan_rack',
        messageType: 'std_msgs/Int32MultiArray'
      });
      // std_msgs/Int32MultiArray structure: { layout: ..., data: [...] }
      // roslib usually handles the layout if omitted, or we just send data.
      // Let's try sending just data first, or full structure if needed.
      // Standard structure: { data: [1, 2, 3] }
      scanRackTopic.publish({ data: racks });
    }
    this.logCommand('OUT', 'SCAN_RACK', { racks });
  }

  public sendRestartLocalisationCommand(x: number, y: number, theta: number): void {
    if (this.mode === 'real' && this.ros && this.settings) {
      const topic = new ROSLIB.Topic({
        ros: this.ros,
        name: this.settings.topics.restartLocalisation || '/restart_localisation',
        messageType: 'std_msgs/Float32MultiArray'
      });
      // Float32MultiArray: { layout: ..., data: [x, y, theta] }
      topic.publish({ data: [x, y, theta] });
    }
    this.logCommand('OUT', 'RESTART_LOC', { x, y, theta });
  }


  public publishMapData(scanPoints: ScanPoint[], pathSegments: PathSegment[], racks?: any[]): void {
    if (this.mode === 'real' && this.ros) {
      // Publish Scan Points (Convert cm to meters and add start/stop markers)
      const scanTopic = new ROSLIB.Topic({
        ros: this.ros,
        name: '/map/scan_points',
        messageType: 'std_msgs/Float32MultiArray'
      });
      // Flatten the array for Float32MultiArray
      // Format: [x1_m, y1_m, is_start, is_stop, x2_m, y2_m, is_start, is_stop, ...]
      const flatScanPoints = scanPoints.flatMap((p, i) => [
        p.x / 100, // Convert cm to meters
        p.y / 100, // Convert cm to meters
        i === 0 ? 1 : 0, // First point is start
        i === scanPoints.length - 1 ? 1 : 0 // Last point is stop
      ]);
      scanTopic.publish({
        layout: { dim: [], data_offset: 0 },
        data: flatScanPoints
      });

      // Publish Path Segments (Convert cm to meters)
      const pathTopic = new ROSLIB.Topic({
        ros: this.ros,
        name: '/map/path_segments',
        messageType: 'std_msgs/Float32MultiArray'
      });
      const flatPathSegments = pathSegments.flatMap(s => [
        s.x1 / 100, // Convert cm to meters
        s.y1 / 100, // Convert cm to meters
        s.x2 / 100, // Convert cm to meters
        s.y2 / 100, // Convert cm to meters
        s.direction
      ]);
      pathTopic.publish({
        layout: { dim: [], data_offset: 0 },
        data: flatPathSegments
      });

      // Publish Rack Data (Convert cm to meters)
      if (racks && racks.length > 0) {
        const rackTopic = new ROSLIB.Topic({
          ros: this.ros,
          name: this.settings?.topics.rackData || '/map/racks', // Use configured topic or default
          messageType: 'std_msgs/Float32MultiArray'
        });
        // Format: [cx_m, cy_m, width_m, height_m, ...next_rack]
        const flatRacks = racks.flatMap(r => [
          r.position.x / 100, // Convert cm to meters
          r.position.y / 100, // Convert cm to meters
          r.width / 100, // Convert cm to meters
          r.height / 100 // Convert cm to meters
        ]);
        rackTopic.publish({
          layout: { dim: [], data_offset: 0 },
          data: flatRacks
        });
      }

      console.log('🗺️ Map Data Published to ROS (in meters)');
    }
    this.logCommand('OUT', 'PUBLISH_MAP', {
      scanPointsCount: scanPoints.length,
      pathSegmentsCount: pathSegments.length,
      racksCount: racks?.length || 0
    });
  }

  public toggleAutoScan(): void {
    const newState = !this.state.autoMode;
    this.state.autoMode = newState;

    if (this.mode === 'real' && this.ros && this.settings) {
      const autoScanTopic = new ROSLIB.Topic({
        ros: this.ros,
        name: this.settings.topics.autoScan,
        messageType: 'std_msgs/String'
      });
      // User requested "yes" or "no" string
      autoScanTopic.publish({ data: newState ? "yes" : "no" });
    }

    if (newState) {
      this.state.status = RobotStatus.MOVING;
      this.state.currentTask = "Starting Auto Scan...";
      this.autoScanIndex = 0;
      this.processAutoScanStep();
    } else {
      this.state.status = RobotStatus.IDLE;
      this.state.currentTask = null;
    }
    this.notify();
  }

  private sendSimulationCommand(command: string, payload?: any): void {
    switch (command) {
      case 'START_AUTO_SCAN':
        this.state.autoMode = true;
        this.autoScanIndex = 0;
        localStorage.setItem('sim_auto_mode', 'true');
        this.processAutoScanStep();
        break;
      case 'STOP_AUTO_SCAN':
        this.state.autoMode = false;
        this.state.status = RobotStatus.IDLE;
        this.target = null;
        localStorage.setItem('sim_auto_mode', 'false');
        break;
      case 'GOTO':
        if (payload) {
          this.target = payload;
          this.state.status = RobotStatus.MOVING;
          this.state.currentTask = "Navigating to Target";
          // If manual move, pause auto scan?
          // User said "click to go functionality should work even when auto scanning is off"
          // If on, it might interrupt. For now, we let it override.
        }
        break;
      case 'STOP':
        this.state.status = RobotStatus.IDLE;
        this.target = null;
        break;
    }
    this.notify();
  }

  private processAutoScanStep() {
    if (!this.state.autoMode || !this.settings) return;

    const waypoints = this.settings.rackWaypoints;
    if (this.autoScanIndex < waypoints.length) {
      // Move to next rack
      const wp = waypoints[this.autoScanIndex];
      this.target = wp.scanPosition;
      this.state.status = RobotStatus.MOVING;
      this.state.currentTask = `Auto Scan: Moving to ${wp.rackId}`;
    } else {
      // Done with all racks, return to dock
      this.target = { x: 250, y: -200 }; // Dock position
      this.state.status = RobotStatus.MOVING;
      this.state.currentTask = "Auto Scan: Returning to Dock";
    }
  }

  private async performScan(rackId?: string) {
    try {
      const id = rackId || `R-${Math.floor(Math.random() * 100)}`;
      const types: ('inventory' | 'maintenance' | 'hazard')[] = ['inventory', 'inventory', 'inventory', 'maintenance', 'hazard'];
      const category = types[Math.floor(Math.random() * types.length)];
      const itemId = category === 'inventory' ? `ITM${Math.floor(Math.random() * 1000)}` :
        category === 'hazard' ? 'HAZ001' : 'MNT001';
      const shelfId = `S${Math.floor(Math.random() * 5) + 1}`;
      const rawData = `${id}_${shelfId}_${itemId}`;

      await saveScanLog({
        rawData: rawData,
        rackId: id,
        shelfId: shelfId,
        itemId: itemId,
        timestamp: new Date().toISOString(),
        content: `${shelfId} - ${itemId}`,
        category
      });
    } catch (error) {
      console.error('Failed to save scan:', error);
    }
  }

  private startSystemLoop() {
    if (this.systemInterval) return;
    this.systemInterval = window.setInterval(() => {
      if (!this.settings?.schedule.enabled) return;

      const now = Date.now();
      // Check if it's time to scan
      if (now >= this.settings.schedule.nextScanTime) {
        console.log("⏰ Scheduled scan triggering...");
        this.sendCommand('START_AUTO_SCAN');

        // Update next scan time
        this.settings.schedule.lastScanTime = now;
        this.settings.schedule.nextScanTime = now + (this.settings.schedule.intervalMinutes * 60 * 1000);

        // Ideally we would save this back to storage, but we rely on App to persist settings on change.
        // Since we modified settings in place, we should probably notify App? 
        // For now, the loop handles the trigger.
      }
    }, 1000); // Check every second
  }

  private startSimulationLoop() {
    if (this.simulationInterval) return;

    this.simulationInterval = window.setInterval(() => {
      if (this.mode !== 'simulation') return;

      // Battery Logic
      if (this.state.status === RobotStatus.MOVING || this.state.status === RobotStatus.SCANNING) {
        this.state.batteryLevel = Math.max(0, this.state.batteryLevel - 0.05);
      } else if (this.state.position.x > 200 && this.state.position.y < -150) {
        this.state.batteryLevel = Math.min(100, this.state.batteryLevel + 0.2);
        if (this.state.status === RobotStatus.IDLE) this.state.status = RobotStatus.CHARGING;
      }

      // Movement Logic
      if (this.state.status === RobotStatus.MOVING) {
        if (this.target) {
          // ... existing target logic ...
          const dx = this.target.x - this.state.position.x;
          const dy = this.target.y - this.state.position.y;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < 5) {
            this.state.position = this.target;
            this.target = null;

            // Arrived logic
            if (this.state.autoMode) {
              if (this.autoScanIndex < (this.settings?.rackWaypoints.length || 0)) {
                // Arrived at rack
                this.state.status = RobotStatus.SCANNING;
                this.state.currentTask = "Scanning...";
                this.performScan(this.settings?.rackWaypoints[this.autoScanIndex].rackId);

                setTimeout(() => {
                  this.autoScanIndex++;
                  this.processAutoScanStep();
                }, 2000); // Scan takes 2s
              } else {
                // Arrived at Dock
                this.state.status = RobotStatus.CHARGING;
                this.state.currentTask = "Docked (Waiting for next schedule)";
                this.state.autoMode = false; // Round complete
              }
            } else {
              this.state.status = RobotStatus.IDLE;
              this.state.currentTask = null;
            }
          } else {
            const speed = 3;
            const angle = Math.atan2(dy, dx);
            this.state.position.x += Math.cos(angle) * speed;
            this.state.position.y += Math.sin(angle) * speed;
            this.state.rotation = (angle * 180) / Math.PI;
          }
        } else if (this.simulationVelocity.linearX !== 0 || this.simulationVelocity.linearY !== 0 || this.simulationVelocity.angular !== 0) {
          // Manual Velocity Control
          // Update rotation
          const dt = 0.05;
          const rotChangeRad = this.simulationVelocity.angular * dt;
          const rotChangeDeg = rotChangeRad * (180 / Math.PI);
          this.state.rotation += rotChangeDeg;

          // Update position (Omnidirectional)
          // Robot Frame: X is forward, Y is left.
          // We need to rotate this vector by the robot's global rotation to get global displacement.
          const vx = this.simulationVelocity.linearX;
          const vy = this.simulationVelocity.linearY;

          // Global Rotation in Radians
          const theta = this.state.rotation * (Math.PI / 180);

          // Rotate vector (vx, vy) by theta
          // Global dx = vx * cos(theta) - vy * sin(theta)
          // Global dy = vx * sin(theta) + vy * cos(theta)
          // Note: Standard rotation matrix. 
          // Wait, if Y is Left (positive), and we rotate CCW (positive theta):
          // Forward (vx=1, vy=0) -> dx=cos, dy=sin. Correct.
          // Left (vx=0, vy=1) -> dx=-sin, dy=cos. Correct.

          const globalVx = vx * Math.cos(theta) - vy * Math.sin(theta);
          const globalVy = vx * Math.sin(theta) + vy * Math.cos(theta);

          // Scale by time and pixels/meter (100)
          this.state.position.x += globalVx * dt * 100;
          this.state.position.y += globalVy * dt * 100;
        }
      }

      this.state.wifiSignal = Math.max(50, Math.min(100, this.state.wifiSignal + (Math.random() * 4 - 2)));
      this.notify();
    }, 50);
  }
}

export const robotService = new RobotService();