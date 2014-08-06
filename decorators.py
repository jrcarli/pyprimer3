from threading import Thread

__author__ = "Joe Carli"
__copyright__ = "Copyright 2014"
__credits__ = ["Joe Carli"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Joe Carli"
__email__ = "jrcarli@gmail.com"
__status__ = "Development"

def async(f):

    def wrapper(*args, **kwargs):
        thr = Thread(target=f, args=args, kwargs=kwargs)
        thr.start()

    return wrapper
