#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PBT Property Validation Script"""
import pandas as pd

csv_path = r'D:\Intern_Peking University_supu\parallel_global_stiffness_assembly\cpu_parallel_stiffness_assembly\results\benchmark_results_2026-01-30.csv'
df = pd.read_csv(csv_path)

print('=== PBT Property Validation ===\n')

# PBT-01: All GPU errors < 1e-10
max_error = df['Error'].max()
pbt01 = max_error < 1e-10
print(f'PBT-01: All GPU errors < 1e-10')
print(f'        Max error = {max_error:.2e}')
print(f'        Result: {"PASS" if pbt01 else "FAIL"}\n')

# PBT-02: PrefixScan NOT in output
algos = df['Algorithm'].unique().tolist()
pbt02 = 'Prefix_Scan' not in algos and 'PrefixScan' not in algos
print(f'PBT-02: PrefixScan NOT in output')
print(f'        Algorithms: {algos}')
print(f'        Result: {"PASS" if pbt02 else "FAIL"}\n')

# PBT-04: All speedups > 0 and finite
pbt04 = all(df['Speedup'] > 0) and all(df['Speedup'].apply(lambda x: not pd.isna(x) and x != float('inf')))
print(f'PBT-04: All speedups > 0 and finite')
print(f'        Min: {df["Speedup"].min():.2f}, Max: {df["Speedup"].max():.2f}')
print(f'        Result: {"PASS" if pbt04 else "FAIL"}\n')

# PBT-05: All DOFs divisible by 3
pbt05 = all(df['DOFs'] % 3 == 0)
print(f'PBT-05: All DOFs divisible by 3')
print(f'        DOFs: {sorted(df["DOFs"].unique().tolist())}')
print(f'        Result: {"PASS" if pbt05 else "FAIL"}\n')

# PBT-06: Algorithm names match enum
expected = {'CPU_Serial', 'Atomic_WarpAgg', 'Block_Parallel', 'Work_Queue'}
actual = set(algos)
pbt06 = actual == expected
print(f'PBT-06: Algorithm names match enum')
print(f'        Expected: {expected}')
print(f'        Actual: {actual}')
print(f'        Result: {"PASS" if pbt06 else "FAIL"}\n')

# Summary
all_pass = all([pbt01, pbt02, pbt04, pbt05, pbt06])
print('=' * 40)
print(f'OVERALL: {"ALL PBT PROPERTIES PASS" if all_pass else "SOME FAILURES"}')
print('=' * 40)
