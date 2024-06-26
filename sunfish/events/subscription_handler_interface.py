# Copyright IBM Corp. 2023
# This software is available to you under a BSD 3-Clause License. 
# The full license terms are available here: https://github.com/OpenFabrics/sunfish_library_reference/blob/main/LICENSE

from abc import abstractmethod


class SubscriptionHandlerInterface():
    @abstractmethod
    def load_subscriptions(self):
        pass
    @abstractmethod
    def new_subscription(self, payload: dict):
        pass

    @abstractmethod
    def validate_subscription(self, payload: dict):
        pass

    @abstractmethod
    def delete_subscription(self, id):
        pass