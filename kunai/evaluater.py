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
    ast.GtE: op.ge, ast.LtE: op.le
}


functions = {'abs':abs}


#exp = '{collector.loadaverage.load1} {collector.loadaverage.load5}'
#all_parts = re.findall('{.*?}', exp)

#for p in all_parts:
#    p = p[1:-1]
#    print p


class Evaluater(object):
    def __init__(self):
        pass

    

    def eval_expr(self, expr):
        # first manage {} thing and look at them
        all_parts = re.findall('{.*?}', expr)

        changes = []
        print 'ALL PARTS', all_parts
        for p in all_parts:
            p = p[1:-1]
            print p
            if not p.startswith('collector.'):
                continue
            s = p[len('collector.'):]
            print 'WILL OOK AT', s
            v = collectormgr.get_data(s)
            print 'Ask', s, 'got', v
            changes.append( (p, v) )
            
        print 'ALL CHANGES', changes
        if not len(changes) == len(all_parts):
            raise ValueError('Some parts cannot be changed')
        for (p,v) in changes:
            expr = expr.replace('{%s}' % p, str(v))
        # final tree
        tree = ast.parse(expr, mode='eval').body
        return self.eval_(tree)

    
    def eval_(self, node):
        print 'EVAL NODE', node, type(node)
        print dir(node)
        try:
            print node.__dict__
        except:
            pass

        if isinstance(node, ast.Num): # <number>
            print "RETURN", node.n
            return node.n
        elif isinstance(node, ast.BinOp): # <left> <operator> <right>
            return operators[type(node.op)](self.eval_(node.left), self.eval_(node.right))
        elif isinstance(node, ast.Compare): # <left> <operator> <right>
            left = self.eval_(node.left)
            print ''
            print "LEFT", left

            print ""
            print "NODE", node, node.__dict__

            right = self.eval_(node.comparators[0])
            print ''
            print 'RIGHT', right

            return operators[type(node.ops[0])](left, right)
        elif isinstance(node, ast.UnaryOp): # <operator> <operand> e.g., -1
            return operators[type(node.op)](self.eval_(node.operand))
        elif isinstance(node, ast.Name): # name? try to look at it
            key = node.id
            v = globals().get(key, None)
            print 'VALUE', v
            return v
        elif isinstance(node, ast.Call): # call? dangerous, must be registered :)
            args = [self.eval_(arg) for arg in node.args]
            print ''
            print "CALL"
            print node.__dict__
            print 'END CALL'
            f = None
            print 'attr?', isinstance(node.func, ast.Attribute)
            print 'name?', isinstance(node.func, ast.Name)
            if isinstance(node.func, ast.Name):
                fname = node.func.id
                print 'FUNCTION CALL', fname
                print node, node.__dict__
                f = functions.get(fname, None)
            elif isinstance(node.func, ast.Attribute):
                print 'WTF F', node.func, node.func.__dict__, node.func.value.__dict__

            else:
                print 'UNKNOW FUNC'
                raise TypeError(node)
    #        elif isinstance(node.func, ast.Name):

            if f:
                v = f(*args)
                print 'FUNCITON', fname, 'called', args, "returns", v
                return v
        else:
            raise TypeError(node)



evaluater = Evaluater()
