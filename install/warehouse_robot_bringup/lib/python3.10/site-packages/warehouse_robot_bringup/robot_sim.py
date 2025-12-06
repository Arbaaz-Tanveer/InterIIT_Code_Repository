#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import String, Float32MultiArray, MultiArrayDimension
import pygame
import math
import numpy as np
from typing import List
import json
import os

# Constants for the simulation
WHEEL_DIAMETER = 10  # cm
BOT_SIZE = 50  # cm
MIN_SEPARATION_DISTANCE = BOT_SIZE/2 + 10
TICKS_PER_REVOLUTION = 1750
BOT_MASS = 20  # kg
WHEEL_DISTANCE = BOT_SIZE / math.sqrt(2)
MOMENT_OF_INERTIA = BOT_MASS * ((BOT_SIZE/100) ** 2) / 6
FPS = 40
MAX_MOTOR_FORCE = 20  # Newtons
KP = 0.1
KI = 0
KD = 0.0001
MAX_TICKS_PER_SECOND = 30000
TICKS_PER_METER = (100 * TICKS_PER_REVOLUTION) / (math.pi*WHEEL_DIAMETER)

class PIDController:
    def __init__(self, kp: float, ki: float, kd: float):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.prev_error = 0
        self.integral = 0

    def compute(self, target: float, current: float, dt: float) -> float:
        error = target - current
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error
        return output

