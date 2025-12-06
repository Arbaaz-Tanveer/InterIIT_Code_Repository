# generated from rosidl_generator_py/resource/_idl.py.em
# with input from warehouse_msgs:srv/Localisation.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_Localisation_Request(type):
    """Metaclass of message 'Localisation_Request'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('warehouse_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'warehouse_msgs.srv.Localisation_Request')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__localisation__request
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__localisation__request
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__localisation__request
            cls._TYPE_SUPPORT = module.type_support_msg__srv__localisation__request
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__localisation__request

            from std_msgs.msg import Float32MultiArray
            if Float32MultiArray.__class__._TYPE_SUPPORT is None:
                Float32MultiArray.__class__.__import_type_support__()

            from std_msgs.msg import Int16MultiArray
            if Int16MultiArray.__class__._TYPE_SUPPORT is None:
                Int16MultiArray.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class Localisation_Request(metaclass=Metaclass_Localisation_Request):
    """Message class 'Localisation_Request'."""

    __slots__ = [
        '_points',
        '_bounds',
    ]

    _fields_and_field_types = {
        'points': 'std_msgs/Int16MultiArray',
        'bounds': 'std_msgs/Float32MultiArray',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.NamespacedType(['std_msgs', 'msg'], 'Int16MultiArray'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['std_msgs', 'msg'], 'Float32MultiArray'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        from std_msgs.msg import Int16MultiArray
        self.points = kwargs.get('points', Int16MultiArray())
        from std_msgs.msg import Float32MultiArray
        self.bounds = kwargs.get('bounds', Float32MultiArray())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.points != other.points:
            return False
        if self.bounds != other.bounds:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def points(self):
        """Message field 'points'."""
        return self._points

    @points.setter
    def points(self, value):
        if __debug__:
            from std_msgs.msg import Int16MultiArray
            assert \
                isinstance(value, Int16MultiArray), \
                "The 'points' field must be a sub message of type 'Int16MultiArray'"
        self._points = value

    @builtins.property
    def bounds(self):
        """Message field 'bounds'."""
        return self._bounds

    @bounds.setter
    def bounds(self, value):
        if __debug__:
            from std_msgs.msg import Float32MultiArray
            assert \
                isinstance(value, Float32MultiArray), \
                "The 'bounds' field must be a sub message of type 'Float32MultiArray'"
        self._bounds = value


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_Localisation_Response(type):
    """Metaclass of message 'Localisation_Response'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('warehouse_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'warehouse_msgs.srv.Localisation_Response')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__localisation__response
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__localisation__response
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__localisation__response
            cls._TYPE_SUPPORT = module.type_support_msg__srv__localisation__response
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__localisation__response

            from std_msgs.msg import Float32MultiArray
            if Float32MultiArray.__class__._TYPE_SUPPORT is None:
                Float32MultiArray.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class Localisation_Response(metaclass=Metaclass_Localisation_Response):
    """Message class 'Localisation_Response'."""

    __slots__ = [
        '_transform',
    ]

    _fields_and_field_types = {
        'transform': 'std_msgs/Float32MultiArray',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.NamespacedType(['std_msgs', 'msg'], 'Float32MultiArray'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        from std_msgs.msg import Float32MultiArray
        self.transform = kwargs.get('transform', Float32MultiArray())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.transform != other.transform:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def transform(self):
        """Message field 'transform'."""
        return self._transform

    @transform.setter
    def transform(self, value):
        if __debug__:
            from std_msgs.msg import Float32MultiArray
            assert \
                isinstance(value, Float32MultiArray), \
                "The 'transform' field must be a sub message of type 'Float32MultiArray'"
        self._transform = value


class Metaclass_Localisation(type):
    """Metaclass of service 'Localisation'."""

    _TYPE_SUPPORT = None

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('warehouse_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'warehouse_msgs.srv.Localisation')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._TYPE_SUPPORT = module.type_support_srv__srv__localisation

            from warehouse_msgs.srv import _localisation
            if _localisation.Metaclass_Localisation_Request._TYPE_SUPPORT is None:
                _localisation.Metaclass_Localisation_Request.__import_type_support__()
            if _localisation.Metaclass_Localisation_Response._TYPE_SUPPORT is None:
                _localisation.Metaclass_Localisation_Response.__import_type_support__()


class Localisation(metaclass=Metaclass_Localisation):
    from warehouse_msgs.srv._localisation import Localisation_Request as Request
    from warehouse_msgs.srv._localisation import Localisation_Response as Response

    def __init__(self):
        raise NotImplementedError('Service classes can not be instantiated')
