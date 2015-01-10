import time
import platform
import traceback
import subprocess
import random
from collections import defaultdict

from kunai.stats import STATS
from kunai.log import logger
from kunai.threadmgr import threader
from kunai.now import NOW
from kunai.collectors import get_collectors
from kunai.stop import stopper


class CollectorManager:
    def __init__(self):
        self.collectors = {}
        self.interrupted = False
        self.cfg_data = {}

    def load_collector(self, cls):
        colname = cls.__name__.lower()
        logger.debug('Loading collector %s from class %s' % (colname, cls))
        try:
            inst = cls(self.cfg_data)
        except Exception, exp:
            
            logger.error('Cannot load the %s collector: %s' % (cls, traceback.format_exc()))
            return
        e = {
            'name': colname,
            'inst': inst,
            'last_check': 0,
            'next_check': int(time.time()) + int(random.random())*10,
            }
        self.collectors[cls] = e
        

    def load_collectors(self, cfg_data):
        self.cfg_data = cfg_data
        get_collectors(self)
        
        

    # Main thread for launching collectors
    def do_collector_thread(self):
       logger.log('COLLECTOR thread launched', part='check')
       cur_launchs = {}
       while not stopper.interrupted:
           #logger.debug('... collectors...')
           now = int(time.time())
           for (cls, e) in self.collectors.iteritems():
               colname = e['name']
               inst = e['inst']
               # maybe a collection is already running
               if colname in cur_launchs:
                   continue
               if now >= e['next_check']:
                   logger.debug('COLLECTOR: launching collector %s' % colname, part='check')
                   t = threader.create_and_launch(inst.main, name='collector-%s' % colname)#, args=(,))
                   cur_launchs[colname] = t
                   e['next_check'] += 10

           to_del = []
           for (colname, t) in cur_launchs.iteritems():
               if not t.is_alive():
                   t.join()
                   to_del.append(colname)
           for colname in to_del:
               del cur_launchs[colname]

           time.sleep(1)


collectormgr = CollectorManager()
