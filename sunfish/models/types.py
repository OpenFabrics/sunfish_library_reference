# Copyright IBM Corp. 2024
# This software is available to you under a BSD 3-Clause License.
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

from enum import Enum


class SunfishRequestType(Enum):
    GET = 0
    CREATE = 1
    DELETE = 2
    PATCH = 3
    REPLACE = 4
