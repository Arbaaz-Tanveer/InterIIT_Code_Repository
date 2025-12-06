#include <acado_toolkit.hpp>
#include <acado_gnuplot.hpp>
#include <iostream>
#include <thread>
#include <mutex>
#include <vector>
#include <chrono>
#include <cmath>
#include <atomic>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float32_multi_array.hpp"
#include "std_msgs/msg/bool.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp" // Added standard Pose header

USING_NAMESPACE_ACADO

// --------------------- HELPER FUNCTIONS ---------------------
inline double normalize_angle(double angle) {
    while (angle > M_PI) angle -= 2.0 * M_PI;
    while (angle < -M_PI) angle += 2.0 * M_PI;
    return angle;
}

inline double angle_difference(double target, double current) {
    double diff = target - current;
    return normalize_angle(diff);
}

// Helper to convert Quaternion to Yaw (Theta)
inline double get_yaw_from_quat(double x, double y, double z, double w) {
    // yaw (z-axis rotation)
    double siny_cosp = 2.0 * (w * z + x * y);
    double cosy_cosp = 1.0 - 2.0 * (y * y + z * z);
    return std::atan2(siny_cosp, cosy_cosp);
}

// --------------------- GLOBAL VARIABLES ---------------------
double current_x = 0.0, current_y = 0.0, current_theta = 0.0;
// Note: PoseStamped only gives Position. We must estimate Velocity 
// from the previous MPC step (Open Loop) or use an Odometry message instead.
double current_vx = 0.0, current_vy = 0.0, current_omega = 0.0; 

double next_x = 0.0, next_y = 0.0, next_theta = 0.0;
double next_vx = 0.0, next_vy = 0.0, next_omega = 0.0;

// FLAGS
std::atomic<bool> is_slow_mode(false);
std::atomic<bool> is_motion_active(true); 

// ========== ROBOT PHYSICAL PARAMETERS ==========
const double ROBOT_MASS = 25.0;            
const double ROBOT_INERTIA = 1.56;          
const double WHEEL_RADIUS = 0.05;          
const double ROBOT_RADIUS = 0.25;           

const double MAX_WHEEL_TORQUE = 1;         
const double MAX_WHEEL_VEL = (100/60)*6.28; 
const double MAX_WHEEL_FORCE = MAX_WHEEL_TORQUE / WHEEL_RADIUS;

// ========== MPC PARAMETERS ==========
const double NORMAL_HORIZON = 1.5;
const int NORMAL_N = 8;
const double SLOW_MODE_HORIZON = 1.5;
const int SLOW_MODE_N = 8;

std::vector<std::array<double, 3>> path_points;

DifferentialState x, y, theta, vx, vy, omega;
Control ax, ay, alpha;
DifferentialEquation f;

// --------------------- NODE CLASS ---------------------
class MyRobotNode : public rclcpp::Node {
public:
    MyRobotNode() : Node("my_robot_node") {
        // Publishers
        global_cmd_vel_publisher = this->create_publisher<geometry_msgs::msg::Twist>("o1/cmd_vel", 10);
        local_cmd_vel_publisher = this->create_publisher<geometry_msgs::msg::Twist>("local_cmd_vel", 10);

        // Subscribers
        // CHANGED: Listens to PoseStamped instead of Float32MultiArray
        pose_subscription = this->create_subscription<geometry_msgs::msg::PoseStamped>(
            "/robot_pose", 10, std::bind(&MyRobotNode::mpc_callback, this, std::placeholders::_1));
        
        target_subscription = this->create_subscription<std_msgs::msg::Float32MultiArray>(
            "target_pos", 10, std::bind(&MyRobotNode::update_target_callback, this, std::placeholders::_1));
        
        slow_mode_subscription = this->create_subscription<std_msgs::msg::Bool>(
            "slow_mode_flag", 10, std::bind(&MyRobotNode::slow_mode_callback, this, std::placeholders::_1));

        motion_active_subscription = this->create_subscription<std_msgs::msg::Bool>(
            "motion_active", 10, std::bind(&MyRobotNode::motion_active_callback, this, std::placeholders::_1));

        // ------------------- Define Dynamics -------------------
        f << dot(x) == vx;
        f << dot(y) == vy;
        f << dot(theta) == omega;
        f << dot(vx) == ax;
        f << dot(vy) == ay;
        f << dot(omega) == alpha;

        std::cout << "========== Robot MPC Node Started ==========" << std::endl;
        std::cout << "Listening on /robot_pose (GeometryMsgs::PoseStamped)" << std::endl;
    }

    void slow_mode_callback(const std_msgs::msg::Bool::SharedPtr msg) {
        is_slow_mode = msg->data;
        RCLCPP_INFO(this->get_logger(), "🐢 Slow mode: %s", is_slow_mode ? "ENABLED" : "DISABLED");
    }

