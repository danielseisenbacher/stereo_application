import inspect
from time import time, strftime, localtime


def func_info(func):
    """
    Diese Funktion printed Informationen zum Ablauf von Funktionen (Start- und Endzeit, Dauer, Name)
    """
    def wrap_func(*args, **kwargs):
        module = inspect.getmodule(func).__name__
        t0 = strftime("%H:%M:%S", localtime())
        print(f'-----\n{t0}: Function {module}.{func.__name__!r} started')
        t1 = time()
        result = func(*args, **kwargs)
        t2 = time()
        t3 = strftime("%H:%M:%S", localtime())
        print(f'{t3}: Function {module}.{func.__name__!r} executed in {(t2 - t1):.4f}s\n-----')
        return result

    return wrap_func
