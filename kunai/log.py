import os
import sys
import time
import logging


def is_tty():
    # Look if we are in a tty or not
    if hasattr(sys.stdout, 'isatty'):
        return sys.stdout.isatty()
    return False

if is_tty():
    # Try to load the terminal color. Won't work under python 2.4
    try:
        from kunai.termcolor import cprint
    except (SyntaxError, ImportError), exp:
        # Outch can't import a cprint, do a simple print
        def cprint(s, color='', end='\n'):
            if end == '':
                print s,
            else:
                print s

# Ok it's a daemon mode, if so, just print
else:
    def cprint(s, color='', end='\n'):
        if end == '':
            print s,
        else:
            print s


            
            
            
class Logger(object):
    def __init__(self):
        self.data_dir = ''
        self.log_file = None
        self.name = ''
        self.logs = {}
        self.level = logging.INFO
        self.linkify_methods()


    def linkify_methods(self):
        methods = {'DEBUG': self.do_debug, 'WARNING': self.do_warning, 'INFO': self.do_info, 'ERROR':self.do_error}
        for (s, m) in methods.iteritems():
            level = getattr(logging, s)
            # If the level is enough, link it
            if level >= self.level:
                setattr(self, s.lower(), m)
            else:
                setattr(self, s.lower(), self.do_null)
        
        
    def load(self, data_dir, name):
        self.name = name
        self.data_dir = data_dir
        self.log_file = open(os.path.join(self.data_dir, 'daemon.log'), 'a')        


    def setLevel(self, s):
        try:
            level = getattr(logging , s.upper())
            if not isinstance(level, int):
                raise AttributeError
            self.level = level
        except AttributeError:
            self.error('Invalid logging level configuration %s' % s)
            return
        
        self.linkify_methods()
            


    def log(self, *args, **kwargs ):
       name = self.name
       now = int(time.time())
       s = '%s [%d]: %s' % (name, now, ' '.join([ str(s) for s in args]))
       if 'color' in kwargs:
           cprint(s, color=kwargs['color'])
       else:
           print(s)
       # if no data_dir, we cannot save anything...
       if self.data_dir == '':
           return
       part = kwargs.get('part', '')
       if part == '':
           if self.log_file is not None:
               self.log_file.write(s+'\n')
       else:
           f = self.logs.get(part, None)
           if f is None:
               f = open(os.path.join(self.data_dir, '%s.log' % part), 'a')
               self.logs[part] = f
           f.write(s+'\n')

    
    def do_debug(self, *args, **kwargs):
        self.log(*args, color='magenta', **kwargs)
        

    def do_info(self, *args, **kwargs):
        self.log(*args, color='blue', **kwargs)

        
    def do_warning(self, *args, **kwargs):
        self.log(*args, color='yellow', **kwargs)        

        
    def do_error(self, *args,  **kwargs):
        self.log(*args, color='red',  **kwargs)
    
    def do_null(self, *args,  **kwargs):
        pass

        
logger = Logger()
