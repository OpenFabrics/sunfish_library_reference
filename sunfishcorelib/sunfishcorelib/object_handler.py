# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

class ObjectHandler:
     def __init__(self, core):
          """init that sets the conf and calls the load subcriptions method

          Args:
               conf (dict): dictionary where are specified the storage implementation type and the specific backend configuration.
          """
          self.core = core
     
     def ComputerSystem(self, payload):
        return "ObjectHandler ComputerSystem"