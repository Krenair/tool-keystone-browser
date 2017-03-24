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

import ldap3


def ldap_conn():
    """Get an ldap connection

    Return value can be used as a context manager
    """
    servers = ldap3.ServerPool([
        ldap3.Server('ldap-labs.eqiad.wikimedia.org'),
        ldap3.Server('ldap-labs.codfw.wikimedia.org'),
    ], ldap3.ROUND_ROBIN, active=True, exhaust=True)
    return ldap3.Connection(
        servers, read_only=True, auto_bind=True)


def in_list(attr, items):
    """Make a search filter that will match all entries having attr with
    values in the given list.

    Similar to an SQL ``WHERE attr in (<list>)`` clause.

    >>> in_list('uid', ['a', 'b', 'c'])
    '(|(uid=a)(uid=b)(uid=c))'
    """
    return '(|{})'.format(''.join(
        ['({}={})'.format(attr, item) for item in items]
    ))


def get_users_by_uid(uids):
    """Get a list of dicts of user information."""
    ret = []
    if not uids:
        return ret
    with ldap_conn() as conn:
        conn.search(
            'ou=people,dc=wikimedia,dc=org',
            in_list('uid', uids),
            ldap3.SUBTREE,
            attributes=['uid', 'cn'],
            time_limit=5
        )
        for resp in conn.response:
            attribs = resp.get('attributes')
            # LDAP attributes come back as a dict of lists. We know that there
            # is only one value for each list, so unwrap it
            ret.append({
                'uid': attribs['uid'][0],
                'cn': attribs['cn'][0],
            })
    return ret