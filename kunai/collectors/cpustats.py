import os
import sys
import platform
import re
import urllib
import urllib2
import traceback
import time
from StringIO import StringIO
import subprocess


from kunai.log import logger
from kunai.collector import Collector


class CpuStats(Collector):
    def launch(self):
        logger.debug('getCPUStats: start')

        cpuStats = {}

        if sys.platform == 'linux2':
            logger.debug('getCPUStats: linux2')

            headerRegexp = re.compile(r'.*?([%][a-zA-Z0-9]+)[\s+]?')
            itemRegexp = re.compile(r'.*?\s+(\d+)[\s+]?')
            itemRegexpAll = re.compile(r'.*?\s+(all)[\s+]?')
            valueRegexp = re.compile(r'\d+\.\d+')
            proc = None
            try:
                cmd = 'mpstat -P ALL 1 1'
                stats = self.execute_shell(cmd)
                if not stats:
                    return None
                stats = stats.split('\n')
                header = stats[2]
                headerNames = re.findall(headerRegexp, header)
                device = None
                
                for statsIndex in range(3, len(stats)): # no skip "all"
                    row = stats[statsIndex]

                    if not row: # skip the averages
                        break
                    deviceMatchAll = re.match(itemRegexpAll, row)                    
                    deviceMatch = re.match(itemRegexp, row)
                    if deviceMatchAll is not None:
                        device = 'cpuall'
                    elif deviceMatch is not None:
                        device = 'cpu%s' % deviceMatch.groups()[0]
                    
                    values = re.findall(valueRegexp, row.replace(',', '.'))
                    
                    cpuStats[device] = {}
                    for headerIndex in range(0, len(headerNames)):
                        headerName = headerNames[headerIndex]
                        cpuStats[device][headerName] = float(values[headerIndex])

            except Exception, ex:
                logger.error('getCPUStats: exception = %s', traceback.format_exc())
                return False
        else:
            logger.debug('getCPUStats: unsupported platform')
            return False

        logger.debug('getCPUStats: completed, returning')
        return cpuStats

