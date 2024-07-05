# Copyright IBM Corp. 2024
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE
from abc import abstractmethod

class ObjectHandlerInterface:
    @abstractmethod
    def dispatch(self, object_type: str, path: str,
                 operation: 'sunfish.models.types.SunfishRequestType', payload: dict = None):
        pass
