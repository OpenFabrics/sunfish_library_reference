# Copyright IBM Corp. 2023
# Copyright Hewlett Packard Enterprise Development LP 2024
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

from abc import abstractmethod

class BackendInterface():
    @abstractmethod
    def read():
        pass
    @abstractmethod
    def write():
        pass

    @abstractmethod
    def replace():
        pass

    @abstractmethod
    def patch():
        pass

    @abstractmethod
    def remove():
        pass

    @abstractmethod
    def reset_resources():
        pass