    void motion_active_callback(const std_msgs::msg::Bool::SharedPtr msg) {
        is_motion_active = msg->data;
    }

    // ----------------------------------------------------------
    //             MPC LOGIC (Triggered by Pose Update)
    // ----------------------------------------------------------
    void mpc_callback(const geometry_msgs::msg::PoseStamped::SharedPtr msg) {
        // 1. EXTRACT STATE FROM POSE STAMPED
        current_x = msg->pose.position.x;
        current_y = msg->pose.position.y;
        
        // Convert Quaternion to Theta (Yaw)
        current_theta = normalize_angle(get_yaw_from_quat(
            msg->pose.orientation.x,
            msg->pose.orientation.y,
            msg->pose.orientation.z,
            msg->pose.orientation.w
        ));

        // WARNING: PoseStamped does not contain velocity. 
        // We assume current velocity matches the previous MPC prediction.
        // For better results, use nav_msgs/Odometry which has both Pose and Twist.
        current_vx = next_vx;
        current_vy = next_vy;
        current_omega = next_omega;

        // 2. Setup MPC based on Mode
        int N = is_slow_mode ? SLOW_MODE_N : NORMAL_N;
        double horizon = is_slow_mode ? SLOW_MODE_HORIZON : NORMAL_HORIZON;

        OCP ocp(0.0, horizon, N);

        Function h; h << x << y;
        DMatrix W(2, 2); W.setAll(0.0);
        W(0,0) = is_slow_mode ? 5000.0 : 5000;
        W(1,1) = is_slow_mode ? 5000.0 : 5000;

        Function hN; hN << x << y << sin(theta) << cos(theta);
        DMatrix WN(4, 4); WN.setAll(0.0);
        WN(0,0) = 1500.0; WN(1,1) = 1500.0; 
        WN(2,2) = 5000.0; WN(3,3) = 5000.0;

        // 3. Trajectory Reference
        VariablesGrid reference;
        reference.init(h.getDim(), Grid(0.0, horizon, N+1));

        if (path_points.empty()) {
            for (int i = 0; i <= N; ++i) {
                DVector r(h.getDim()); r.setAll(0.0);
                r(0) = current_x; r(1) = current_y;
                reference.setVector(i, r);
            }
        } else {
            for (int i = 0; i <= N; ++i) {
                DVector r(h.getDim()); r.setAll(0.0);
                size_t idx = std::min(i, (int)path_points.size() - 1);
                r(0) = path_points[idx][0]; r(1) = path_points[idx][1];
                reference.setVector(i, r);
            }
        }

        ocp.minimizeLSQ(W, h, reference);

        DVector refN(hN.getDim());
        double target_theta;
        if (path_points.empty()) {
            refN(0) = current_x; refN(1) = current_y;
            target_theta = current_theta;
        } else {
            refN(0) = path_points.back()[0]; refN(1) = path_points.back()[1];
            target_theta = normalize_angle(path_points.back()[2]);
        }
        refN(2) = sin(target_theta); refN(3) = cos(target_theta);
        ocp.minimizeLSQEndTerm(WN, hN, refN);

        // 4. Constraints & Dynamics
        const double m = ROBOT_MASS;
        const double I = ROBOT_INERTIA;
        const double r = WHEEL_RADIUS;
        const double L = ROBOT_RADIUS;
        const double sqrt2 = sqrt(2.0);
        const double F_max = MAX_WHEEL_FORCE;
        const double omega_max = MAX_WHEEL_VEL;

        Expression vx_local_exp =  cos(theta)*vx + sin(theta)*vy;
        Expression vy_local_exp = -sin(theta)*vx + cos(theta)*vy;
        Expression ax_local =  cos(theta)*ax + sin(theta)*ay;
        Expression ay_local = -sin(theta)*ax + cos(theta)*ay;

        Expression omega1 = (sqrt2/(2.0*r)) * (-vx_local_exp + vy_local_exp) + (L/r) * omega;
        Expression omega2 = (sqrt2/(2.0*r)) * ( vx_local_exp + vy_local_exp) + (L/r) * omega;
        Expression omega3 = (sqrt2/(2.0*r)) * ( vx_local_exp - vy_local_exp) + (L/r) * omega;
        Expression omega4 = (sqrt2/(2.0*r)) * (-vx_local_exp - vy_local_exp) + (L/r) * omega;

        Expression F1 = (m*sqrt2/4.0) * (-ax_local + ay_local) + (I/(4.0*L)) * alpha;
        Expression F2 = (m*sqrt2/4.0) * ( ax_local + ay_local) + (I/(4.0*L)) * alpha;
        Expression F3 = (m*sqrt2/4.0) * ( ax_local - ay_local) + (I/(4.0*L)) * alpha;
        Expression F4 = (m*sqrt2/4.0) * (-ax_local - ay_local) + (I/(4.0*L)) * alpha;

        ocp.subjectTo(f);
        ocp.subjectTo(-omega_max <= omega1 <= omega_max);
        ocp.subjectTo(-omega_max <= omega2 <= omega_max);
        ocp.subjectTo(-omega_max <= omega3 <= omega_max);
        ocp.subjectTo(-omega_max <= omega4 <= omega_max);
        ocp.subjectTo(-F_max <= F1 <= F_max);
        ocp.subjectTo(-F_max <= F2 <= F_max);
        ocp.subjectTo(-F_max <= F3 <= F_max);
        ocp.subjectTo(-F_max <= F4 <= F_max);

        if (is_slow_mode) {
            ocp.subjectTo(-1.0 <= vx_local_exp <= 1.0);
            ocp.subjectTo(-1.0 <= vy_local_exp <= 1.0);
            ocp.subjectTo(-0.8 <= omega <= 0.8);
        } else {
            ocp.subjectTo(-0.5 <= vx_local_exp <= 0.5);
            ocp.subjectTo(-0.5 <= vy_local_exp <= 0.5);
            ocp.subjectTo(-1.0 <= omega <= 1.0);
        }

        ocp.subjectTo(AT_START, x == current_x);
        ocp.subjectTo(AT_START, y == current_y);
        ocp.subjectTo(AT_START, theta == current_theta);
        ocp.subjectTo(AT_START, vx == current_vx);
        ocp.subjectTo(AT_START, vy == current_vy);
        ocp.subjectTo(AT_START, omega == current_omega);

        // 5. Solve
        OptimizationAlgorithm algorithm(ocp);
        algorithm.set(PRINTLEVEL, NONE);
        algorithm.set(MAX_NUM_ITERATIONS, 3);
        algorithm.set(KKT_TOLERANCE, 1e-3);

        auto t0 = std::chrono::high_resolution_clock::now();
        int ret = algorithm.solve();
        auto t1 = std::chrono::high_resolution_clock::now();
        double solve_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

        if (ret != SUCCESSFUL_RETURN) {
            publish_velocities(0, 0, 0); 
            RCLCPP_WARN(this->get_logger(), "⚠️ MPC Failed (code %d)", ret);
            return;
        }

        // 6. Get Results
        VariablesGrid states;
        algorithm.getDifferentialStates(states);
        if (states.getNumPoints() > 1) {
            DVector next_state = states.getVector(1);
            next_vx = next_state(3);
            next_vy = next_state(4);
            next_omega = next_state(5);
        }

        RCLCPP_INFO(this->get_logger(), "Solve: %.2fms | Next(G): [%.2f, %.2f, %.2f]", 
                    solve_ms, next_vx, next_vy, next_omega);

        if (is_motion_active) {
            publish_velocities(next_vx, next_vy, next_omega);
        } else {
            publish_velocities(0.0, 0.0, 0.0);
        }
    }

