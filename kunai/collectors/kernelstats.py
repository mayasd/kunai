import os
import sys
import platform
import re
import traceback
import time
from StringIO import StringIO


from kunai.log import logger
from kunai.collector import Collector


class KernelStats(Collector):
    def __init__(self, config, put_result=None):
        super(KernelStats, self).__init__(config, put_result)
        self.store = {}
        self.last_launch = 0.0

        
    def launch(self):
        now = int(time.time())
        diff = now - self.last_launch
        self.last_launch = now
        
        logger.debug('getKernelStats: start')

        if sys.platform == 'linux2':
            logger.debug('getKernelStats: linux2')

            try:
                logger.debug('getKernelStats: attempting open')
                lines = []
                with open('/proc/stat', 'r') as stats:
                    lines.extend(stats.readlines())
                with open('/proc/vmstat', 'r') as vmstat:
                    lines.extend(vmstat.readlines())
            except IOError, e:
                logger.error('getKernelStat: exception = %s', e)
                return False

            logger.debug('getKernelStat: open success, parsing')

            data = {}
            for line in lines:
                elts = line.split(' ', 1)
                # only look at keys
                if len(elts) != 2:
                    continue
                try:
                    data[elts[0]] = long(elts[1])
                except ValueError: # not an int? skip this value
                    continue
            
            # Now loop through each interface
            by_sec_keys = ['ctxt', 'processes', 'pgfault', 'pgmajfault']
            to_add = {}
            for (k,v) in data.iteritems():
                if k in by_sec_keys:
                    if k in self.store:
                        to_add['%s/s' % k] = (v - self.store[k]) / diff
                    else:
                        to_add['%s/s' % k] = 0
                    self.store[k] = data[k]
            for k in by_sec_keys:
                del data[k]
            data.update(to_add)
            logger.debug('getKernelStats: completed, returning')

            return data

        else:
            logger.debug('getKernelStats: other platform, returning')
            return False
