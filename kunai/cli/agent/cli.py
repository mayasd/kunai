#!/usr/bin/env python

# -*- coding: utf-8 -*-

# Copyright (C) 2014:
#    Gabes Jean, naparuba@gmail.com


import os
import sys
import base64
import uuid
#import socket
import time
import json
#import urllib2
#import urllib
#import httplib
#from urlparse import urlsplit
import socket
try:
    import requests as rq
except ImportError:
    rq = None

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


# If not requests we should exit because the
# daemon cannot be in a good shape at all
if rq is None:
    logger.error('Missing python-requests lib, please install it')
    sys.exit(2)


# Will be populated by the shinken CLI command
CONFIG = None

def get_local_socket():
    return CONFIG.get('socket', '/var/lib/kunai/kunai.sock')


from kunai.unixclient import get_json, get_local, request_errors


def get_kunai_json(uri):
    local_socket = get_local_socket()
    return get_json(uri, local_socket)


def get_kunai_local(uri):
    local_socket = get_local_socket()
    return get_local(uri, local_socket)
    

############# ********************        MEMBERS management          ****************###########    

def do_members():
    try:
        members = get_kunai_json('/agent/members').values()
    except request_errors, exp:
        logger.error('Cannot join kunai agent: %s' % exp)
        sys.exit(1)
    members = sorted(members, key=lambda e:e['name'])
    max_name_size = max([ len(m['name']) for m in members ])
    max_addr_size = max([ len(m['addr']) + len(str(m['port'])) + 1 for m in members ])    
    for m in members:
        name = m['name']
        tags = m['tags']
        port = m['port']
        addr = m['addr']
        state = m['state']
        cprint('%s  ' % name.ljust(max_name_size), end='')
        c = {'alive':'green', 'dead':'red', 'suspect':'yellow', 'leave':'cyan'}.get(state, 'cyan')
        cprint(state, color=c, end='')
        s = ' %s:%s ' % (addr, port)
        s = s.ljust(max_addr_size+2) # +2 for the spaces
        cprint(s, end='')
        cprint(' %s ' % ','.join(tags))        



def do_leave(name=''):
    # Lookup at the localhost name first
    if not name:
        try:
            (code, r) = get_kunai_local('/agent/name')
        except request_errors, exp:
            logger.error(exp)
            return
        name = r
    try:
        (code, r) = get_kunai_local('/agent/leave/%s' % name)        
    except request_errors, exp:
        logger.error(exp)
        return
    
    if code != 200:
        logger.error('Node %s is missing' % name)
        print r
        return
    cprint('Node %s is set to leave state' % name,end='')
    cprint(': OK', color='green')


def do_state(name=''):
    uri = '/agent/state/%s' % name
    if not name:
        uri = '/agent/state'
    try:
        (code, r) = get_kunai_local(uri)
    except request_errors, exp:
        logger.error(exp)
        return

    try:
        d = json.loads(r)
    except ValueError, exp:# bad json
        logger.error('Bad return from the server %s' % exp)
        return

    print 'Services:'
    for (sname, service) in d['services'].iteritems():
        state = service['state_id']
        cprint('\t%s ' % sname.ljust(20),end='')
        c = {0:'green', 2:'red', 1:'yellow', 3:'cyan'}.get(state, 'cyan')
        state = {0:'OK', 2:'CRITICAL', 1:'WARNING', 3:'UNKNOWN'}.get(state, 'UNKNOWN')
        cprint('%s - ' % state.ljust(8), color=c, end='')
        output = service['check']['output']
        cprint(output.strip(), color='grey')

    print "Checks:"
    for (cname, check) in d['checks'].iteritems():
        state = check['state_id']
        cprint('\t%s ' % cname.ljust(20),end='')
        c = {0:'green', 2:'red', 1:'yellow', 3:'cyan'}.get(state, 'cyan')
        state = {0:'OK', 2:'CRITICAL', 1:'WARNING', 3:'UNKNOWN'}.get(state, 'UNKNOWN')
        cprint('%s - ' % state.ljust(8), color=c, end='')
        output = check['output']
        cprint(output.strip(), color='grey')
        


def do_version():
    cprint(VERSION)
    
    
