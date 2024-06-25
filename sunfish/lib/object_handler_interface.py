# Copyright IBM Corp. 2024
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE
import string
from abc import abstractmethod
from typing import Optional


class ObjectHandlerInterface:
    @abstractmethod
    def dispatch(self, object_type: str, path: str,
                 operation: 'sunfish.models.types.SunfishRequestType', payload: dict = None):
        pass

    @abstractmethod
    def forward_to_manager(self, request_type: 'sunfish.models.types.SunfishRequestType', path: string, payload: dict = None) -> Optional[dict]:
        pass

