import os
import time
import platform
import traceback
import subprocess
import random
import threading
import glob
import imp
import json
import copy
from collections import defaultdict

from kunai.stats import STATS
from kunai.log import logger
from kunai.threadmgr import threader
from kunai.now import NOW
from kunai.stop import stopper
from kunai.httpdaemon import route, response
from kunai.collector import Collector

def get_collectors(self):
    collector_dir = os.path.dirname(__file__)
    p = collector_dir+'/collectors/*py'
    logger.debug('Loading collectors from ', p)
    collector_files = glob.glob(p)
    for f in collector_files:
        fname = os.path.splitext(os.path.basename(f))[0]
        try:
            m = imp.load_source('collector%s' % fname, f)
        except Exception, exp:
            logger.error('Cannot load collector %s: %s' % (fname, exp))
            continue

    collector_clss = Collector.get_sub_class()
    for ccls in collector_clss:
        # skip base module Collector
        if ccls == Collector:
            continue
        # Maybe this collector is already loaded
        if ccls in self.collectors:
            continue
        self.load_collector(ccls)


class CollectorManager:
    def __init__(self):
        self.collectors = {}
        self.interrupted = False
        self.cfg_data = {}

        # results from the collectors, keep ony the last run
        self.results_lock = threading.RLock()
        self.results = {}

        self.export_http()
        

    def load_collector(self, cls):
        colname = cls.__name__.lower()
        logger.debug('Loading collector %s from class %s' % (colname, cls))
        try:
            # also give it our put result callback
            inst = cls(self.cfg_data, put_result=self.put_result)
        except Exception, exp:
            
            logger.error('Cannot load the %s collector: %s' % (cls, traceback.format_exc()))
            return
        e = {
            'name': colname,
            'inst': inst,
            'last_check': 0,
            'next_check': int(time.time()) + int(random.random())*10,
            'results': None,
            }
        self.collectors[colname] = e
        

    def load_collectors(self, cfg_data):
        self.cfg_data = cfg_data
        get_collectors(self)
        

    # Our collector threads will put back results so beware of the threads
    def put_result(self, cname, res):
        if cname in self.collectors:
            self.collectors[cname]['results'] = res
        

    # Main thread for launching collectors
    def do_collector_thread(self):
       logger.log('COLLECTOR thread launched', part='check')
       cur_launchs = {}
       while not stopper.interrupted:
           #logger.debug('... collectors...')
           now = int(time.time())
           for (colname, e) in self.collectors.iteritems():
               colname = e['name']
               inst = e['inst']
               # maybe a collection is already running
               if colname in cur_launchs:
                   continue
               if now >= e['next_check']:
                   logger.debug('COLLECTOR: launching collector %s' % colname, part='check')
                   t = threader.create_and_launch(inst.main, name='collector-%s' % colname)
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


    # main method to export http interface. Must be in a method that got
    # a self entry
    def export_http(self):
        @route('/collectors/')
        @route('/collectors')
        def get_collectors():
            response.content_type = 'application/json'
            res = {}
            for (ccls, e) in self.collectors.iteritems():
                c = copy.copy(e)
                # insta are not serializable
                del c['inst']
                res[c['name']] = c
            print 'RES', res
            return json.dumps(res)

        
        @route('/collectors/:_id')
        def get_container(_id):
            response.content_type = 'application/json'
            cont = self.collectors.get(_id, None)
            return json.dumps(cont)
    
       


collectormgr = CollectorManager()
