import multiprocessing
import os

from presentation.reporter import print_summary, save_report
from services.analysis_service import AnalysisService

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG = {
    'dataset_path': os.path.join(BASE_DIR, 'data', 'online_retail_II.csv'),
    'results_dir': os.path.join(BASE_DIR, 'results'),
    'num_batches': 4,
    'num_chunks': 4,
    'num_workers': multiprocessing.cpu_count(),
}


def main():
    service = AnalysisService(CONFIG)
    seq_results, par_results, stats = service.run()

    print_summary(seq_results, par_results, stats)

    report_path = os.path.join(CONFIG['results_dir'], 'analysis_report.csv')
    save_report(par_results, stats, report_path)


if __name__ == '__main__':
    main()
