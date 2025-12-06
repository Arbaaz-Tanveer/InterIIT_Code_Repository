// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from warehouse_msgs:srv/Localisation.idl
// generated code does not contain a copyright notice

#ifndef WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__TRAITS_HPP_
#define WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "warehouse_msgs/srv/detail/localisation__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'points'
#include "std_msgs/msg/detail/int16_multi_array__traits.hpp"
// Member 'bounds'
#include "std_msgs/msg/detail/float32_multi_array__traits.hpp"

namespace warehouse_msgs
{

namespace srv
{

inline void to_flow_style_yaml(
  const Localisation_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: points
  {
    out << "points: ";
    to_flow_style_yaml(msg.points, out);
    out << ", ";
  }

  // member: bounds
  {
    out << "bounds: ";
    to_flow_style_yaml(msg.bounds, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const Localisation_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: points
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "points:\n";
    to_block_style_yaml(msg.points, out, indentation + 2);
  }

  // member: bounds
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "bounds:\n";
    to_block_style_yaml(msg.bounds, out, indentation + 2);
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const Localisation_Request & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace srv

}  // namespace warehouse_msgs

namespace rosidl_generator_traits
{

[[deprecated("use warehouse_msgs::srv::to_block_style_yaml() instead")]]
inline void to_yaml(
  const warehouse_msgs::srv::Localisation_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  warehouse_msgs::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use warehouse_msgs::srv::to_yaml() instead")]]
inline std::string to_yaml(const warehouse_msgs::srv::Localisation_Request & msg)
{
  return warehouse_msgs::srv::to_yaml(msg);
}

template<>
inline const char * data_type<warehouse_msgs::srv::Localisation_Request>()
{
  return "warehouse_msgs::srv::Localisation_Request";
}

template<>
inline const char * name<warehouse_msgs::srv::Localisation_Request>()
{
  return "warehouse_msgs/srv/Localisation_Request";
}

template<>
struct has_fixed_size<warehouse_msgs::srv::Localisation_Request>
  : std::integral_constant<bool, has_fixed_size<std_msgs::msg::Float32MultiArray>::value && has_fixed_size<std_msgs::msg::Int16MultiArray>::value> {};

template<>
struct has_bounded_size<warehouse_msgs::srv::Localisation_Request>
  : std::integral_constant<bool, has_bounded_size<std_msgs::msg::Float32MultiArray>::value && has_bounded_size<std_msgs::msg::Int16MultiArray>::value> {};

template<>
struct is_message<warehouse_msgs::srv::Localisation_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

// Include directives for member types
// Member 'transform'
// already included above
// #include "std_msgs/msg/detail/float32_multi_array__traits.hpp"

namespace warehouse_msgs
{

namespace srv
{

inline void to_flow_style_yaml(
  const Localisation_Response & msg,
  std::ostream & out)
{
  out << "{";
  // member: transform
  {
    out << "transform: ";
    to_flow_style_yaml(msg.transform, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const Localisation_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: transform
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "transform:\n";
    to_block_style_yaml(msg.transform, out, indentation + 2);
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const Localisation_Response & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace srv

}  // namespace warehouse_msgs

namespace rosidl_generator_traits
{

[[deprecated("use warehouse_msgs::srv::to_block_style_yaml() instead")]]
inline void to_yaml(
  const warehouse_msgs::srv::Localisation_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  warehouse_msgs::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use warehouse_msgs::srv::to_yaml() instead")]]
inline std::string to_yaml(const warehouse_msgs::srv::Localisation_Response & msg)
{
  return warehouse_msgs::srv::to_yaml(msg);
}

template<>
inline const char * data_type<warehouse_msgs::srv::Localisation_Response>()
{
  return "warehouse_msgs::srv::Localisation_Response";
}

template<>
inline const char * name<warehouse_msgs::srv::Localisation_Response>()
{
  return "warehouse_msgs/srv/Localisation_Response";
}

template<>
struct has_fixed_size<warehouse_msgs::srv::Localisation_Response>
  : std::integral_constant<bool, has_fixed_size<std_msgs::msg::Float32MultiArray>::value> {};

template<>
struct has_bounded_size<warehouse_msgs::srv::Localisation_Response>
  : std::integral_constant<bool, has_bounded_size<std_msgs::msg::Float32MultiArray>::value> {};

template<>
struct is_message<warehouse_msgs::srv::Localisation_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<warehouse_msgs::srv::Localisation>()
{
  return "warehouse_msgs::srv::Localisation";
}

template<>
inline const char * name<warehouse_msgs::srv::Localisation>()
{
  return "warehouse_msgs/srv/Localisation";
}

template<>
struct has_fixed_size<warehouse_msgs::srv::Localisation>
  : std::integral_constant<
    bool,
    has_fixed_size<warehouse_msgs::srv::Localisation_Request>::value &&
    has_fixed_size<warehouse_msgs::srv::Localisation_Response>::value
  >
{
};

template<>
struct has_bounded_size<warehouse_msgs::srv::Localisation>
  : std::integral_constant<
    bool,
    has_bounded_size<warehouse_msgs::srv::Localisation_Request>::value &&
    has_bounded_size<warehouse_msgs::srv::Localisation_Response>::value
  >
{
};

template<>
struct is_service<warehouse_msgs::srv::Localisation>
  : std::true_type
{
};

template<>
struct is_service_request<warehouse_msgs::srv::Localisation_Request>
  : std::true_type
{
};

template<>
struct is_service_response<warehouse_msgs::srv::Localisation_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

#endif  // WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__TRAITS_HPP_
