# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

from abc import abstractmethod

class EventHandlerInterface():
    @abstractmethod
    def new_event():
        pass
    @abstractmethod
    def check_data_type():
        pass

    @abstractmethod
    def forward_event():
        pass