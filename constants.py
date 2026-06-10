import re
GROUP_QUANTILE = 0.27
DI_GOOD = 0.6
DI_OK = 0.3
DI_POOR = 0
AVG_MED = 0.3
AVG_EASY = 0.6
CA_RELIABLE = 0.9
CA_ACCEPTABLE = 0.7
col_reg = re.compile(r'\((\d+.\d+)\s+pts\)')

DIS_GOOD = 'good'
DIS_OK = 'ok'
DIS_POOR = 'poor'
DIS_NEED_REVIEW = 'need review'
DIFF_EASY = 'easy'
DIFF_MED = 'medium'
DIFF_HARD = 'hard'

DI_BINS = [-1, DI_POOR, DI_OK, DI_GOOD, 1] # (a,b]
DI_LABELS = [DIS_NEED_REVIEW, DIS_POOR, DIS_OK, DIS_GOOD]
DIFF_BINS = [0, AVG_MED, AVG_EASY, 1] # (a,b]
DIFF_LABELS = [DIFF_HARD, DIFF_MED, DIFF_EASY]