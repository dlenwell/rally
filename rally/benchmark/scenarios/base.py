# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import itertools
import random
import time

from rally import consts
from rally import exceptions
from rally import utils


def scenario(f):
    """This method is used as decorator for the methods of benchmark scenarios
       and it adds extra field is_scenario = True to the methods
    """
    f.is_scenario = True
    return f


class Scenario(object):
    """This is base class for any benchmark scenario.
       You should create subclass of this class. And you test scenarios will
       be auto discoverable and you will be able to specify it in test config.
    """
    def __init__(self, context=None, admin_clients=None, clients=None):
        self._context = context
        self._admin_clients = admin_clients
        self._clients = clients
        self._idle_time = 0
        self._atomic_actions_time = []

    @staticmethod
    def get_by_name(name):
        """Returns Scenario class by name."""
        for scenario in utils.itersubclasses(Scenario):
            if name == scenario.__name__:
                return scenario
        raise exceptions.NoSuchScenario(name=name)

    @staticmethod
    def list_benchmark_scenarios():
        """Lists all the existing methods in the benchmark scenario classes.

        Returns the method names in format <Class name>.<Method name>, which
        is used in the test config.

        :returns: List of strings
        """
        benchmark_scenarios = [
            ["%s.%s" % (scenario.__name__, method)
             for method in dir(scenario) if getattr(
                 getattr(scenario, method), "is_scenario", False)]
            for scenario in utils.itersubclasses(Scenario)
        ]
        benchmark_scenarios_flattened = list(itertools.chain.from_iterable(
                                                        benchmark_scenarios))
        return benchmark_scenarios_flattened

    @staticmethod
    def _validate_helper(validators, clients, args):
        for validator in validators:
            result = validator(clients=clients, **args)
            if not result.is_valid:
                raise exceptions.InvalidScenarioArgument(message=result.msg)

    @staticmethod
    def validate(name, args, admin=None, users=None):
        """Semantic check of benchmark arguments."""
        cls_name, method_name = name.split(".", 1)
        cls = Scenario.get_by_name(cls_name)

        method = getattr(cls, method_name)
        validators = getattr(method, "validators", [])

        if not validators:
            return

        admin_validators = [v for v in validators
                            if v.permission == consts.EndpointPermission.ADMIN]
        user_validators = [v for v in validators
                           if v.permission == consts.EndpointPermission.USER]

        # NOTE(boris-42): Potential bug, what if we don't have "admin" client
        #                 and scenario have "admin" validators.
        if admin:
            Scenario._validate_helper(admin_validators, admin, args)
        if users:
            for user in users:
                Scenario._validate_helper(user_validators, user, args)

    def context(self):
        """Returns the context of the current benchmark scenario."""
        return self._context

    def clients(self, client_type):
        """Returns a python openstack client of the requested type.

        The client will be that for one of the temporary non-administrator
        users created before the benchmark launch.

        :param client_type: Client type ("nova"/"glance" etc.)

        :returns: Standard python OpenStack client instance
        """
        return getattr(self._clients, client_type)()

    def admin_clients(self, client_type):
        """Returns a python admin openstack client of the requested type.

        :param client_type: Client type ("nova"/"glance" etc.)

        :returns: Python openstack client object
        """
        return getattr(self._admin_clients, client_type)()

    def sleep_between(self, min_sleep, max_sleep):
        """Performs a time.sleep() call for a random amount of seconds.

        The exact time is chosen uniformly randomly from the interval
        [min_sleep; max_sleep). The method also updates the idle_time
        variable to take into account the overall time spent on sleeping.

        :param min_sleep: Minimum sleep time in seconds (non-negative)
        :param max_sleep: Maximum sleep time in seconds (non-negative)
        """
        if not 0 <= min_sleep <= max_sleep:
            raise exceptions.InvalidArgumentsException(
                                        message="0 <= min_sleep <= max_sleep")

        sleep_time = random.uniform(min_sleep, max_sleep)
        time.sleep(sleep_time)
        self._idle_time += sleep_time

    def idle_time(self):
        """Returns duration of all sleep_between."""
        return self._idle_time

    def _add_atomic_actions_time(self, name, duration):
        """Adds the duration of an atomic action by its 'name'."""
        self._atomic_actions_time.append(
            {'action': name, 'duration': duration})

    def atomic_actions_time(self):
        """Returns the duration of each atomic action."""
        return self._atomic_actions_time
