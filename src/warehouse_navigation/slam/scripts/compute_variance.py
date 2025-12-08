#!/usr/bin/env python3
# Computes covariance for ODOM and IMU from a fixed CSV file

import numpy as np
import pandas as pd
import argparse
import math
import os

def circular_variance_rad2(angle_array):
    """Compute circular variance (for yaw) in rad^2"""
    c = np.cos(angle_array)
    s = np.sin(angle_array)
    C = np.mean(c)
    S = np.mean(s)
    R = math.sqrt(C*C + S*S)
    if R <= 0:
        return 1e3
    return -2.0 * math.log(R)

def main():

    # =======================================================
    # FIXED CSV FILE (placed in same folder as this script)
    # =======================================================
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "odom_imu_samples.csv")

    print(f"Using CSV file: {csv_path}")

    if not os.path.exists(csv_path):
        print("\nERROR: CSV file not found!")
        print("Place odom_imu_data.csv in the same folder as this script.")
        return

    df = pd.read_csv(csv_path).dropna()

    # === ODOM COVARIANCES ===
    xs = df["x"].to_numpy()
    ys = df["y"].to_numpy()
    yaws = df["yaw"].to_numpy()
    vxs = df["vx"].to_numpy()
    vys = df["vy"].to_numpy()
    vyaws = df["vyaw"].to_numpy()

    var_x = np.var(xs, ddof=1)
    var_y = np.var(ys, ddof=1)
    var_yaw = circular_variance_rad2(yaws)
    var_vx = np.var(vxs, ddof=1)
    var_vy = np.var(vys, ddof=1)
    var_vyaw = np.var(vyaws, ddof=1)

    # === IMU COVARIANCES ===
    wx = df["imu_wx"].to_numpy()
    wy = df["imu_wy"].to_numpy()
    wz = df["imu_wz"].to_numpy()
    ax = df["imu_ax"].to_numpy()
    ay = df["imu_ay"].to_numpy()
    az = df["imu_az"].to_numpy()

    var_wx = np.var(wx, ddof=1)
    var_wy = np.var(wy, ddof=1)
    var_wz = np.var(wz, ddof=1)
    var_ax = np.var(ax, ddof=1)
    var_ay = np.var(ay, ddof=1)
    var_az = np.var(az, ddof=1)

    # Safety factor
    sf = 2.0
    var_x *= sf; var_y *= sf; var_yaw *= sf
    var_vx *= sf; var_vy *= sf; var_vyaw *= sf
    var_wx *= sf; var_wy *= sf; var_wz *= sf
    var_ax *= sf; var_ay *= sf; var_az *= sf

    # ---------------------- PRINTING ------------------------
    print("\n================= ODOM pose covariance 6×6 =================")
    odom_pose_cov = [
        var_x, 0, 0, 0, 0, 0,
        0, var_y, 0, 0, 0, 0,
        0, 0, 1000, 0, 0, 0,
        0, 0, 0, 1000, 0, 0,
        0, 0, 0, 0, 1000, 0,
        0, 0, 0, 0, 0, var_yaw
    ]
    print(odom_pose_cov)

    print("\n================= ODOM twist covariance 6×6 =================")
    odom_twist_cov = [
        var_vx, 0, 0, 0, 0, 0,
        0, var_vy, 0, 0, 0, 0,
        0, 0, 1000, 0, 0, 0,
        0, 0, 0, 1000, 0, 0,
        0, 0, 0, 0, 1000, 0,
        0, 0, 0, 0, 0, var_vyaw
    ]
    print(odom_twist_cov)

    print("\n================= IMU orientation_covariance (3×3) =================")
    ori_cov = [
        99999, 0, 0,
        0, 99999, 0,
        0, 0, var_yaw
    ]
    print(ori_cov)

    print("\n================= IMU angular_velocity_covariance (3×3) =================")
    ang_cov = [
        var_wx, 0, 0,
        0, var_wy, 0,
        0, 0, var_wz
    ]
    print(ang_cov)

    print("\n================= IMU linear_acceleration_covariance (3×3) =================")
    acc_cov = [
        var_ax, 0, 0,
        0, var_ay, 0,
        0, 0, var_az
    ]
    print(acc_cov)


if __name__ == "__main__":
    main()

