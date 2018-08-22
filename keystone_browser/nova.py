#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of the Keystone browser
#
# Copyright (c) 2017 Bryan Davis and contributors
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

import functools

from novaclient import client

from . import cache
from . import keystone


@functools.lru_cache(maxsize=None)
def nova_client(project, region):
    return client.Client(
        '2.12',
        session=keystone.session(project),
        endpoint_type='public',
        timeout=2,
        region_name=region
    )


@functools.lru_cache()
def get_regions():
    nova = client.Client('2.12', session=keystone.session, endpoint_type='public')
    region_recs = nova.regions.list()
    return [region.id for region in region_recs]


def project_servers(project):
    """Get a list of information about servers in the given project.

    Data returned for each server is described at
    https://developer.openstack.org/api-ref/compute/?expanded=list-servers-detailed-detail#listServers
    """
    key = 'nova:project_servers:{}'.format(project)
    data = cache.CACHE.load(key)
    if data is None:
        data = []
        for region in get_regions():
            nova = nova_client(project, region)
            data.extend([
                s._info for s in nova.servers.list(
                    detailed=True,
                    sort_keys=['display_name'],
                    sort_dirs=['asc'],
                )
            ])

        cache.CACHE.save(key, data, 300)
    return data


def flavors(project):
    """Get a dict of flavor details indexed by id."""
    key = 'nova:flavors:{}'.format(project)
    data = cache.CACHE.load(key)
    if data is None:
        data = {}
        for region in get_regions():
            nova = nova_client(project, region)
            for f in nova.flavors.list():
                data[f._info['id']] = f._info

        cache.CACHE.save(key, data, 3600)
    return data


def all_servers():
    """Get a list of all servers in all projects."""
    key = 'keystone:all_servers'
    data = cache.CACHE.load(key)
    if data is None:
        data = []
        all_projects = keystone.all_projects()
        for project in all_projects:
            if project != 'admin':
                data += project_servers(project)
        cache.CACHE.save(key, data, 300)
    return data


def server(fqdn):
    """Get information about a server by fqdn."""
    key = 'nova:server:{}'.format(fqdn)
    data = cache.CACHE.load(key)
    if data is None:
        name, project, _ = fqdn.split('.', 2)
        servers = []
        for region in get_regions():
            nova = nova_client(project, region)
            reg_servers = nova.servers.list(
                detailed=True,
                search_opts={
                    'name': '^{}$'.format(name),
                },
            )
            if reg_servers:
                servers.extend(reg_servers)

        if servers:
            data = servers[0]._info
        else:
            data = {}
        cache.CACHE.save(key, data, 300)
    return data
