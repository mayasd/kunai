import os
import sys
import imp
import glob

from kunai.collector import Collector
from kunai.log import logger


def get_collectors(self):
    collector_dir = os.path.dirname(__file__)
    p = collector_dir+'/*py'
    print "LOAD", p
    collector_files = glob.glob(p)
    for f in collector_files:
        fname = os.path.splitext(os.path.basename(f))[0]
        try:
            m = imp.load_source('collector%s' % fname, f)
        except Exception, exp:
            print "COLLECTOR LOAD FAIL", exp
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

