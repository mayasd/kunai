import time
import json
import requests

from kunai.log import logger
from kunai.collector import Collector
from kunai.util import to_best_int_float


class Geoloc(Collector):
    
    def __init__(self, config, put_result=None):
        super(Geoloc, self).__init__(config, put_result)
        self.geodata = {}
    
    
    def launch(self):
        if self.geodata:
            return self.geodata
        
        r = requests.get('http://ipinfo.io/json')
        data = r.text
        logger.debug('RAW geoloc data', data)
        self.geodata = json.loads(data)
        return self.geodata
