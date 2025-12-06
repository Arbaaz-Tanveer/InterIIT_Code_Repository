// generated from rosidl_generator_c/resource/idl__functions.h.em
// with input from warehouse_msgs:srv/Localisation.idl
// generated code does not contain a copyright notice

#ifndef WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__FUNCTIONS_H_
#define WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__FUNCTIONS_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stdlib.h>

#include "rosidl_runtime_c/visibility_control.h"
#include "warehouse_msgs/msg/rosidl_generator_c__visibility_control.h"

#include "warehouse_msgs/srv/detail/localisation__struct.h"

/// Initialize srv/Localisation message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * warehouse_msgs__srv__Localisation_Request
 * )) before or use
 * warehouse_msgs__srv__Localisation_Request__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
bool
warehouse_msgs__srv__Localisation_Request__init(warehouse_msgs__srv__Localisation_Request * msg);

/// Finalize srv/Localisation message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
void
warehouse_msgs__srv__Localisation_Request__fini(warehouse_msgs__srv__Localisation_Request * msg);

/// Create srv/Localisation message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * warehouse_msgs__srv__Localisation_Request__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
warehouse_msgs__srv__Localisation_Request *
warehouse_msgs__srv__Localisation_Request__create();

/// Destroy srv/Localisation message.
/**
 * It calls
 * warehouse_msgs__srv__Localisation_Request__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
void
warehouse_msgs__srv__Localisation_Request__destroy(warehouse_msgs__srv__Localisation_Request * msg);

/// Check for srv/Localisation message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
bool
warehouse_msgs__srv__Localisation_Request__are_equal(const warehouse_msgs__srv__Localisation_Request * lhs, const warehouse_msgs__srv__Localisation_Request * rhs);

/// Copy a srv/Localisation message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
bool
warehouse_msgs__srv__Localisation_Request__copy(
  const warehouse_msgs__srv__Localisation_Request * input,
  warehouse_msgs__srv__Localisation_Request * output);

/// Initialize array of srv/Localisation messages.
/**
 * It allocates the memory for the number of elements and calls
 * warehouse_msgs__srv__Localisation_Request__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
bool
warehouse_msgs__srv__Localisation_Request__Sequence__init(warehouse_msgs__srv__Localisation_Request__Sequence * array, size_t size);

/// Finalize array of srv/Localisation messages.
/**
 * It calls
 * warehouse_msgs__srv__Localisation_Request__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
void
warehouse_msgs__srv__Localisation_Request__Sequence__fini(warehouse_msgs__srv__Localisation_Request__Sequence * array);

/// Create array of srv/Localisation messages.
/**
 * It allocates the memory for the array and calls
 * warehouse_msgs__srv__Localisation_Request__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
warehouse_msgs__srv__Localisation_Request__Sequence *
warehouse_msgs__srv__Localisation_Request__Sequence__create(size_t size);

/// Destroy array of srv/Localisation messages.
/**
 * It calls
 * warehouse_msgs__srv__Localisation_Request__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
void
warehouse_msgs__srv__Localisation_Request__Sequence__destroy(warehouse_msgs__srv__Localisation_Request__Sequence * array);

/// Check for srv/Localisation message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
bool
warehouse_msgs__srv__Localisation_Request__Sequence__are_equal(const warehouse_msgs__srv__Localisation_Request__Sequence * lhs, const warehouse_msgs__srv__Localisation_Request__Sequence * rhs);

/// Copy an array of srv/Localisation messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
bool
warehouse_msgs__srv__Localisation_Request__Sequence__copy(
  const warehouse_msgs__srv__Localisation_Request__Sequence * input,
  warehouse_msgs__srv__Localisation_Request__Sequence * output);

/// Initialize srv/Localisation message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * warehouse_msgs__srv__Localisation_Response
 * )) before or use
 * warehouse_msgs__srv__Localisation_Response__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
bool
warehouse_msgs__srv__Localisation_Response__init(warehouse_msgs__srv__Localisation_Response * msg);

/// Finalize srv/Localisation message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
void
warehouse_msgs__srv__Localisation_Response__fini(warehouse_msgs__srv__Localisation_Response * msg);

/// Create srv/Localisation message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * warehouse_msgs__srv__Localisation_Response__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
warehouse_msgs__srv__Localisation_Response *
warehouse_msgs__srv__Localisation_Response__create();

/// Destroy srv/Localisation message.
/**
 * It calls
 * warehouse_msgs__srv__Localisation_Response__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
void
warehouse_msgs__srv__Localisation_Response__destroy(warehouse_msgs__srv__Localisation_Response * msg);

/// Check for srv/Localisation message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
bool
warehouse_msgs__srv__Localisation_Response__are_equal(const warehouse_msgs__srv__Localisation_Response * lhs, const warehouse_msgs__srv__Localisation_Response * rhs);

/// Copy a srv/Localisation message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
bool
warehouse_msgs__srv__Localisation_Response__copy(
  const warehouse_msgs__srv__Localisation_Response * input,
  warehouse_msgs__srv__Localisation_Response * output);

/// Initialize array of srv/Localisation messages.
/**
 * It allocates the memory for the number of elements and calls
 * warehouse_msgs__srv__Localisation_Response__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
bool
warehouse_msgs__srv__Localisation_Response__Sequence__init(warehouse_msgs__srv__Localisation_Response__Sequence * array, size_t size);

/// Finalize array of srv/Localisation messages.
/**
 * It calls
 * warehouse_msgs__srv__Localisation_Response__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
void
warehouse_msgs__srv__Localisation_Response__Sequence__fini(warehouse_msgs__srv__Localisation_Response__Sequence * array);

/// Create array of srv/Localisation messages.
/**
 * It allocates the memory for the array and calls
 * warehouse_msgs__srv__Localisation_Response__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
warehouse_msgs__srv__Localisation_Response__Sequence *
warehouse_msgs__srv__Localisation_Response__Sequence__create(size_t size);

/// Destroy array of srv/Localisation messages.
/**
 * It calls
 * warehouse_msgs__srv__Localisation_Response__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
void
warehouse_msgs__srv__Localisation_Response__Sequence__destroy(warehouse_msgs__srv__Localisation_Response__Sequence * array);

/// Check for srv/Localisation message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
bool
warehouse_msgs__srv__Localisation_Response__Sequence__are_equal(const warehouse_msgs__srv__Localisation_Response__Sequence * lhs, const warehouse_msgs__srv__Localisation_Response__Sequence * rhs);

/// Copy an array of srv/Localisation messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_warehouse_msgs
bool
warehouse_msgs__srv__Localisation_Response__Sequence__copy(
  const warehouse_msgs__srv__Localisation_Response__Sequence * input,
  warehouse_msgs__srv__Localisation_Response__Sequence * output);

#ifdef __cplusplus
}
#endif

#endif  // WAREHOUSE_MSGS__SRV__DETAIL__LOCALISATION__FUNCTIONS_H_
