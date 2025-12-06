// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from warehouse_msgs:srv/Localisation.idl
// generated code does not contain a copyright notice
#include "warehouse_msgs/srv/detail/localisation__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"

// Include directives for member types
// Member `points`
#include "std_msgs/msg/detail/int16_multi_array__functions.h"
// Member `bounds`
#include "std_msgs/msg/detail/float32_multi_array__functions.h"

bool
warehouse_msgs__srv__Localisation_Request__init(warehouse_msgs__srv__Localisation_Request * msg)
{
  if (!msg) {
    return false;
  }
  // points
  if (!std_msgs__msg__Int16MultiArray__init(&msg->points)) {
    warehouse_msgs__srv__Localisation_Request__fini(msg);
    return false;
  }
  // bounds
  if (!std_msgs__msg__Float32MultiArray__init(&msg->bounds)) {
    warehouse_msgs__srv__Localisation_Request__fini(msg);
    return false;
  }
  return true;
}

void
warehouse_msgs__srv__Localisation_Request__fini(warehouse_msgs__srv__Localisation_Request * msg)
{
  if (!msg) {
    return;
  }
  // points
  std_msgs__msg__Int16MultiArray__fini(&msg->points);
  // bounds
  std_msgs__msg__Float32MultiArray__fini(&msg->bounds);
}

bool
warehouse_msgs__srv__Localisation_Request__are_equal(const warehouse_msgs__srv__Localisation_Request * lhs, const warehouse_msgs__srv__Localisation_Request * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // points
  if (!std_msgs__msg__Int16MultiArray__are_equal(
      &(lhs->points), &(rhs->points)))
  {
    return false;
  }
  // bounds
  if (!std_msgs__msg__Float32MultiArray__are_equal(
      &(lhs->bounds), &(rhs->bounds)))
  {
    return false;
  }
  return true;
}

bool
warehouse_msgs__srv__Localisation_Request__copy(
  const warehouse_msgs__srv__Localisation_Request * input,
  warehouse_msgs__srv__Localisation_Request * output)
{
  if (!input || !output) {
    return false;
  }
  // points
  if (!std_msgs__msg__Int16MultiArray__copy(
      &(input->points), &(output->points)))
  {
    return false;
  }
  // bounds
  if (!std_msgs__msg__Float32MultiArray__copy(
      &(input->bounds), &(output->bounds)))
  {
    return false;
  }
  return true;
}

warehouse_msgs__srv__Localisation_Request *
warehouse_msgs__srv__Localisation_Request__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  warehouse_msgs__srv__Localisation_Request * msg = (warehouse_msgs__srv__Localisation_Request *)allocator.allocate(sizeof(warehouse_msgs__srv__Localisation_Request), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(warehouse_msgs__srv__Localisation_Request));
  bool success = warehouse_msgs__srv__Localisation_Request__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
