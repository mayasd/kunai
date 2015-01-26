import time
import threading
import ctypes
import traceback
import cStringIO
import json

from kunai.log import logger
from kunai.pubsub import pubsub
from kunai.httpdaemon import route, response
from kunai.evaluater import evaluater


class DetectorMgr(object):
    def __init__(self):
        self.clust = None
        
        
    def load(self, clust):
        self.clust = clust
    

    # Main thread for launching detectors
    def do_detector_thread(self):
       logger.log('DETECTOR thread launched', part='detector')
       cur_launchs = {}
       while not self.clust.interrupted:
           now = int(time.time())
           for (gname, gen) in self.clust.detectors.iteritems():
               logger.debug('LOOK AT DETECTOR', gen)
               interval   = int(gen['interval'].split('s')[0]) # todo manage like it should
               should_be_launch = gen['last_launch'] < int(time.time()) - interval
               if should_be_launch:
                   print "LAUNCHING DETECTOR", gen
                   gen['last_launch'] = int(time.time())
                   do_apply = evaluater.eval_expr(gen['apply_if'])
                   print "DO APPLY?", do_apply
                   if do_apply:
                       tags = gen['tags']
                       for tag in tags:
                           if tag not in self.clust.tags:
                               print "ADDING NEW TAGS", tag
           time.sleep(1)


    # main method to export http interface. Must be in a method that got
    # a self entry
    def export_http(self):
        
        @route('/agent/detectors/')
        @route('/agent/detectors')
        def get_detectors():
            response.content_type = 'application/json'
            return json.dumps(self.clust.detectors.values())

        
        @route('/agent/detectors/run')
        @route('/agent/detectors/run/:dname')        
        def _runrunrunr(dname=''):
            response.content_type = 'application/json'
            res = {}
            for (gname, gen) in self.clust.detectors.iteritems():
                if dname and dname != gname:
                    continue
                res[gname] = {'matched':False, 'tags':[], 'new_tags':[]}
                print "LAUNCHING DETECTOR", gen
                res[gname]['matched'] = evaluater.eval_expr(gen['apply_if'])
                if res[gname]['matched']:
                    res[gname]['tags'] = gen['tags']
                    for tag in res[gname]['tags']:
                       if tag not in self.clust.tags:
                           res[gname]['new_tags'].append(tag)
                           print "ADDING NEW TAGS", tag
            
            return json.dumps(res)
        
        
    
           

detecter = DetectorMgr()
