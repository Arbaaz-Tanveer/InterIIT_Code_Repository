// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from warehouse_msgs:srv/Localisation.idl
// generated code does not contain a copyright notice

#ifndef WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__STRUCT_HPP_
#define WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


// Include directives for member types
// Member 'points'
#include "std_msgs/msg/detail/int16_multi_array__struct.hpp"
// Member 'bounds'
#include "std_msgs/msg/detail/float32_multi_array__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__warehouse_msgs__srv__Localisation_Request __attribute__((deprecated))
#else
# define DEPRECATED__warehouse_msgs__srv__Localisation_Request __declspec(deprecated)
#endif

namespace warehouse_msgs
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct Localisation_Request_
{
  using Type = Localisation_Request_<ContainerAllocator>;

  explicit Localisation_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : points(_init),
    bounds(_init)
  {
    (void)_init;
  }

  explicit Localisation_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : points(_alloc, _init),
    bounds(_alloc, _init)
  {
    (void)_init;
  }

  // field types and members
  using _points_type =
    std_msgs::msg::Int16MultiArray_<ContainerAllocator>;
  _points_type points;
  using _bounds_type =
    std_msgs::msg::Float32MultiArray_<ContainerAllocator>;
  _bounds_type bounds;

  // setters for named parameter idiom
  Type & set__points(
    const std_msgs::msg::Int16MultiArray_<ContainerAllocator> & _arg)
  {
    this->points = _arg;
    return *this;
  }
  Type & set__bounds(
    const std_msgs::msg::Float32MultiArray_<ContainerAllocator> & _arg)
  {
    this->bounds = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    warehouse_msgs::srv::Localisation_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const warehouse_msgs::srv::Localisation_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<warehouse_msgs::srv::Localisation_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<warehouse_msgs::srv::Localisation_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      warehouse_msgs::srv::Localisation_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<warehouse_msgs::srv::Localisation_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      warehouse_msgs::srv::Localisation_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<warehouse_msgs::srv::Localisation_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<warehouse_msgs::srv::Localisation_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<warehouse_msgs::srv::Localisation_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__warehouse_msgs__srv__Localisation_Request
    std::shared_ptr<warehouse_msgs::srv::Localisation_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__warehouse_msgs__srv__Localisation_Request
    std::shared_ptr<warehouse_msgs::srv::Localisation_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const Localisation_Request_ & other) const
  {
    if (this->points != other.points) {
      return false;
    }
    if (this->bounds != other.bounds) {
      return false;
    }
    return true;
  }
  bool operator!=(const Localisation_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct Localisation_Request_

// alias to use template instance with default allocator
using Localisation_Request =
  warehouse_msgs::srv::Localisation_Request_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace warehouse_msgs


// Include directives for member types
// Member 'transform'
// already included above
// #include "std_msgs/msg/detail/float32_multi_array__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__warehouse_msgs__srv__Localisation_Response __attribute__((deprecated))
#else
# define DEPRECATED__warehouse_msgs__srv__Localisation_Response __declspec(deprecated)
#endif

namespace warehouse_msgs
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct Localisation_Response_
{
  using Type = Localisation_Response_<ContainerAllocator>;

  explicit Localisation_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : transform(_init)
  {
    (void)_init;
  }

  explicit Localisation_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : transform(_alloc, _init)
  {
    (void)_init;
  }

  // field types and members
  using _transform_type =
    std_msgs::msg::Float32MultiArray_<ContainerAllocator>;
  _transform_type transform;

  // setters for named parameter idiom
  Type & set__transform(
    const std_msgs::msg::Float32MultiArray_<ContainerAllocator> & _arg)
  {
    this->transform = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    warehouse_msgs::srv::Localisation_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const warehouse_msgs::srv::Localisation_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<warehouse_msgs::srv::Localisation_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<warehouse_msgs::srv::Localisation_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      warehouse_msgs::srv::Localisation_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<warehouse_msgs::srv::Localisation_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      warehouse_msgs::srv::Localisation_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<warehouse_msgs::srv::Localisation_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<warehouse_msgs::srv::Localisation_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<warehouse_msgs::srv::Localisation_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__warehouse_msgs__srv__Localisation_Response
    std::shared_ptr<warehouse_msgs::srv::Localisation_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__warehouse_msgs__srv__Localisation_Response
    std::shared_ptr<warehouse_msgs::srv::Localisation_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const Localisation_Response_ & other) const
  {
    if (this->transform != other.transform) {
      return false;
    }
    return true;
  }
  bool operator!=(const Localisation_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct Localisation_Response_

// alias to use template instance with default allocator
using Localisation_Response =
  warehouse_msgs::srv::Localisation_Response_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace warehouse_msgs

namespace warehouse_msgs
{

namespace srv
{

struct Localisation
{
  using Request = warehouse_msgs::srv::Localisation_Request;
  using Response = warehouse_msgs::srv::Localisation_Response;
};

}  // namespace srv

}  // namespace warehouse_msgs

#endif  // WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__STRUCT_HPP_