    void publish_velocities(double g_vx, double g_vy, double g_omega) {
        // Global Frame
        geometry_msgs::msg::Twist global_twist;
        global_twist.linear.x = g_vx;
        global_twist.linear.y = g_vy;
        global_twist.angular.z = g_omega;
        global_cmd_vel_publisher->publish(global_twist);

        // Local Frame (Rotate into body)
        double local_vx = g_vx * cos(current_theta) + g_vy * sin(current_theta);
        double local_vy = -g_vx * sin(current_theta) + g_vy * cos(current_theta);

        geometry_msgs::msg::Twist local_twist;
        local_twist.linear.x = local_vx;
        local_twist.linear.y = local_vy;
        local_twist.angular.z = g_omega;
        local_cmd_vel_publisher->publish(local_twist);
    }

    void update_target_callback(const std_msgs::msg::Float32MultiArray::SharedPtr msg) {
        std::lock_guard<std::mutex> lock(target_mutex);
        path_points.clear();
        for (size_t i = 0; i + 2 < msg->data.size(); i += 3) {
            path_points.push_back({ 
                msg->data[i], 
                msg->data[i + 1], 
                normalize_angle(msg->data[i + 2]) 
            });
        }
    }

private:
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr global_cmd_vel_publisher;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr local_cmd_vel_publisher;
    
    // CHANGED: PoseStamped subscriber
    rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr pose_subscription;
    
    rclcpp::Subscription<std_msgs::msg::Float32MultiArray>::SharedPtr target_subscription;
    rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr slow_mode_subscription;
    rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr motion_active_subscription;
    
    std::mutex target_mutex;
};

int main(int argc, char *argv[]) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<MyRobotNode>());
    rclcpp::shutdown();
    return 0;
}