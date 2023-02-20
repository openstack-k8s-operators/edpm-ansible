#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2020 OpenStack Foundation
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

import os


def validate_playbook_dir(playbook_dir_path):
    if not os.path.exists(playbook_dir_path):
        raise Exception('ERROR: Playbook directory {} does not exist.'.format(
            playbook_dir_path))

    if not os.path.isdir(playbook_dir_path):
        raise Exception(
            'ERROR: Playbook directory {} is not a directory'.format(
                playbook_dir_path))


def tags_to_dict(resource_tags):
    tag_dict = dict()
    for tag in resource_tags:
        if not tag.startswith('edpm_'):
            continue
        try:
            key, value = tag.rsplit('=')
        except ValueError:
            continue
        if key == 'edpm_net_idx':
            value = int(value)
        tag_dict.update({key: value})

    return tag_dict