warehouse_msgs__srv__Localisation_Request__destroy(warehouse_msgs__srv__Localisation_Request * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    warehouse_msgs__srv__Localisation_Request__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
warehouse_msgs__srv__Localisation_Request__Sequence__init(warehouse_msgs__srv__Localisation_Request__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  warehouse_msgs__srv__Localisation_Request * data = NULL;

  if (size) {
    data = (warehouse_msgs__srv__Localisation_Request *)allocator.zero_allocate(size, sizeof(warehouse_msgs__srv__Localisation_Request), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = warehouse_msgs__srv__Localisation_Request__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        warehouse_msgs__srv__Localisation_Request__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
warehouse_msgs__srv__Localisation_Request__Sequence__fini(warehouse_msgs__srv__Localisation_Request__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      warehouse_msgs__srv__Localisation_Request__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

warehouse_msgs__srv__Localisation_Request__Sequence *
warehouse_msgs__srv__Localisation_Request__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  warehouse_msgs__srv__Localisation_Request__Sequence * array = (warehouse_msgs__srv__Localisation_Request__Sequence *)allocator.allocate(sizeof(warehouse_msgs__srv__Localisation_Request__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = warehouse_msgs__srv__Localisation_Request__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
warehouse_msgs__srv__Localisation_Request__Sequence__destroy(warehouse_msgs__srv__Localisation_Request__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    warehouse_msgs__srv__Localisation_Request__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
warehouse_msgs__srv__Localisation_Request__Sequence__are_equal(const warehouse_msgs__srv__Localisation_Request__Sequence * lhs, const warehouse_msgs__srv__Localisation_Request__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!warehouse_msgs__srv__Localisation_Request__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
warehouse_msgs__srv__Localisation_Request__Sequence__copy(
  const warehouse_msgs__srv__Localisation_Request__Sequence * input,
  warehouse_msgs__srv__Localisation_Request__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(warehouse_msgs__srv__Localisation_Request);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    warehouse_msgs__srv__Localisation_Request * data =
      (warehouse_msgs__srv__Localisation_Request *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!warehouse_msgs__srv__Localisation_Request__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          warehouse_msgs__srv__Localisation_Request__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!warehouse_msgs__srv__Localisation_Request__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}


// Include directives for member types
// Member `transform`
// already included above
// #include "std_msgs/msg/detail/float32_multi_array__functions.h"

bool
warehouse_msgs__srv__Localisation_Response__init(warehouse_msgs__srv__Localisation_Response * msg)
{
  if (!msg) {
    return false;
  }
  // transform
  if (!std_msgs__msg__Float32MultiArray__init(&msg->transform)) {
    warehouse_msgs__srv__Localisation_Response__fini(msg);
    return false;
  }
  return true;
}

void
warehouse_msgs__srv__Localisation_Response__fini(warehouse_msgs__srv__Localisation_Response * msg)
{
  if (!msg) {
    return;
  }
  // transform
  std_msgs__msg__Float32MultiArray__fini(&msg->transform);
}

bool
warehouse_msgs__srv__Localisation_Response__are_equal(const warehouse_msgs__srv__Localisation_Response * lhs, const warehouse_msgs__srv__Localisation_Response * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // transform
  if (!std_msgs__msg__Float32MultiArray__are_equal(
      &(lhs->transform), &(rhs->transform)))
  {
    return false;
  }
  return true;
}

bool
warehouse_msgs__srv__Localisation_Response__copy(
  const warehouse_msgs__srv__Localisation_Response * input,
  warehouse_msgs__srv__Localisation_Response * output)
{
  if (!input || !output) {
    return false;
  }
  // transform
  if (!std_msgs__msg__Float32MultiArray__copy(
      &(input->transform), &(output->transform)))
  {
    return false;
  }
  return true;
}

warehouse_msgs__srv__Localisation_Response *
warehouse_msgs__srv__Localisation_Response__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  warehouse_msgs__srv__Localisation_Response * msg = (warehouse_msgs__srv__Localisation_Response *)allocator.allocate(sizeof(warehouse_msgs__srv__Localisation_Response), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(warehouse_msgs__srv__Localisation_Response));
  bool success = warehouse_msgs__srv__Localisation_Response__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
warehouse_msgs__srv__Localisation_Response__destroy(warehouse_msgs__srv__Localisation_Response * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    warehouse_msgs__srv__Localisation_Response__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
warehouse_msgs__srv__Localisation_Response__Sequence__init(warehouse_msgs__srv__Localisation_Response__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  warehouse_msgs__srv__Localisation_Response * data = NULL;

  if (size) {
    data = (warehouse_msgs__srv__Localisation_Response *)allocator.zero_allocate(size, sizeof(warehouse_msgs__srv__Localisation_Response), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = warehouse_msgs__srv__Localisation_Response__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        warehouse_msgs__srv__Localisation_Response__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
warehouse_msgs__srv__Localisation_Response__Sequence__fini(warehouse_msgs__srv__Localisation_Response__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      warehouse_msgs__srv__Localisation_Response__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

warehouse_msgs__srv__Localisation_Response__Sequence *
warehouse_msgs__srv__Localisation_Response__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  warehouse_msgs__srv__Localisation_Response__Sequence * array = (warehouse_msgs__srv__Localisation_Response__Sequence *)allocator.allocate(sizeof(warehouse_msgs__srv__Localisation_Response__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = warehouse_msgs__srv__Localisation_Response__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
warehouse_msgs__srv__Localisation_Response__Sequence__destroy(warehouse_msgs__srv__Localisation_Response__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    warehouse_msgs__srv__Localisation_Response__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
warehouse_msgs__srv__Localisation_Response__Sequence__are_equal(const warehouse_msgs__srv__Localisation_Response__Sequence * lhs, const warehouse_msgs__srv__Localisation_Response__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!warehouse_msgs__srv__Localisation_Response__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
warehouse_msgs__srv__Localisation_Response__Sequence__copy(
  const warehouse_msgs__srv__Localisation_Response__Sequence * input,
  warehouse_msgs__srv__Localisation_Response__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(warehouse_msgs__srv__Localisation_Response);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    warehouse_msgs__srv__Localisation_Response * data =
      (warehouse_msgs__srv__Localisation_Response *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!warehouse_msgs__srv__Localisation_Response__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          warehouse_msgs__srv__Localisation_Response__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!warehouse_msgs__srv__Localisation_Response__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
