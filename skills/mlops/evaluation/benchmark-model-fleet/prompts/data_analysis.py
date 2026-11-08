"""Data analysis prompts and scorers.

Every prompt has one pinned, checkable answer. Inline data keeps the prompt
self-contained — no file paths that differ per host.

Scoring: 5 checks x 0.2 = 1.0 max.
"""
import re

# North: 10*5 + 5*10 = 100 | South: 20*3 + 10*2 = 80 | East: 7*4 = 28
SALES_CSV = """region,units,price
North,10,5
South,20,3
North,5,10
East,7,4
South,10,2"""

PROMPTS = [
    ("csv_aggregate",
     "Given this CSV data:\n\n" + SALES_CSV + "\n\n"
     "Revenue is units multiplied by price. Which region has the highest total revenue, "
     "and what is that total? Show how you calculated it."),
    ("trend_anomaly",
     "Monthly active users: Jan 100, Feb 110, Mar 121, Apr 133, May 20, Jun 161.\n\n"
     "Describe the trend, identify anything anomalous, and say what you would do about it "
     "before reporting these numbers to a stakeholder."),
    ("missing_data",
     "You have a dataset of 10,000 customer records where the 'income' column is missing "
     "for 18% of rows. You need to model customer churn. How do you handle the missing "
     "values, and what are the tradeoffs of your approach?"),
    ("stats_test_choice",
     "You are comparing conversion rates between two groups, n=12 and n=15. The data is "
     "not normally distributed. Which significance test do you use and why? What would "
     "you report alongside the p-value?"),
]


def _score(checks):
    score = sum(0.2 for _, passed in checks if passed)
    return min(round(score, 2), 1.0), [f"{'ok' if p else 'no'}: {n}" for n, p in checks]


def score_csv_aggregate(text):
    low = text.lower()
    return _score([
        ("correct region (North)", "north" in low),
        ("correct total (100)", re.search(r'\b100\b', text) is not None),
        ("multiplies units x price", any(t in low for t in ("units * price", "units*price", "unit price", "multiply", "revenue =", "units × price"))),
        ("shows per-region totals", "80" in text or "28" in text),
        ("method shown", any(t in low for t in ("groupby", "group by", "sum(", "total", "aggregate"))),
    ])


def score_trend_anomaly(text):
    low = text.lower()
    return _score([
        ("identifies growth", any(t in low for t in ("grow", "increas", "upward", "rising", "10%", "compound"))),
        ("flags May", "may" in low),
        ("calls it anomalous", any(t in low for t in ("anomal", "outlier", "drop", "dip", "suspicious", "error"))),
        ("suspects data quality", any(t in low for t in ("data quality", "collection", "tracking", "instrument", "pipeline", "missing", "logging", "verify", "investigate"))),
        ("advises before reporting", any(t in low for t in ("before report", "caveat", "annotate", "flag", "confirm", "validate", "footnote"))),
    ])


def score_missing_data(text):
    low = text.lower()
    return _score([
        ("names a strategy", any(t in low for t in ("impute", "median", "mean", "drop", "fillna"))),
        ("considers missingness mechanism", any(t in low for t in ("mcar", "mar", "mnar", "not at random", "systematic", "why", "mechanism"))),
        ("missing-indicator or model-native", any(t in low for t in ("indicator", "flag", "dummy", "native", "xgboost", "lightgbm", "tree"))),
        ("names the tradeoff", any(t in low for t in ("bias", "variance", "distort", "underestimat", "leakage", "tradeoff", "trade-off"))),
        ("warns against naive drop", any(t in low for t in ("18%", "lose", "losing", "discard", "too much data", "1,800", "1800"))),
    ])


def score_stats_test_choice(text):
    low = text.lower()
    return _score([
        ("names the right test", any(t in low for t in ("mann-whitney", "mann whitney", "wilcoxon rank-sum", "rank sum", "fisher", "permutation", "bootstrap"))),
        ("says non-parametric", "parametric" in low),
        ("justifies vs t-test", "t-test" in low or "t test" in low),
        ("effect size", any(t in low for t in ("effect size", "confidence interval", "ci", "magnitude"))),
        ("flags small n", any(t in low for t in ("small sample", "power", "n=12", "n=15", "underpowered", "sample size"))),
    ])


SCORERS = {
    "csv_aggregate": score_csv_aggregate,
    "trend_anomaly": score_trend_anomaly,
    "missing_data": score_missing_data,
    "stats_test_choice": score_stats_test_choice,
}
