import os
import shutil
import glob

def make_dir(path):
   if not os.path.isdir(path):
      os.mkdir(path)



def copy_dir(source_item, destination_item):
   if os.path.isdir(source_item):
      make_dir(destination_item)
      sub_items = glob.glob(source_item + '/*')
      for sub_item in sub_items:
         copy_dir(sub_item, destination_item + '/' + sub_item.split('/')[-1])
   else:
       shutil.copy(source_item, destination_item)



def to_best_int_float(val):
   try:
      i = int(float(val))
      f = float(val)
   except ValueError:
      return None
   # If the f is a .0 value,
      # best match is int
   if i == f:
      return i
   return f