class OmniwheelRobot:
    def __init__(self, team: str, robot_number: int, x: float, y: float, theta: float = 0, color: tuple = (255, 0, 0)):
        self.team = team
        self.robot_number = robot_number
        self.x = x
        self.y = y
        self.theta = theta
        self.color = color
        self.vx = 0
        self.vy = 0
        self.omega = 0
        self.target_vx = 0
        self.target_vy = 0
        self.target_omega = 0
        self.ax = 0
        self.ay = 0
        self.alpha = 0
        self.desired_ticks = [0, 0, 0, 0]
        self.achieved_ticks = [0, 0, 0, 0]
        self.current_wheel_velocities = [0, 0, 0, 0]
        self.pid_controllers = [PIDController(KP, KI, KD) for _ in range(4)]
        self.wheel_angles = [math.pi/4, 3*math.pi/4, 5*math.pi/4, 7*math.pi/4]
        self.motor_forces = [0, 0, 0, 0]
        self.target_velocities = [0, 0, 0, 0]

    def set_velocity(self, vx: float, vy: float, omega: float):
        root2 = math.sqrt(2)
        wheel_velocities = [(vx + vy)/root2 + omega, (-vx + vy)/root2 + omega, (-vx - vy)/root2 + omega, (vx - vy)/root2 + omega]
        self.add_target_ticks(wheel_velocities)

    def add_target_ticks(self, ticks_per_second: List[float]):
        self.target_velocities = ticks_per_second
        for i in range(4):
            self.desired_ticks[i] += ticks_per_second[i] / FPS

    def update(self, dt: float):
        self.motor_forces = []
        for i in range(4):
            pid_output = self.pid_controllers[i].compute(self.target_velocities[i], self.current_wheel_velocities[i], dt)
            force = np.clip(pid_output*MAX_MOTOR_FORCE/255, -MAX_MOTOR_FORCE, MAX_MOTOR_FORCE)
            self.motor_forces.append(force)

        fx = fy = torque = 0
        for i, force in enumerate(self.motor_forces):
            angle = self.wheel_angles[i]
            fx += force * math.cos(angle)
            fy += force * math.sin(angle)
            torque += force * WHEEL_DISTANCE/100

        self.ax = 100*fx / BOT_MASS
        self.ay = 100*fy / BOT_MASS
        self.alpha = torque / MOMENT_OF_INERTIA

        self.vx += self.ax * dt
        self.vy += self.ay * dt
        self.omega += self.alpha * dt

        world_vx = self.vx * math.cos(self.theta) - self.vy * math.sin(self.theta)
        world_vy = self.vx * math.sin(self.theta) + self.vy * math.cos(self.theta)

        self.x += world_vx * dt
        self.y += world_vy * dt
        self.theta += self.omega * dt

        wheel_radius = WHEEL_DIAMETER / 2
        for i in range(4):
            angle = self.wheel_angles[i]
            linear_velocity = (self.vx * math.cos(angle) + self.vy * math.sin(angle) + self.omega * WHEEL_DISTANCE)
            self.current_wheel_velocities[i] = (linear_velocity * TICKS_PER_REVOLUTION / (2 * math.pi * wheel_radius))
            self.achieved_ticks[i] += self.current_wheel_velocities[i] * dt

        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))

    def draw(self, screen: pygame.Surface, scale: float, offset_x: int, offset_y: int):
        """Draw the robot on the screen"""
        px = int(self.x * scale) + offset_x
        py = int(self.y * scale) + offset_y
        size = int(BOT_SIZE * scale)

        if self.team == 'b':
            pygame.draw.circle(screen, self.color, (px, py), size // 2)
            font = pygame.font.Font(None, int(size/1.5))
            number_text = font.render(str(self.robot_number), True, (255, 255, 255))
            text_rect = number_text.get_rect(center=(px, py))
            screen.blit(number_text, text_rect)
            return

        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(surface, (*self.color, 128), (0, 0, size, size))
        pygame.draw.circle(surface, (255,255,255), (size, size/2), size/4, 0)

        font = pygame.font.Font(None, int(size/1.5))
        number_text = font.render(str(self.robot_number), True, (255, 255, 255))
        text_rect = number_text.get_rect(center=(size/2, size/2))
        surface.blit(number_text, text_rect)

        wheel_size = int(WHEEL_DIAMETER * scale)
        for i, angle in enumerate(self.wheel_angles):
            wheel_x = size/2 + WHEEL_DISTANCE*scale*math.cos(angle)
            wheel_y = size/2 - WHEEL_DISTANCE*scale*math.sin(angle)
            velocity_ratio = self.target_velocities[i] / MAX_TICKS_PER_SECOND
            if velocity_ratio > 0: color = (255, 0, 0)
            elif velocity_ratio < 0: color = (0, 0, 255)
            else: color = (128, 128, 128)
            pygame.draw.circle(surface, (0,0,0), (int(wheel_x), int(wheel_y)), wheel_size)

        rotated = pygame.transform.rotate(surface, -math.degrees(self.theta))
        screen.blit(rotated, (px - rotated.get_width()/2, py - rotated.get_height()/2))

class ROS2RobotSimulation(Node):
    def __init__(self):
        super().__init__('robot_simulation')

        # CONFIGURATION
        num_our_team = 1
        num_opp_team = 2 
        field_dims_m = [7, 7] 
        
        self.obstacle_noise_base_meters = 0.00
        self.obstacle_noise_per_meter = 0.00

        config_path = 'src/baseStation_pkg/baseStation_pkg/config.json'
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.obstacle_noise_base_meters = float(config.get('camera_noise_base_meters', 0.00))
                self.obstacle_noise_per_meter = float(config.get('camera_noise_per_meter', 0.00))
        except:
            pass 

        self.field_width = field_dims_m[0] * 100
        self.field_height = field_dims_m[1] * 100
        self.get_logger().info(f"Field dimensions set to {self.field_width/100}m x {self.field_height/100}m.")
        
        pygame.init()
        fixed_width = 800
        
        if self.field_width > 0:
            self.scale = fixed_width / self.field_width
            dynamic_height = int(self.scale * self.field_height)
        else:
            self.scale = 1
            dynamic_height = 800

        self.width = fixed_width
        self.height = dynamic_height

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("ROS2 Robot Simulation (7x7m) - Pose/Obstacle Fix")
        self.clock = pygame.time.Clock()

        self.robots = []
        self.robot_namespaces = []
        self.cmd_vel_subs = []
        self.state_pubs = []
        self.odom_pubs = []
        self.pose_pubs = []
        self.obstacle_pubs = []

        # Spawn Red Robot (o1)
        for i in range(num_our_team):
            namespace = f'o{i+1}'
            self.robot_namespaces.append(namespace)
            x = self.field_width / 2
            y = self.field_height / 2
            robot = OmniwheelRobot(team='o', robot_number=(i + 1), x=x, y=y, color=(255, 0, 0))
            self.robots.append(robot)

        # Spawn Blue Robots (b1, b2) 
        for i in range(num_opp_team):
            namespace = f'b{i+1}'
            self.robot_namespaces.append(namespace)
            if i == 0:
                x = self.field_width * 0.8
                y = self.field_height * 0.2
            else:
                x = self.field_width * 0.2
                y = self.field_height * 0.8
            robot = OmniwheelRobot(team='b', robot_number=(i + 1), x=x, y=y, color=(0, 0, 255))
            self.robots.append(robot)

        for i, robot in enumerate(self.robots):
            namespace = self.robot_namespaces[i]
            
            # --- TOPIC NAMING LOGIC ---
            if namespace == 'o1':
                pose_topic = '/robot_pose'
                obs_topic = '/obstacles'
            else:
                pose_topic = f'{namespace}/pose'
                obs_topic = f'{namespace}_obstacles'
            
            self.cmd_vel_subs.append(self.create_subscription(Twist, f'{namespace}/cmd_vel', lambda msg, idx=i: self.cmd_vel_callback(msg, idx), 10))
            self.odom_pubs.append(self.create_publisher(Odometry, f'{namespace}_odom', 10))
            self.state_pubs.append(self.create_publisher(Float32MultiArray, f'{namespace}_data', 10))
            
            # Use computed topic names
            self.obstacle_pubs.append(self.create_publisher(Float32MultiArray, obs_topic, 10))
            self.pose_pubs.append(self.create_publisher(PoseStamped, pose_topic, 10))

        self.status_pub = self.create_publisher(String, 'simulation/status', 10)
        self.create_timer(1.0/FPS, self.update_and_render)
    
    def handle_robot_collisions(self):
        num_robots = len(self.robots)
        for i in range(num_robots):
            for j in range(i + 1, num_robots):
                robot_a = self.robots[i]
                robot_b = self.robots[j]

                dx = robot_b.x - robot_a.x
                dy = robot_b.y - robot_a.y
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < MIN_SEPARATION_DISTANCE:
                    overlap = MIN_SEPARATION_DISTANCE - dist
                    nx = dx / dist if dist != 0 else 1
                    ny = dy / dist if dist != 0 else 0
                    
                    robot_a.x -= overlap / 2 * nx
                    robot_a.y -= overlap / 2 * ny
                    robot_b.x += overlap / 2 * nx
                    robot_b.y += overlap / 2 * ny

                    vel_a_n = robot_a.vx * nx + robot_a.vy * ny
                    vel_b_n = robot_b.vx * nx + robot_b.vy * ny

                    if vel_a_n > 0:
                        robot_a.vx -= vel_a_n * nx
                        robot_a.vy -= vel_a_n * ny

                    if vel_b_n < 0:
                        robot_b.vx -= vel_b_n * nx
                        robot_b.vy -= vel_b_n * ny

    def publish_obstacles(self, robot_index: int):
        obstacles_msg = Float32MultiArray()
        obstacle_data = []
        sensing_robot = self.robots[robot_index]

        for i, robot in enumerate(self.robots): 
            if i != robot_index:
                dx_cm = robot.x - sensing_robot.x
                dy_cm = robot.y - sensing_robot.y
                distance_cm = math.sqrt(dx_cm**2 + dy_cm**2)
                distance_m = distance_cm / 100.0
                
                sigma = self.obstacle_noise_base_meters + (distance_m * self.obstacle_noise_per_meter)
                noise_x = np.random.normal(0.0, sigma)
                noise_y = np.random.normal(0.0, sigma)

                true_x_pos = (robot.x - self.field_width/2) / 100.0
                true_y_pos = (self.field_height/2 - robot.y) / 100.0

                noisy_x_pos = true_x_pos + noise_x
                noisy_y_pos = true_y_pos + noise_y

                obstacle_data.extend([noisy_x_pos, noisy_y_pos])
        
        msg_data = [float(len(obstacle_data) // 2)] + obstacle_data
        obstacles_msg.layout.dim = [MultiArrayDimension(label="obstacles", size=len(msg_data), stride=len(msg_data))]
        obstacles_msg.data = msg_data
        self.obstacle_pubs[robot_index].publish(obstacles_msg)

    def update_and_render(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                rclpy.shutdown()
                return

        dt = 1.0/FPS
        for i, robot in enumerate(self.robots):
            robot.set_velocity(robot.target_vx, robot.target_vy, robot.target_omega)
            robot.update(dt)

        self.handle_robot_collisions()

        for i, robot in enumerate(self.robots):
            self.publish_robot_state(robot, i)
            self.publish_obstacles(i)

        status_msg = String(data="Simulation running")
        self.status_pub.publish(status_msg)

        self.screen.fill((0, 100, 0)) 

        field_width_px = int(self.field_width * self.scale)
        field_height_px = int(self.field_height * self.scale)
        start_x = (self.width - field_width_px) // 2 
        start_y = (self.height - field_height_px) // 2 

        self.draw_field(start_x, start_y, field_width_px, field_height_px)
        for robot in self.robots:
            robot.draw(self.screen, self.scale, start_x, start_y)
        
        # Draw HUD: Speed and Position of Red Bot (o1)
        if len(self.robots) > 0:
            red_bot = self.robots[0] 
            pos_x_m = (red_bot.x - self.field_width/2) / 100.0
            pos_y_m = (self.field_height/2 - red_bot.y) / 100.0
            speed_mps = math.sqrt(red_bot.vx**2 + red_bot.vy**2) / 100.0

            font = pygame.font.Font(None, 36)
            text_surf = font.render(f"Pos: ({pos_x_m:.2f}m, {pos_y_m:.2f}m)  Speed: {speed_mps:.2f} m/s", True, (255, 255, 255))
            self.screen.blit(text_surf, (10, 10))

        pygame.display.flip()
        self.clock.tick(FPS)

    def draw_field(self, start_x, start_y, field_width_px, field_height_px):
        pygame.draw.rect(self.screen, (255, 255, 255), (start_x, start_y, field_width_px, field_height_px), 2)

    def cmd_vel_callback(self, msg: Twist, robot_index: int):
        theta = self.robots[robot_index].theta
        global_vx = msg.linear.x * TICKS_PER_METER
        global_vy = -msg.linear.y * TICKS_PER_METER
        local_vx = global_vx * math.cos(theta) + global_vy * math.sin(theta)
        local_vy = -global_vx * math.sin(theta) + global_vy * math.cos(theta)
        omega = -msg.angular.z * WHEEL_DISTANCE * TICKS_PER_METER/100
        self.robots[robot_index].target_vx = local_vx
        self.robots[robot_index].target_vy = local_vy
        self.robots[robot_index].target_omega = omega

    def publish_robot_state(self, robot: OmniwheelRobot, robot_index: int):
        current_time = self.get_clock().now().to_msg()
        
        # --- 1. COORDINATE CONVERSION (Sim -> ROS Centered) ---
        ros_x = (robot.x - self.field_width/2) / 100.0
        ros_y = (self.field_height/2 - robot.y) / 100.0 
        ros_theta = -robot.theta 

        # --- 2. PUBLISH POSE STAMPED ---
        pose_msg = PoseStamped()
        pose_msg.header.stamp = current_time
        pose_msg.header.frame_id = "map"
        
        pose_msg.pose.position.x = ros_x
        pose_msg.pose.position.y = ros_y
        pose_msg.pose.position.z = 0.0

        pose_msg.pose.orientation.z = math.sin(ros_theta / 2.0)
        pose_msg.pose.orientation.w = math.cos(ros_theta / 2.0)
        
        self.pose_pubs[robot_index].publish(pose_msg)

        # --- 3. PUBLISH ODOM ---
        odom = Odometry()
        odom.header.frame_id = "odom"
        odom.child_frame_id = f"{self.robot_namespaces[robot_index]}_base_link"
        odom.header.stamp = current_time
        odom.pose.pose.position.x = ros_x 
        odom.pose.pose.position.y = ros_y
        odom.pose.pose.orientation.z = pose_msg.pose.orientation.z
        odom.pose.pose.orientation.w = pose_msg.pose.orientation.w
        odom.twist.twist.linear.x = robot.vx / 100.0
        odom.twist.twist.linear.y = -robot.vy / 100.0
        odom.twist.twist.angular.z = -robot.omega
        self.odom_pubs[robot_index].publish(odom)

        # --- 4. PUBLISH CUSTOM STATE ---
        state_msg = Float32MultiArray()
        state_msg.layout.dim = [MultiArrayDimension(label="state", size=7, stride=7)]
        state_msg.data = [
            ros_x,
            ros_y,
            ros_theta,
            -robot.achieved_ticks[0],
            -robot.achieved_ticks[3],
            -robot.achieved_ticks[1],
            -robot.achieved_ticks[2]
        ]
        self.state_pubs[robot_index].publish(state_msg)

def main(args=None):
    rclpy.init(args=args)
    sim_node = ROS2RobotSimulation()
    try:
        rclpy.spin(sim_node)
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()
        sim_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()