def print_info_title(title):
    #t = title.ljust(15)
    #s = '=================== %s ' % t
    #s += '='*(50 - len(s))
    #cprint(s)
    cprint('========== [%s]:' % title)


def print_2tab(e, capitalize=True, col_size=20):
    for (k, v) in e:
        label = k
        if capitalize:
            label = label.capitalize()
        s = '%s: ' % label
        s = s.ljust(col_size)
        cprint(s, end='', color='blue')
        # If it's a dict, we got additiionnal data like color or type
        if isinstance(v, dict):
            color = v.get('color', 'green')
            _type = v.get('type', 'std')
            value = v.get('value')
            cprint(value, color=color)
        else:
            cprint(v, color='green')
    
    
def do_info(show_logs):
    d = get_kunai_json('/agent/info')
    
    logs = d.get('logs')
    version = d.get('version')
    pid = d.get('pid')
    name = d.get('name')
    port = d.get('port')
    nb_threads = d.get('threads')['nb_threads']
    httpservers = d.get('httpservers', {'internal':None, 'external':None})
    socket_path = d.get('socket')
    _uuid = d.get('uuid')
    graphite = d.get('graphite')
    statsd = d.get('statsd')
    websocket = d.get('websocket')
    dns = d.get('dns')
    _docker = d.get('docker')
    collectors = d.get('collectors')

    e = [('name', name), ('uuid',_uuid), ('version', version), ('pid', pid), ('port',port), ('socket',socket_path), ('threads', nb_threads)]

    # Normal agent information
    print_info_title('Kunai Daemon')
    print_2tab(e)
    
    # Normal agent information
    int_server = httpservers['external']
    if int_server:
        e = (('threads', int_server['nb_threads']), ('idle_threads', int_server['idle_threads']), ('queue', int_server['queue']) )
        print_info_title('HTTP (LAN)')
        print_2tab(e)

    # Unix socket http daemon
    int_server = httpservers['internal']
    if int_server:
        e = (('threads', int_server['nb_threads']), ('idle_threads', int_server['idle_threads']), ('queue', int_server['queue']) )
        print_info_title('HTTP (Unix Socket)')
        print_2tab(e)
        
    # Now DNS part
    print_info_title('DNS')
    if dns is None:
        cprint('No dns configured')
    else:
        w = dns
        e = [('enabled', w['enabled']), ('port', w['port']), ('domain',w['domain']) ]
        print_2tab(e)
    
    # Now websocket part
    print_info_title('Websocket')
    if websocket is None:
        cprint('No websocket configured')
    else:
        w = websocket
        st = d.get('websocket_info', None)
        e = [('enabled', w['enabled']), ('port', w['port']) ]
        if st:
            e.append( ('Nb connexions', st.get('nb_connexions')) )
        print_2tab(e)

    # Now graphite part
    print_info_title('Graphite')
    if graphite is None:
        cprint('No graphite configured')
    else:
        g = graphite
        e = [('enabled', g['enabled']), ('port', g['port']), ('udp', g['udp']), ('tcp', g['tcp']) ]
        print_2tab(e)

    # Now statsd part
    print_info_title('Statsd')
    if statsd is None:
        cprint('No statsd configured')
    else:
        s = statsd
        e = [('enabled', s['enabled']), ('port', s['port']), ('interval', s['interval'])]
        print_2tab(e)

    # Now collectors part
    print_info_title('Collectors')
    cnames = collectors.keys()
    cnames.sort()
    e = []
    for cname in cnames:
        v = collectors[cname]
        color = 'green'
        if not v['active']:
            color = 'grey'
        e.append( (cname, {'value':v['active'], 'color':color}) )
    print_2tab(e, capitalize=False)
    

    # Now statsd part
    print_info_title('Docker')
    _d = _docker
    if _d['connected']:
        e = [('enabled', _d['enabled']), ('connected', _d['connected']),
             ('version',_d['version']), ('api', _d['api']),
              ('containers', len(_d['containers'])),
             ('images', len(_d['images'])),
        ]
    else:
        e = [
            ('enabled', {'value':_d['enabled'], 'color':'grey'}),
            ('connected', {'value':_d['connected'], 'color':'grey'}),
            ]
            
    print_2tab(e)
    
    # Show errors logs if any
    print_info_title('Logs')
    errors  = logs.get('ERROR')
    warnings = logs.get('WARNING')
 
    # Put warning and errors in red/yellow if need only
    e = []
    if len(errors) > 0:
        e.append( ('error', {'value':len(errors), 'color':'red'}) )
    else:
        e.append( ('error', len(errors)) )
    if len(warnings) > 0:
        e.append( ('warning', {'value':len(warnings), 'color':'yellow'}) )
    else:
        e.append( ('warning', len(warnings)) )

    print_2tab(e)

    if show_logs:
        if len(errors) > 0:
            print_info_title('Error logs')
            for s in errors:
                cprint(s, color='red')
    
        if len(warnings) > 0:
            print_info_title('Warning logs')
            for s in warnings:
                cprint(s, color='yellow')
        
    logger.debug('Raw information: %s' % d)
    


