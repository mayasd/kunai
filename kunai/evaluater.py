import re
import sys
import ast
import operator as op
import math


from kunai.collectormanager import collectormgr


# supported operators
operators = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
    ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
    ast.USub: op.neg, ast.Eq: op.eq, ast.Gt: op.gt, ast.Lt: op.lt,
    ast.GtE: op.ge, ast.LtE: op.le, ast.Mod: op.mod,
}


functions = {'abs':abs}


#exp = '{collector.loadaverage.load1} {collector.loadaverage.load5}'
#all_parts = re.findall('{.*?}', exp)

#for p in all_parts:
#    p = p[1:-1]
#    print p


class Evaluater(object):
    def __init__(self):
        self.cfg_data = {}
        self.services = {}

        
    def load(self, cfg_data, services):
        self.cfg_data = cfg_data
        self.services = services


    def compile(self, expr, check=None):
        # first manage {} thing and look at them
        all_parts = re.findall('{.*?}', expr)

        changes = []
        print 'ALL PARTS', all_parts
        for p in all_parts:
            p = p[1:-1]
            print p
            if p.startswith('collector.'):
                s = p[len('collector.'):]
                print 'WILL LOOK AT collector', s
                v = collectormgr.get_data(s)
                print 'Ask', s, 'got', v
                changes.append( (p, v) )
            elif p.startswith('configuration.'):
                s = p[len('configuration.'):]
                print 'WILL LOOK AT configuration', s
                v = self._found_params(s, check)
                changes.append( (p, v) )
            
        print 'ALL CHANGES', changes
        if not len(changes) == len(all_parts):
            raise ValueError('Some parts cannot be changed')
        for (p,v) in changes:
            expr = expr.replace('{%s}' % p, str(v))
        return expr
    

    def eval_expr(self, expr, check=None):
        expr = self.compile(expr, check=check)
        
        # final tree
        tree = ast.parse(expr, mode='eval').body
        return self.eval_(tree)

    
    def eval_(self, node):
        if isinstance(node, ast.Num): # <number>
            return node.n
        elif isinstance(node, ast.Str): # <string>
            return node.s
        elif isinstance(node, ast.BinOp): # <left> <operator> <right>
            return operators[type(node.op)](self.eval_(node.left), self.eval_(node.right))
        elif isinstance(node, ast.Compare): # <left> <operator> <right>
            left = self.eval_(node.left)
            right = self.eval_(node.comparators[0])
            return operators[type(node.ops[0])](left, right)
        elif isinstance(node, ast.UnaryOp): # <operator> <operand> e.g., -1
            return operators[type(node.op)](self.eval_(node.operand))
        elif isinstance(node, ast.Name): # name? try to look at it
            key = node.id
            v = globals().get(key, None)
            return v
        elif isinstance(node, ast.Call): # call? dangerous, must be registered :)
            args = [self.eval_(arg) for arg in node.args]
            f = None
            #print 'attr?', isinstance(node.func, ast.Attribute)
            #print 'name?', isinstance(node.func, ast.Name)
            if isinstance(node.func, ast.Name):
                fname = node.func.id
                f = functions.get(fname, None)
            elif isinstance(node.func, ast.Attribute):
                print 'UNMANAGED CALL', node.func, node.func.__dict__, node.func.value.__dict__
                
            else:
                print node.__dict__
                raise TypeError(node)

            if f:
                v = f(*args)
                return v
        else:
            raise TypeError(node)


           
    # Try to find the params for a macro in the foloowing objets, in that order:
    # * check
    # * service
    # * main configuration
    def _found_params(self, m, check):

          parts = [m]
          # if we got a |, we got a default value somewhere
          if '|' in m:
             parts = m.split('|', 1)
          change_to = ''

          for p in parts:
             elts = [p]
             if '.' in p:
                elts = p.split('.')
             elts = [e.strip() for e in elts]

             # we will try to grok into our cfg_data for the k1.k2.k3 =>
             # self.cfg_data[k1][k2][k3] entry if exists
             d = None
             founded = False

             # if we got a check, we can look into it, and maybe the
             # linked service
             if check:
                 # We will look into the check>service>global order
                 # but skip serviec if it's not related with the check
                 sname = check.get('service', '')
                 service = {}
                 find_into = [check, self.cfg_data]
                 if sname and sname in self.services:
                     service = self.services.get(sname)
                     find_into = [check, service, self.cfg_data]
             # if not, just the global configuration will be ok :)
             else:
                 find_into = [self.cfg_data]

             for tgt in find_into:
                (lfounded, ld) = self._found_params_inside(elts, tgt)
                if not lfounded:
                   continue
                if lfounded:
                   founded = True
                   d = ld
                   break
             if not founded:
                continue
             change_to = str(d)
             break
          return change_to


    # Try to found a elts= k1.k2.k3 => d[k1][k2][k3] entry
    # if exists
    def _found_params_inside(self, elts, d):
             founded = False
             for e in elts:
                if not e in d:
                   founded = False
                   break
                d = d[e]
                founded = True
             return (founded, d)
        
        

evaluater = Evaluater()
