import time

from concurrency.thread_pool import ThreadPool
from data.data_loader import clean, load, make_chunks
from workers.data_worker import aggregate_results, analyze_chunk


class AnalysisService:
    def __init__(self, config):
        self.config = config
        self.pool = ThreadPool(config['num_workers'])

    def run(self):
        df = load(self.config['dataset_path'])
        original_rows = len(df)

        df = clean(df)
        cleaned_rows = len(df)

        chunks = make_chunks(df, self.config['num_batches'], self.config['num_chunks'])

        seq_start = time.time()
        seq_results = aggregate_results(self.pool.run_sequential(analyze_chunk, chunks))
        seq_time = time.time() - seq_start

        par_start = time.time()
        par_results = aggregate_results(self.pool.run_parallel(analyze_chunk, chunks))
        par_time = time.time() - par_start

        stats = {
            'original_rows': original_rows,
            'cleaned_rows': cleaned_rows,
            'removed_rows': original_rows - cleaned_rows,
            'total_chunks': len(chunks),
            'num_workers': self.config['num_workers'],
            'seq_time': seq_time,
            'par_time': par_time,
        }

        return seq_results, par_results, stats