def do_docker_stats():
    d = get_kunai_json('/docker/stats')
    scontainers = d.get('containers')
    simages     = d.get('images')

    print_info_title('Docker Stats')
    for (cid, stats) in scontainers.iteritems():
        print_info_title('Container:%s' % cid)
        keys = stats.keys()
        keys.sort()
        e = []
        for k in keys:
            sd = stats[k]
            e.append( (k, sd['value']) )
            
        # Normal agent information
        print_2tab(e, capitalize=False, col_size=30)

    for (cid, stats) in simages.iteritems():
        print_info_title('Image:%s (sum)' % cid)
        keys = stats.keys()
        keys.sort()
        e = []
        for k in keys:
            sd = stats[k]
            e.append( (k, sd['value']) )
            
        # Normal agent information
        print_2tab(e, capitalize=False, col_size=30)




def do_collectors_show(name='', all=False):
    collectors = get_kunai_json('/collectors')
    disabled = []
    for (cname, d) in collectors.iteritems():
        if name and not name == cname:
            continue
        if not name and not d['active'] and not all:
            disabled.append(d)
            continue
        print_info_title('Collector %s' % cname)
        # for pretty print in color, need to have both pygments and don't
        # be in a | or a file dump >, so we need to have a tty ^^
        if pygments and sys.stdout.isatty():
            lexer = pygments.lexers.get_lexer_by_name("json", stripall=False)
            formatter = pygments.formatters.TerminalFormatter()
            code = json.dumps(d, indent=4)
            result = pygments.highlight(code, lexer, formatter)
            print result
        else:
            pprint(d)
    if len(disabled) > 0:
        print_info_title('Disabled collectors')
        cprint(','.join([ d['name'] for d in disabled]), color='grey')
    

    
# Main daemon function. Currently in blocking mode only
def do_start(daemon):
    cprint('Starting kunai daemon', color='green')
    lock_path = CONFIG.get('lock', '/var/run/kunai.pid')
    l = Launcher(lock_path=lock_path)
    l.do_daemon_init_and_start(is_daemon=daemon)
    # Here only the last son reach this
    l.main()
    
    

def do_stop():
    try:
        (code, r) = get_kunai_local('/stop')
    except request_errors, exp:
        logger.error(exp)
        return
    cprint(r, color='green')
    
    
    
def do_join(seed=''):
    if seed == '':
        logger.error('Missing target argument. For example 192.168.0.1:6768')
        return
    try:
        (code, r) = get_kunai_local('/agent/join/%s' % seed)
    except request_errors, exp:
        logger.error(exp)
        return
    try:
        b = json.loads(r)
    except ValueError, exp:# bad json
        logger.error('Bad return from the server %s' % exp)
        return
    cprint('Joining %s : ' % seed, end='')
    if b:
        cprint('OK', color='green')
    else:
        cprint('FAILED', color='red')



