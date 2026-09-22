"""Keep CNBI_all only in one completed synthetic ablation scenario."""
import argparse
import json
from pathlib import Path
import shutil

import pandas as pd

from .pilot import write_json, ABLATION_SCENARIO
from .report import report


def revise(source, output):
    if output.exists():
        raise ValueError('Use a new output directory to preserve earlier evidence')

    def ignore_cnbi_all(path, names):
        if Path(path).resolve() != source.resolve():
            return set()
        keep_prefix = f'{ABLATION_SCENARIO}_'
        return {name for name in names
                if '_CNBI_all' in name and not name.startswith(keep_prefix)}

    shutil.copytree(source, output, ignore=ignore_cnbi_all)
    data = pd.read_csv(output/'master_results.csv')
    removed = data[(data.method == 'CNBI_all') &
                   (data.scenario_id != ABLATION_SCENARIO)]
    data = data[~((data.method == 'CNBI_all') &
                  (data.scenario_id != ABLATION_SCENARIO))].copy()
    data.to_csv(output/'master_results.csv', index=False)
    write_json(output/'ABLATION_SCOPE_REVISION.json', dict(
        source=str(source), ablation_scenario=ABLATION_SCENARIO,
        reason='only synthetic scenario where CNBI_all completed both pilot seeds',
        removed_table_rows=len(removed), removed_complete_runs=int(
            removed.comparison.eq('complete').sum()),
        cnbi_all_runs_in_other_scenarios=0,
        reused_optimizer_runs=int(data.comparison.eq('complete').sum())))
    previous = json.loads((source/'VERIFICATION.json').read_text(encoding='utf-8'))
    write_json(output/'VERIFICATION.json', dict(
        previous=previous, revision='single synthetic ablation scenario',
        ablation_scenario=ABLATION_SCENARIO, removed_complete_runs=10,
        reused_complete_runs=50, optimizer_reruns=0))
    report(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    revise(args.source, args.output)
