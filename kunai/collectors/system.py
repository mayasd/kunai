import os
import sys
import platform
import re
import traceback
import time
import multiprocessing
import socket

from kunai.log import logger
from kunai.collector import Collector


class System(Collector):
    def launch(self):
        logger.debug('getSystem: start')
        res = {}
        
        res['hostname'] = platform.node()
        res['fqdn']     = socket.getfqdn()
        
        res['os']             = {}
        res['os']['name']     = os.name
        res['os']['platform'] = sys.platform
        
        res['cpucount'] = multiprocessing.cpu_count()
        
        res['linux']             = {'distname':'','version':'','id':''}
        (distname, version, _id) = platform.linux_distribution()
        res['linux']['distname'] = distname
        res['linux']['version']  = version
        res['linux']['id']       = _id
        
        res['user']              = os.getlogin()
        res['uid']               = os.getuid()
        res['gid']               = os.getgid()

        res['publicip'] = ''
        try:
            res['publicip'] = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            pass
        
        logger.debug('getsystem: completed, returning')
        return res