def do_keygen():
    k = uuid.uuid1().hex[:16]
    cprint('UDP Encryption key: (aka encryption_key)', end='')
    cprint(base64.b64encode(k), color='green')
    print ''
    try:
        from Crypto.PublicKey import RSA
    except ImportError:
        logger.error('Missing python-crypto module for RSA keys generation, please install it')
        return
    key = RSA.generate(2048)
    privkey = key.exportKey()
    pub_key = key.publickey()
    pubkey = pub_key.exportKey()
    print "Private RSA key (2048). (aka master_key_priv for for file mfkey.priv)"
    cprint(privkey, color='green')
    print ''
    print "Public RSA key (2048). (aka master_key_pub for file mfkey.pub)"
    cprint(pubkey, color='green')
    print ''



def do_exec(tag='*', cmd='uname -a'):
    if cmd == '':
        logger.error('Missing command')
        return
    try:
        (code, r) = get_kunai_local('/exec/%s?cmd=%s' % (tag, cmd))
    except request_errors, exp:
        logger.error(exp)
        return
    print r
    cid = r
    print "Command group launch as cid", cid
    time.sleep(5) # TODO: manage a real way to get the result..
    try:
        (code, r) = get_kunai_local('/exec-get/%s' % cid)
    except request_errors, exp:
        logger.error(exp)
        return
    j = json.loads(r)
    #print j
    res = j['res']
    for (uuid, e) in res.iteritems():
        node = e['node']
        nname = node['name']
        color = {'alive':'green', 'dead':'red', 'suspect':'yellow', 'leave':'cyan'}.get(node['state'], 'cyan')
        cprint(nname, color=color)
        cprint('Return code:', end='')
        color = {0:'green', 1:'yellow', 2:'red'}.get(e['rc'], 'cyan')
        cprint(e['rc'], color=color)
        cprint('Output:', end='')
        cprint(e['output'].strip(), color=color)
        if e['err']:
            cprint('Error:', end='')
            cprint(e['err'].strip(), color='red')
        print ''
            

exports = {
    do_members : {
        'keywords': ['members'],
        'args': [],
        'description': 'List the cluster members'
        },

    do_start : {
        'keywords': ['agent', 'start'],
        'args': [
            {'name' : '--daemon', 'type':'bool', 'default':False, 'description':'Start kunai into the background'},
        ],
        'description': 'Start the kunai daemon'
        },

    do_stop : {
        'keywords': ['agent', 'stop'],
        'args': [],
        'description': 'Stop the kunai daemon'
        },

    do_version : {
        'keywords': ['version'],
        'args': [],
        'description': 'Print the daemon version'
        },

    do_info : {
        'keywords': ['info'],
        'args': [
            {'name' : '--show-logs', 'default':False, 'description':'Dump last warning & error logs', 'type':'bool'},
            ],
        'description': 'Show info af a daemon'
        },

    do_keygen : {
        'keywords': ['keygen'],
        'args': [],
        'description': 'Generate a encryption key'
        },

    do_exec : {
        'keywords': ['exec'],
        'args': [
            {'name' : 'tag', 'default':'', 'description':'Name of the node tag to execute command on'},
            {'name' : 'cmd', 'default':'uname -a', 'description':'Command to run on the nodes'},
            ],
        'description': 'Execute a command (default to uname -a) on a group of node of the good tag (default to all)'
        },

    do_join : {
        'keywords': ['join'],
        'description': 'Join another node cluster',
        'args': [
            {'name' : 'seed', 'default':'', 'description':'Other node to join. For example 192.168.0.1:6768'},
            ],
        },

    do_leave : {
        'keywords': ['leave'],
        'description': 'Put in leave a cluster node',
        'args': [
            {'name' : 'name', 'default':'', 'description':'Name of the node to force leave. If void, leave our local node'},
            ],
        },


    do_state : {
        'keywords': ['state'],
        'description': 'Print the state of a node',
        'args': [
            {'name' : 'name', 'default':'', 'description':'Name of the node to print state. If void, take our localhost one'},
            ],
        },

    do_docker_stats : {
        'keywords': ['docker', 'stats'],
        'args': [],
        'description': 'Show stats from docker containers and images'
        },

    do_collectors_show : {
        'keywords': ['collectors', 'show'],
        'args': [
            {'name' : 'name', 'default':'', 'description':'Show a specific'},
            {'name' : '--all', 'default':False, 'description':'Show all collectors, even diabled one', 'type':'bool'},            
            ],
        'description': 'Show collectors informations'
        },

    

    }
