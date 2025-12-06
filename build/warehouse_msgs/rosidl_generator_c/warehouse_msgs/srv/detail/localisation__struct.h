// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from warehouse_msgs:srv/Localisation.idl
// generated code does not contain a copyright notice

#ifndef WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__STRUCT_H_
#define WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'points'
#include "std_msgs/msg/detail/int16_multi_array__struct.h"
// Member 'bounds'
#include "std_msgs/msg/detail/float32_multi_array__struct.h"

/// Struct defined in srv/Localisation in the package warehouse_msgs.
typedef struct warehouse_msgs__srv__Localisation_Request
{
  std_msgs__msg__Int16MultiArray points;
  std_msgs__msg__Float32MultiArray bounds;
} warehouse_msgs__srv__Localisation_Request;

// Struct for a sequence of warehouse_msgs__srv__Localisation_Request.
typedef struct warehouse_msgs__srv__Localisation_Request__Sequence
{
  warehouse_msgs__srv__Localisation_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} warehouse_msgs__srv__Localisation_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'transform'
// already included above
// #include "std_msgs/msg/detail/float32_multi_array__struct.h"

/// Struct defined in srv/Localisation in the package warehouse_msgs.
typedef struct warehouse_msgs__srv__Localisation_Response
{
  std_msgs__msg__Float32MultiArray transform;
} warehouse_msgs__srv__Localisation_Response;

// Struct for a sequence of warehouse_msgs__srv__Localisation_Response.
typedef struct warehouse_msgs__srv__Localisation_Response__Sequence
{
  warehouse_msgs__srv__Localisation_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} warehouse_msgs__srv__Localisation_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__STRUCT_H_
