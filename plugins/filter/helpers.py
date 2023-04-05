#!/usr/bin/env python
# Copyright 2019 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import ast
import json
import re


class FilterModule:
    def filters(self):
        return {
            'needs_delete': self.needs_delete,
            'haskey': self.haskey,
            'dict_to_list': self.dict_to_list,
        }

    def needs_delete(self, container_infos, config, config_id,
                     clean_orphans=False, check_config=True):
        """Returns a list of containers which need to be removed.

        This filter will check which containers need to be removed for these
        reasons: no config_data, updated config_data or container not
        part of the global config.

        :param container_infos: list
        :param config: dict
        :param config_id: string
        :param clean_orphans: bool
        :param check_config: bool to whether or not check if config changed
        :returns: list
        """
        to_delete = []
        to_skip = []
        installed_containers = []

        for c in container_infos:
            c_name = c['Name']
            installed_containers.append(c_name)
            labels = c['Config'].get('Labels', {})
            managed_by = labels.get('managed_by', 'unknown').lower()

            # Check containers have a label
            if not labels:
                to_skip += [c_name]
                continue

            elif not re.findall(r"(?=edpm)", managed_by):
                to_skip += [c_name]
                continue

            # Only remove containers managed in this config_id
            elif labels.get('config_id') != config_id:
                to_skip += [c_name]
                continue

            # Remove containers with no config_data
            # e.g. broken config containers
            elif 'config_data' not in labels and clean_orphans:
                to_delete += [c_name]

        for c_name, config_data in config.items():
            # don't try to remove a container which doesn't exist
            if c_name not in installed_containers:
                continue

            # already tagged to be removed
            if c_name in to_delete:
                continue

            if c_name in to_skip:
                continue

            # Remove containers managed by edpm-ansible when config_data
            # changed. Since we already cleaned the containers not in config,
            # this check needs to be in that loop.
            # e.g. new EDPM_CONFIG_HASH during a minor update
            c_datas = []
            for c in container_infos:
                if c_name == c['Name']:
                    try:
                        c_datas.append(c['Config']['Labels']['config_data'])
                    except KeyError:
                        pass

            # Build c_facts so it can be compared later with config_data
            for c_data in c_datas:
                try:
                    c_data = ast.literal_eval(c_data)
                except (ValueError, SyntaxError):  # may already be data
                    try:
                        c_data = dict(c_data)  # Confirms c_data is type safe
                    except ValueError:  # c_data is not data
                        c_data = {}

                if check_config and c_data != config_data:
                    to_delete += [c_name]

        # Cleanup installed containers that aren't in config anymore.
        for c in installed_containers:
            if c not in config.keys() and c not in to_skip and clean_orphans:
                to_delete += [c]

        return to_delete

    def haskey(self, data, attribute, value=None, reverse=False, any=False,
               excluded_keys=[]):
        """Return dict data with a specific key.

        This filter will take a list of dictionaries (data)
        and will return the dictionnaries which have a certain key given
        in parameter with 'attribute'.
        If reverse is set to True, the returned list won't contain dictionaries
        which have the attribute.
        If any is set to True, the returned list will match any value in
        the list of values for "value" parameter which has to be a list.
        If we want to exclude items which have certain key(s); these keys
        should be added to the excluded_keys list. If excluded_keys is used
        with reverse, we'll just exclude the items which had a key from
        excluded_keys in the reversed list.

        :returns: list of dictionaries
        :rtype: `list`
        """
        return_list = []
        for i in data:
            to_skip = False
            for k, v in json.loads(json.dumps(i)).items():
                for e in excluded_keys:
                    if e in v:
                        to_skip = True
                        break
                if to_skip:
                    break
                if attribute in v and not reverse:
                    if value is None:
                        return_list.append(i)
                    else:
                        if isinstance(value, list) and any:
                            if v[attribute] in value:
                                return_list.append({k: v})
                        elif any:
                            raise TypeError("value has to be a list if any is "
                                            "set to True.")
                        else:
                            if v[attribute] == value:
                                return_list.append({k: v})
                if attribute not in v and reverse:
                    return_list.append({k: v})
        return return_list

    def dict_to_list(self, data):
        """Return a list of dictionaries."

        This filter will take a dictionary which itself containers
        multiple dictionaries; and will convert that to a list
        of dictionaries.
        """
        return_list = []
        for k, v in data.items():
            return_list.append({k: v})
        return return_list
