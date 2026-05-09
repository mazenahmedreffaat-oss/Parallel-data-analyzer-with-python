import multiprocessing as mp

_g_func = None
_g_items = None


def _dispatch(idx):
    return _g_func(_g_items[idx])


class ThreadPool:
    def __init__(self, num_workers):
        self.num_workers = num_workers

    def run_parallel(self, func, items):
        global _g_func, _g_items
        _g_func = func
        _g_items = items
        ctx = mp.get_context('fork')
        with ctx.Pool(processes=self.num_workers) as pool:
            return pool.map(_dispatch, range(len(items)))

    def run_sequential(self, func, items):
        return [func(item) for item in items]
