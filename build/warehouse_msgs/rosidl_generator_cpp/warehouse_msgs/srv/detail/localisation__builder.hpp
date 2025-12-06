// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from warehouse_msgs:srv/Localisation.idl
// generated code does not contain a copyright notice

#ifndef WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__BUILDER_HPP_
#define WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "warehouse_msgs/srv/detail/localisation__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace warehouse_msgs
{

namespace srv
{

namespace builder
{

class Init_Localisation_Request_bounds
{
public:
  explicit Init_Localisation_Request_bounds(::warehouse_msgs::srv::Localisation_Request & msg)
  : msg_(msg)
  {}
  ::warehouse_msgs::srv::Localisation_Request bounds(::warehouse_msgs::srv::Localisation_Request::_bounds_type arg)
  {
    msg_.bounds = std::move(arg);
    return std::move(msg_);
  }

private:
  ::warehouse_msgs::srv::Localisation_Request msg_;
};

class Init_Localisation_Request_points
{
public:
  Init_Localisation_Request_points()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Localisation_Request_bounds points(::warehouse_msgs::srv::Localisation_Request::_points_type arg)
  {
    msg_.points = std::move(arg);
    return Init_Localisation_Request_bounds(msg_);
  }

private:
  ::warehouse_msgs::srv::Localisation_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::warehouse_msgs::srv::Localisation_Request>()
{
  return warehouse_msgs::srv::builder::Init_Localisation_Request_points();
}

}  // namespace warehouse_msgs


namespace warehouse_msgs
{

namespace srv
{

namespace builder
{

class Init_Localisation_Response_transform
{
public:
  Init_Localisation_Response_transform()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::warehouse_msgs::srv::Localisation_Response transform(::warehouse_msgs::srv::Localisation_Response::_transform_type arg)
  {
    msg_.transform = std::move(arg);
    return std::move(msg_);
  }

private:
  ::warehouse_msgs::srv::Localisation_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::warehouse_msgs::srv::Localisation_Response>()
{
  return warehouse_msgs::srv::builder::Init_Localisation_Response_transform();
}

}  // namespace warehouse_msgs

#endif  // WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__BUILDER_HPP_
