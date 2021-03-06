# Copyright 2014: Mirantis Inc.
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

import json
import mock

from rally.benchmark.processing import plot
from tests import test


class PlotTestCase(test.TestCase):

    @mock.patch("rally.benchmark.processing.plot.open", create=True)
    @mock.patch("rally.benchmark.processing.plot.mako.template.Template")
    @mock.patch("rally.benchmark.processing.plot.os.path.dirname")
    @mock.patch("rally.benchmark.processing.plot._process_results")
    def test_plot(self, mock_proc_results, mock_dirname, mock_template,
                  mock_open):
        mock_dirname.return_value = "abspath"
        mock_open.return_value = mock_open
        mock_open.__enter__.return_value = mock_open
        mock_open.read.return_value = "some_template"

        templ = mock.MagicMock()
        templ.render.return_value = "output"
        mock_template.return_value = templ
        mock_proc_results.return_value = [{"name": "a"}, {"name": "b"}]

        result = plot.plot(["abc"])

        self.assertEqual(result, templ.render.return_value)
        templ.render.assert_called_once_with(
                data=json.dumps(mock_proc_results.return_value),
                tasks=map(lambda r: r["name"], mock_proc_results.return_value)
        )
        mock_template.assert_called_once_with(mock_open.read.return_value)
        mock_open.assert_called_once_with("%s/src/index.mako"
                                          % mock_dirname.return_value)

    @mock.patch("rally.benchmark.processing.plot._process_atomic_time")
    @mock.patch("rally.benchmark.processing.plot._process_main_time")
    def test__process_results(self, mock_main_time, mock_atomic_time):
        results = [
            {"key": {"name": "n1", "pos": 1, "kw": "config1"}},
            {"key": {"name": "n2", "pos": 2, "kw": "config2"}}
        ]

        mock_main_time.return_value = "main_time"
        mock_atomic_time.return_value = "main_atomic"

        output = plot._process_results(results)

        for i, r in enumerate(results):
            self.assertEqual(output[i], {
                "name": "%s (task #%d)" % (r["key"]["name"], r["key"]["pos"]),
                "config": r["key"]["kw"],
                "time": mock_main_time.return_value,
                "atomic": mock_atomic_time.return_value
            })

    def test__process_main_time(self):
        result = {
            "result": [
                {
                    "error": [],
                    "time": 1,
                    "idle_time": 2
                },
                {
                    "error": True,
                    "time": 1,
                    "idle_time": 1
                },
                {
                    "error": [],
                    "time": 2,
                    "idle_time": 3
                }
            ]
        }

        output = plot._process_main_time(result)

        self.assertEqual(output, {
            "pie": [
                {"key": "success", "value": 2},
                {"key": "errors", "value": 1}
            ],
            "iter": [
                {
                    "key": "duration",
                    "values": [[1, 1], [2, 0], [3, 2]]
                },
                {
                    "key": "idle_duration",
                    "values": [[1, 2], [2, 0], [3, 3]]
                }
            ]
        })

    def test__process_atomic_time(self):
        result = {
            "result": [
                {
                    "error": [],
                    "atomic_actions_time": [
                        {"action": "action1", "duration": 1},
                        {"action": "action2", "duration": 2}
                    ]
                },
                {
                    "error": ["some", "error", "occurred"],
                    "atomic_actions_time": [
                        {"action": "action1", "duration": 1},
                        {"action": "action2", "duration": 2}
                    ]
                },
                {
                    "error": [],
                    "atomic_actions_time": [
                        {"action": "action1", "duration": 3},
                        {"action": "action2", "duration": 4}
                    ]
                }
            ]
        }

        output = plot._process_atomic_time(result)

        self.assertEqual(output, {
            "pie": [
                {"key": "action1", "value": 2.0},
                {"key": "action2", "value": 3.0}
            ],
            "iter": [
                {
                    "key": "action1",
                    "values": [[1, 1], [2, 0], [3, 3]]
                },
                {
                    "key": "action2",
                    "values": [[1, 2], [2, 0], [3, 4]]
                }
            ]
        })
