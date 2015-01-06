#!/usr/bin/env python
import json
import time
import sys
from pprint import pprint
try:
    from docker import Client
except ImportError:
    Client = None

from kunai.stats import STATS
from kunai.log import logger
from kunai.threadmgr import threader
from kunai.now import NOW
from kunai.httpdaemon import route, response
from kunai.cgroups import cgroupmgr

def lower_dict(d):    
    nd = {}
    for k,v in d.iteritems():
        nk = k.lower()
        if isinstance(v, dict): # yes, it's recursive :)
            v = lower_dict(v)
        nd[nk] = v
    return nd




class DockerManager(object):
    def __init__(self):
        self.con = None
        self.containers = {}
        # We got an object, we can fill the http daemon part
        self.export_http()
        # last stats computation for containers, some are rate
        # we must compare
        self.stats = {}
        self.last_stats = 0
        # We also aggregate stats to the images level
        self.images_stats = {}

        
    def get_info(self):
        r = {'enabled':     Client is not None,
             'connected' :  self.con is not None,
             'containers':  self.containers,
        }
        return r


    def get_stats(self):
        r = {'containers': self.stats,
             'images'    : self.images_stats,
            }
        return r
    
        
    def launch(self):
        if not Client:
            logger.warning('Missing docker lib')
            return
        t = threader.create_and_launch(self.do_loop, name='docker-loop')
        t = threader.create_and_launch(self.do_stats_loop, name='docker-stats-loop')        
        


    def connect(self):
        if not self.con:
            try:
                self.con = Client(base_url='unix://var/run/docker.sock')
            except Exception, exp:
                logger.debug('Cannot connect to docker %s' % exp)
                self.con = None


    def load_container(self, _id):
        inspect = self.con.inspect_container(_id)
        c = lower_dict(inspect)
        logger.debug('LOADED NEW CONTAINER %s' % c)
        self.containers[_id] = c
        
    
    def load_containers(self):
        if not self.con:
            return
        conts = self.con.containers()
        for c in conts:
            _id = c.get('Id')
            self.load_container(_id)
            print "Container", self.containers[_id]


    def compute_stats(self):
        cids = self.containers.keys()
        stats = cgroupmgr.get_containers_metrics(cids)
        print 'RAW STATS', stats
        now = time.time()
        for (cid, nst) in stats.iteritems():
            c_stats = self.stats.get(cid, {})
            if self.last_stats != 0:
                diff = now - self.last_stats
            else:
                diff = 0
            
            for d in nst:
                k = '%s.%s' % (d['scope'], d['mname'])
                _type = d['type']
                scope = d['scope']
                if _type == 'gauge':
                    c_stats[k] = {'type':_type, 'key':k, 'value':d['value'], 'scope':scope}
                elif _type == 'rate':
                    print "HEEH", c_stats.get(k, {})
                    o = c_stats.get(k, {})
                    rate_f = d['rate_f']
                    if o == {}:
                        # If there is no old value, don't need to compare rate as
                        # there is no older value
                        c_stats[k] = {'type':_type, 'key':k, 'value':None, 'raw_value':d['value'], 'scope':scope}
                        continue
                    print "COMPARING", o['raw_value'], d['value']
                    if rate_f is None:
                        rate_v = (d['value'] - o['raw_value']) / diff
                    else:
                        print 'RATE V', o['raw_value'], d['value'], diff
                        rate_v = rate_f(o['raw_value'], d['value'], diff)
                        print rate_v
                    c_stats[k] = {'type':_type, 'key':k, 'value':rate_v, 'raw_value':d['value'], 'scope':scope}
                    
            self.stats[cid] = c_stats
            print 'COMPUTE', self.stats


        # Keep stats only for the known containers
        to_del = []
        for cid in self.stats:
            if cid not in self.containers:
                to_del.append(cid)
        for cid in to_del:
            del self.containers[cid]
            
        # tag the current time so we can diff rate in the future
        self.last_stats = now

        # Now pack the value based on the images if need
        self.aggregate_stats()
        

    # pack stats based on the container id but also merge/sum values for the
    # same images
    def aggregate_stats(self):
        if self.con is None:
            return
        images = {}
        for (cid, cont) in self.containers.iteritems():
            # avoid containers with no stats, it's not a good thing here :)
            if cid not in self.stats:
                continue
            print 'CONT'
            pprint(cont)
            img = cont.get('image')
            if not img in images:
                images[img] = []
            images[img].append(cid)

        img_stats = {}
        print "IMAGES", images
        for (img, cids) in images.iteritems():
            print 'IMAGE', img
            print cids
            s = {}
            img_stats[img] = s
            for cid in cids:
                for (k, d) in self.stats[cid].iteritems():
                    # if the first value, keep it as a whole
                    if s.get(k, None) is None:
                        s[k] = d
                        continue
                    print k, d
                    print s[k]
                    c = s[k]
                    
                    if d['value'] is not None:
                        if c['value'] is None:
                            c['value'] = d['value']
                        else:
                            c['value'] += d['value']
            print 'S'
            print img, s

        images_stats = {}
        # Now get images
        docker_images = self.con.images()
        for (img_id, s) in img_stats.iteritems():
            img = None
            for d in docker_images:
                if d['Id'] == img_id:
                    img = d
                    break
            # No more image?
            if img is None:
                continue
            print "MATCH", img, s
            imgname = img['RepoTags'][0]
            images_stats[imgname] = s
        self.images_stats = images_stats
        print 'Finally compute', self.images_stats


    def do_stats_loop(self):
        while True:
            self.connect()
            if not self.con:
                time.sleep(1) # do not hammer the connexion
                continue
            # Each seconds we are computing several stats on the containers and images
            # thanks to cgroups
            self.compute_stats()
            time.sleep(10)
            
            
    def do_loop(self):
        self.connect()
        self.load_containers()
        while True:
            print "LOOP ON THE DOCKER"
            self.connect()
            if not self.con:
                time.sleep(1) # do not hammer the connexion
                continue
            # now manage events and lock on it
            evts = self.con.events() # can lock here
            for ev in evts:
                evdata = json.loads(ev)
                _id = evdata["id"]
                status = evdata["status"]
                if status in ("die", "stop"):
                    if _id in self.containers:
                        logger.debug('removing a container %s' % _id)
                        del self.containers[_id]
                        # stats will be cleaned on the next computation
                    else:
                        logger.error('Asking to remove an unknow container? %s' % _id)
                elif status == 'start':
                    self.load_container(_id)
                else:
                    logger.debug('UNKNOWN EVENT IN DOCKER %s' % status)

                    
    # main method to export http interface. Must be in a method that got
    # a self entry
    def export_http(self):

        @route('/docker/')
        @route('/docker')
        def get_docker():
            response.content_type = 'application/json'
            return json.dumps(self.con is not None)
    

        @route('/docker/containers')
        @route('/docker/containers/')
        def get_containers():
            response.content_type = 'application/json'
            return json.dumps(self.containers.values())

        
        @route('/docker/containers/:_id')
        def get_container(_id):
            response.content_type = 'application/json'
            cont = self.containers.get(_id, None)
            return json.dumps(cont)
    

        @route('/docker/images')
        @route('/docker/images/')
        def get_images():
            response.content_type = 'application/json'
            if self.con is None:
                return json.dumps(None)
            imgs = self.con.images()
            r = [lower_dict(d) for d in imgs]
            return json.dumps(r)

        
        @route('/docker/images/:_id')
        def get_images(_id):
            response.content_type = 'application/json'
            if self.con is None:
                return json.dumps(None)
            imgs = self.con.images()
            for d in imgs:
                if d['Id'] == _id:
                    return json.dumps(lower_dict(d))
            return json.dumps(None)

        
        @route('/docker/stats')
        @route('/docker/stats/')
        def _stats():
            response.content_type = 'application/json'
            return self.get_stats()
        
        

dockermgr = DockerManager()
                    


    
