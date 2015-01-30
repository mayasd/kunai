#!/usr/bin/env python

# -*- coding: utf-8 -*-

# Copyright (C) 2014:
#    Gabes Jean, naparuba@gmail.com


import os
import sys
import base64
import uuid
import time
import json
import socket

# try pygments for pretty printing if available
from pprint import pprint
try:
    import pygments
    import pygments.lexers
    import pygments.formatters
except ImportError:
    pygments = None


from kunai.cluster import Cluster
from kunai.log import cprint, logger
from kunai.version import VERSION
from kunai.launcher import Launcher
from kunai.unixclient import get_json, get_local, request_errors
from kunai.cli import get_kunai_json, get_kunai_local, print_info_title, print_2tab

def do_detect_list():
    try:
        (code, r) = get_kunai_local('/agent/detectors')
    except request_errors, exp:
        logger.error(exp)
        return

    try:
        d = json.loads(r)
    except ValueError, exp:# bad json
        logger.error('Bad return from the server %s' % exp)
        return

    e = []
    for i in d:
        e.append( (i['name'], ','.join(i['tags']) ) )

    # Normal agent information
    print_info_title('Detectors')
    print_2tab(e)
    

def do_detect_run():
    try:
        (code, r) = get_kunai_local('/agent/detectors/run')
    except request_errors, exp:
        logger.error(exp)
        return

    try:
        d = json.loads(r)
    except ValueError, exp:# bad json
        logger.error('Bad return from the server %s' % exp)
        return

    print_info_title('Detectors results')
    all_tags = []
    new_tags = []
    for (k, v) in d.iteritems():
        all_tags.extend(v['tags'])
        new_tags.extend(v['new_tags'])
    e = [('Tags', ','.join(all_tags))]
    e.append( ('New tags', {'value': ','.join(new_tags), 'color':'green'}) )
    print_2tab(e)    
    


exports = {
    do_detect_list : {
        'keywords': ['detectors', 'list'],
        'args': [
            ],
        'description': 'Show detectors list'
        },


    do_detect_run : {
        'keywords': ['detectors', 'run'],
        'args': [
            ],
        'description': 'Run detectors'
        },
}
