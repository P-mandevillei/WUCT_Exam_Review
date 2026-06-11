import re
from matplotlib import pyplot as plt

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
CA_LAB_RELIABLE = 'reliable'
CA_LAB_ACCEPTABLE = 'acceptable'
CA_LAB_UNRELIABLE = 'unreliable'
BINARY_LOW = "Low"
BINARY_HIGH = "High"

DI_BINS = [-1, DI_POOR, DI_OK, DI_GOOD, 1] # (a,b]
DI_LABELS = [DIS_NEED_REVIEW, DIS_POOR, DIS_OK, DIS_GOOD]
DIFF_BINS = [0, AVG_MED, AVG_EASY, 1] # (a,b]
DIFF_LABELS = [DIFF_HARD, DIFF_MED, DIFF_EASY]
CA_BINS = [0, CA_ACCEPTABLE, CA_RELIABLE, 1] # (a,b]
CA_LABELS = [CA_LAB_UNRELIABLE, CA_LAB_ACCEPTABLE, CA_LAB_RELIABLE]
BINARY_LABELS = [BINARY_LOW, BINARY_HIGH]

colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
quality_cmap = {DIS_GOOD: colors[2], DIS_OK: colors[0], DIS_POOR: colors[1], DIS_NEED_REVIEW: colors[3]}
consistency_cmap = {CA_LAB_RELIABLE: colors[2], CA_LAB_ACCEPTABLE: colors[1], CA_LAB_UNRELIABLE: colors[3]}
binary_cmap = {BINARY_LOW: '#1E88E5', BINARY_HIGH: '#FF0D57'}
