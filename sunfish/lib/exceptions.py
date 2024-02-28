# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

class ResourceNotFound(BaseException):
    """
        Exception raised when the resource is not found.

        Attributes:
        resource_id -- resource which caused the error
        message -- explanation of the error
    """
    
    def __init__(self, resource_id):
        self.resource_id = resource_id
        message = "[Error] Resource " + resource_id + " not found."
        self.message = message
        super().__init__(self.message)


class PropertyNotFound(BaseException):
    """
        Exception raised when the resource is not found.

        Attributes:
        attribute_name -- name of the attribute not found
        message -- explanation of the error
+    """

    def __init__(self, attribute_name):
        self.attribute_name = attribute_name
        message = "Attribute " + attribute_name + "not found."
        self.message = message
        super().__init__(self.message)


class CollectionNotSupported(BaseException):
    """
        Exception raised when the payload is not valid

        Attributes:
        message -- explanation of the error
    """
    
    def __init__(self):
        self.message = "[Error] Method not allowed for Collections."
        super().__init__(self.message)

class AlreadyExists(BaseException):
    """
        Exception raised when the payload is not valid

        Attributes:
        resource_id -- resource which caused the error
        message -- explanation of the error
    """
    
    def __init__(self, resource_id):
        self.resource_id = resource_id
        self.message = "[Error] Resource " + resource_id + " already exists."
        super().__init__(self.message)

class ActionNotAllowed(BaseException):
    """
        Exception raised when an action is not allowed

        Attributes:
        message -- explanation of the error
    """
    
    def __init__(self):
        self.message = "[Error] Action not allowed."
        super().__init__(self.message)

class InvalidPath(BaseException):
    """
        Exception raised when the path is not valid

        Attributes:
        message -- explanation of the error
    """
    
    def __init__(self, path):
        self.path = path
        self.message = "[Error] Path " + path + " not valid."
        super().__init__(self.message)

class IllegalCollectionType(BaseException):
    """
        Exception raised when the path is not valid

        Attributes:
        message -- explanation of the error
    """
    
    def __init__(self, path):
        self.path = path
        self.message = "[Error] Illegal Collection type: " + type
        super().__init__(self.message)

class IllegalSubscription(BaseException):
    """
        Exception raised when the subscription is not valid

        Attributes:
        message -- explanation of the error
    """
    
    def __init__(self):
        self.message = "[Error] Illegal subscription."
        super().__init__(self.message)

class DestinationError(BaseException):
    """
        Exception raised when the resource is not found.

        Attributes:
        resource_id -- resource which caused the error
        message -- explanation of the error
    """
    
    def __init__(self):
        message = "[Error] Cannot reach Destination"
        self.message = message
        super().__init__(self.message)


class AgentForwardingFailure(BaseException):
    """
        Exception raised by the agents forwarding logic in case of error.
    """
    def __init__(self, operation, error_code, reason):
        """

        Args:
            operation: A string containing the operation executed and the target resource
            error_code: The HTTP error code
            reason: The reason for failure reported by the agent HTTP server
        """
        message = f"Agent forwarding failure while {operation}. Error code: {error_code}. Reason: {reason}"
        self.message = message
        super().__init__(self.message)
