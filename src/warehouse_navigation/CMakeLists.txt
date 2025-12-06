cmake_minimum_required(VERSION 3.8)
project(warehouse_navigation)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# 1. Find ROS Dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclpy REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(warehouse_msgs REQUIRED)
find_package(OpenCV REQUIRED)

# 2. Find External ACADO Toolkit
# ---------------------------------------------------------
# Header found at: /usr/local/include/acado/acado_toolkit.hpp
find_path(ACADO_INCLUDE_DIR acado_toolkit.hpp
  PATHS /usr/local/include/acado
  NO_DEFAULT_PATH
)

# Library found at: /usr/local/lib/libacado_toolkit_s.so
# We search for 'acado_toolkit_s' now
find_library(ACADO_LIBRARY NAMES acado_toolkit_s acado_toolkit
  PATHS /usr/local/lib /usr/lib
)

if(ACADO_INCLUDE_DIR AND ACADO_LIBRARY)
  message(STATUS "Found ACADO Header: ${ACADO_INCLUDE_DIR}")
  message(STATUS "Found ACADO Library: ${ACADO_LIBRARY}")
  # Include this specific dir so <acado_toolkit.hpp> works
  include_directories(${ACADO_INCLUDE_DIR})
else()
  message(WARNING "Header found: ${ACADO_INCLUDE_DIR}")
  message(WARNING "Lib found: ${ACADO_LIBRARY}")
  message(FATAL_ERROR "ACADO toolkit not found! We looked for libacado_toolkit_s.so in /usr/local/lib")
endif()
# ---------------------------------------------------------


# 3. Install Python Module
ament_python_install_package(${PROJECT_NAME})

# 4. Install Python Scripts
install(PROGRAMS
  warehouse_navigation/path_planner.py
  warehouse_navigation/vision.py
  warehouse_navigation/utilities.py
  DESTINATION lib/${PROJECT_NAME}
)

# 5. Build C++ Nodes

# --- Genetic Node ---
add_executable(genetic_node src/genetic.cpp)
ament_target_dependencies(genetic_node 
  rclcpp 
  std_msgs 
  warehouse_msgs 
  OpenCV
)

# --- Controller Node (Requires ACADO) ---
add_executable(controller1 src/controller1.cpp)
ament_target_dependencies(controller1 
  rclcpp 
  std_msgs 
  geometry_msgs 
  warehouse_msgs
)
# Link ACADO library manually
target_link_libraries(controller1 ${ACADO_LIBRARY})


# 6. Install Targets
install(TARGETS
  genetic_node
  controller1
  DESTINATION lib/${PROJECT_NAME}
)

# install(DIRECTORY
#   launch
#   config
#   DESTINATION share/${PROJECT_NAME}
# )
    
ament_package()
