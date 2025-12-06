import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/era/Documents/InterIIT_Code_Repository/install/warehouse_robot_bringup'
