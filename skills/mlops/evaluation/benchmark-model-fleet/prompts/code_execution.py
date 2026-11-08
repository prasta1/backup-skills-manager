"""Execution-scored coding tasks.

WHY THIS EXISTS
---------------
The code family's existing quality score is a 5-substring pattern match per
prompt. It cannot distinguish a correct answer that omits a keyword from a
wrong answer that includes it -- demonstrated on rust_closure_borrow, where a
correct borrow-checker diagnosis scored 0.60 and a wrong one scored 0.80.
Vocabulary is not correctness.

Every task here carries:
  * an unambiguous natural-language spec,
  * executable tests whose expected values are computed by a REFERENCE
    solution shipped alongside,
  * so `--self-test` proves the instrument scores a known-correct program at
    100% before any model is measured.

Scoring is per-ASSERTION, not per-task. 40 tasks x ~5 assertions = ~200 graded
data points, which is well under the ~4-task resolution floor that makes
binary task scoring useless for detecting small differences.

Ground truth here is "does the code run and produce the right value" -- the
only definition for a coding model that a model cannot game by wording.
"""

# Each task:
#   id         stable key
#   difficulty easy | medium | hard  (for saturation analysis)
#   prompt     what the model is asked to write
#   func       the required entry-point name
#   tests      list of (expression, expected) -- evaluated with solve() in scope
#   reference  a known-correct implementation, used only for --self-test

CODING_PROMPTS = [
    # ---------------- strings ----------------
    {
        "id": "str_word_reverse",
        "difficulty": "easy",
        "func": "solve",
        "prompt": "Write a Python function `solve(s)` that returns the words of "
                  "string `s` in reverse order, joined by single spaces. "
                  "Whitespace runs collapse; leading/trailing space is ignored.",
        "tests": [
            ("solve('hello world')", "world hello"),
            ("solve('  a  b   c ')", "c b a"),
            ("solve('one')", "one"),
            ("solve('')", ""),
            ("solve('a\\nb')", "b a"),
        ],
        "reference": "def solve(s):\n    return ' '.join(s.split()[::-1])",
    },
    {
        "id": "str_palindrome_normalize",
        "difficulty": "easy",
        "func": "solve",
        "prompt": "Write `solve(s)` returning True if `s` reads the same forwards "
                  "and backwards, ignoring case and any non-alphanumeric "
                  "characters.",
        "tests": [
            ("solve('A man, a plan, a canal: Panama')", True),
            ("solve('race a car')", False),
            ("solve('')", True),
            ("solve('0P')", False),
            ("solve('Was it a car or a cat I saw?')", True),
        ],
        "reference": (
            "def solve(s):\n"
            "    t = [c.lower() for c in s if c.isalnum()]\n"
            "    return t == t[::-1]"
        ),
    },
    {
        "id": "str_run_length_encode",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(s)` that run-length encodes `s`: each run of "
                  "identical characters becomes the character followed by its "
                  "count. 'aaabbc' -> 'a3b2c1'.",
        "tests": [
            ("solve('aaabbc')", "a3b2c1"),
            ("solve('')", ""),
            ("solve('x')", "x1"),
            ("solve('aabbaa')", "a2b2a2"),
            ("solve('zzzzzzzzzzzz')", "z12"),
        ],
        "reference": (
            "def solve(s):\n"
            "    out = []\n"
            "    i = 0\n"
            "    while i < len(s):\n"
            "        j = i\n"
            "        while j < len(s) and s[j] == s[i]:\n"
            "            j += 1\n"
            "        out.append(s[i] + str(j - i))\n"
            "        i = j\n"
            "    return ''.join(out)"
        ),
    },
    {
        "id": "str_longest_unique_substring",
        "difficulty": "hard",
        "func": "solve",
        "prompt": "Write `solve(s)` returning the LENGTH of the longest substring "
                  "of `s` with no repeated characters.",
        "tests": [
            ("solve('abcabcbb')", 3),
            ("solve('bbbbb')", 1),
            ("solve('pwwkew')", 3),
            ("solve('')", 0),
            ("solve('dvdf')", 3),
        ],
        "reference": (
            "def solve(s):\n"
            "    seen = {}\n"
            "    best = start = 0\n"
            "    for i, ch in enumerate(s):\n"
            "        if ch in seen and seen[ch] >= start:\n"
            "            start = seen[ch] + 1\n"
            "        seen[ch] = i\n"
            "        best = max(best, i - start + 1)\n"
            "    return best"
        ),
    },
    {
        "id": "str_caesar",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(s, k)` applying a Caesar shift of `k` to lowercase "
                  "letters only, wrapping within a-z. Non-letters pass through "
                  "unchanged. k may be negative or larger than 26.",
        "tests": [
            ("solve('abc', 1)", "bcd"),
            ("solve('xyz', 3)", "abc"),
            ("solve('abc', -1)", "zab"),
            ("solve('abc', 27)", "bcd"),
            ("solve('a B c!', 2)", "c B e!"),
        ],
        "reference": (
            "def solve(s, k):\n"
            "    out = []\n"
            "    for c in s:\n"
            "        if 'a' <= c <= 'z':\n"
            "            out.append(chr((ord(c) - 97 + k) % 26 + 97))\n"
            "        else:\n"
            "            out.append(c)\n"
            "    return ''.join(out)"
        ),
    },
    {
        "id": "str_anagram_groups",
        "difficulty": "hard",
        "func": "solve",
        "prompt": "Write `solve(words)` returning the number of distinct anagram "
                  "groups in the list `words` (case-sensitive).",
        "tests": [
            ("solve(['eat','tea','tan','ate','nat','bat'])", 3),
            ("solve([])", 0),
            ("solve(['a'])", 1),
            ("solve(['ab','ba','ab'])", 1),
            ("solve(['abc','def'])", 2),
        ],
        "reference": (
            "def solve(words):\n"
            "    return len({''.join(sorted(w)) for w in words})"
        ),
    },
    {
        "id": "str_title_case_fix",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(s)` that capitalises the first letter of every "
                  "word and lowercases the rest, where words are separated by "
                  "single spaces. Collapse whitespace runs first.",
        "tests": [
            ("solve('hello WORLD')", "Hello World"),
            ("solve('  a  bB  ')", "A Bb"),
            ("solve('')", ""),
            ("solve('mIxEd cAsE')", "Mixed Case"),
            ("solve('x')", "X"),
        ],
        "reference": (
            "def solve(s):\n"
            "    return ' '.join(w[:1].upper() + w[1:].lower() for w in s.split())"
        ),
    },

    # ---------------- lists / sequences ----------------
    {
        "id": "list_flatten_nd",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(x)` that flattens an arbitrarily nested list of "
                  "integers into a flat list, preserving order.",
        "tests": [
            ("solve([1,[2,[3,[4]]]])", [1, 2, 3, 4]),
            ("solve([])", []),
            ("solve([[],1])", [1]),
            ("solve([[1],[2]])", [1, 2]),
            ("solve([1,2,3])", [1, 2, 3]),
        ],
        "reference": (
            "def solve(x):\n"
            "    out = []\n"
            "    for i in x:\n"
            "        out.extend(solve(i) if isinstance(i, list) else [i])\n"
            "    return out"
        ),
    },
    {
        "id": "list_rotate_k",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(nums, k)` rotating the list `nums` right by `k` "
                  "positions, returning a new list. k may exceed the length.",
        "tests": [
            ("solve([1,2,3,4,5], 2)", [4, 5, 1, 2, 3]),
            ("solve([1,2], 0)", [1, 2]),
            ("solve([1,2,3], 3)", [1, 2, 3]),
            ("solve([1,2,3], 4)", [3, 1, 2]),
            ("solve([], 5)", []),
        ],
        "reference": (
            "def solve(nums, k):\n"
            "    if not nums:\n"
            "        return []\n"
            "    k %= len(nums)\n"
            "    return nums[-k:] + nums[:-k] if k else list(nums)"
        ),
    },
    {
        "id": "list_merge_intervals",
        "difficulty": "hard",
        "func": "solve",
        "prompt": "Write `solve(intervals)` merging overlapping closed intervals, "
                  "given as a list of [start, end] pairs. Return sorted by start.",
        "tests": [
            ("solve([[1,3],[2,6],[8,10],[15,18]])", [[1, 6], [8, 10], [15, 18]]),
            ("solve([[1,4],[4,5]])", [[1, 5]]),
            ("solve([])", []),
            ("solve([[5,6],[1,2]])", [[1, 2], [5, 6]]),
            ("solve([[1,10],[2,3]])", [[1, 10]]),
        ],
        "reference": (
            "def solve(intervals):\n"
            "    out = []\n"
            "    for s, e in sorted(intervals):\n"
            "        if out and s <= out[-1][1]:\n"
            "            out[-1][1] = max(out[-1][1], e)\n"
            "        else:\n"
            "            out.append([s, e])\n"
            "    return out"
        ),
    },
    {
        "id": "list_missing_number",
        "difficulty": "easy",
        "func": "solve",
        "prompt": "Write `solve(nums)` returning the single missing integer from "
                  "the list `nums`, which contains n distinct values drawn from "
                  "0..n inclusive with exactly one missing.",
        "tests": [
            ("solve([3,0,1])", 2),
            ("solve([0,1])", 2),
            ("solve([9,6,4,2,3,5,7,0,1])", 8),
            ("solve([0])", 1),
            ("solve([1])", 0),
        ],
        "reference": (
            "def solve(nums):\n"
            "    n = len(nums)\n"
            "    return n * (n + 1) // 2 - sum(nums)"
        ),
    },
    {
        "id": "list_top_k_frequent",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(nums, k)` returning the `k` most frequent values "
                  "in `nums`, ordered by descending frequency; ties broken by "
                  "ascending value.",
        "tests": [
            ("solve([1,1,1,2,2,3], 2)", [1, 2]),
            ("solve([1], 1)", [1]),
            ("solve([3,3,2,2,1], 2)", [2, 3]),
            ("solve([4,4,5,5], 2)", [4, 5]),
            ("solve([7,7,7], 1)", [7]),
        ],
        "reference": (
            "def solve(nums, k):\n"
            "    from collections import Counter\n"
            "    c = Counter(nums)\n"
            "    return sorted(c, key=lambda x: (-c[x], x))[:k]"
        ),
    },
    {
        "id": "list_pair_sum_sorted",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(nums, target)` returning True if any two distinct "
                  "positions in the sorted list `nums` sum to `target`.",
        "tests": [
            ("solve([1,2,3,4,5], 9)", True),
            ("solve([1,2,3], 6)", False),
            ("solve([1,1], 2)", True),
            ("solve([], 0)", False),
            ("solve([-3,1,4], 1)", True),
        ],
        "reference": (
            "def solve(nums, target):\n"
            "    i, j = 0, len(nums) - 1\n"
            "    while i < j:\n"
            "        s = nums[i] + nums[j]\n"
            "        if s == target:\n"
            "            return True\n"
            "        if s < target:\n"
            "            i += 1\n"
            "        else:\n"
            "            j -= 1\n"
            "    return False"
        ),
    },
    {
        "id": "list_chunk",
        "difficulty": "easy",
        "func": "solve",
        "prompt": "Write `solve(nums, n)` splitting `nums` into consecutive chunks "
                  "of size `n`; the final chunk may be shorter. n is >= 1.",
        "tests": [
            ("solve([1,2,3,4,5], 2)", [[1, 2], [3, 4], [5]]),
            ("solve([], 3)", []),
            ("solve([1], 1)", [[1]]),
            ("solve([1,2], 5)", [[1, 2]]),
            ("solve([1,2,3,4], 4)", [[1, 2, 3, 4]]),
        ],
        "reference": "def solve(nums, n):\n    return [nums[i:i+n] for i in range(0, len(nums), n)]",
    },

    # ---------------- dicts / sets ----------------
    {
        "id": "dict_invert",
        "difficulty": "easy",
        "func": "solve",
        "prompt": "Write `solve(d)` inverting a dict of unique values, so "
                  "value->key.",
        "tests": [
            ("solve({'a':1,'b':2})", {1: 'a', 2: 'b'}),
            ("solve({})", {}),
            ("solve({'x':0})", {0: 'x'}),
            ("solve({'a':'p','b':'q'})", {'p': 'a', 'q': 'b'}),
            ("solve({'k':-1})", {-1: 'k'}),
        ],
        "reference": "def solve(d):\n    return {v: k for k, v in d.items()}",
    },
    {
        "id": "dict_merge_sum",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(a, b)` merging two dicts, summing values for keys "
                  "present in both.",
        "tests": [
            ("solve({'x':1,'y':2}, {'y':3,'z':4})", {'x': 1, 'y': 5, 'z': 4}),
            ("solve({}, {'a':1})", {'a': 1}),
            ("solve({'a':1}, {})", {'a': 1}),
            ("solve({'a':-1}, {'a':1})", {'a': 0}),
            ("solve({}, {})", {}),
        ],
        "reference": (
            "def solve(a, b):\n"
            "    out = dict(a)\n"
            "    for k, v in b.items():\n"
            "        out[k] = out.get(k, 0) + v\n"
            "    return out"
        ),
    },
    {
        "id": "dict_group_by_length",
        "difficulty": "easy",
        "func": "solve",
        "prompt": "Write `solve(words)` grouping words by their length into a "
                  "dict length -> sorted list of words.",
        "tests": [
            ("solve(['b','a','cc'])", {1: ['a', 'b'], 2: ['cc']}),
            ("solve([])", {}),
            ("solve(['abc'])", {3: ['abc']}),
            ("solve(['bb','aa'])", {2: ['aa', 'bb']}),
            ("solve(['x','yy','z'])", {1: ['x', 'z'], 2: ['yy']}),
        ],
        "reference": (
            "def solve(words):\n"
            "    out = {}\n"
            "    for w in words:\n"
            "        out.setdefault(len(w), []).append(w)\n"
            "    return {k: sorted(v) for k, v in out.items()}"
        ),
    },
    {
        "id": "dict_flatten_nested",
        "difficulty": "hard",
        "func": "solve",
        "prompt": "Write `solve(d)` flattening a nested dict into a single-level "
                  "dict whose keys are dot-joined paths, e.g. "
                  "{'a':{'b':1}} -> {'a.b': 1}. Empty nested dicts are omitted.",
        "tests": [
            ("solve({'a':{'b':1}})", {'a.b': 1}),
            ("solve({'a':1})", {'a': 1}),
            ("solve({'a':{'b':{'c':2}}})", {'a.b.c': 2}),
            ("solve({})", {}),
            ("solve({'a':{},'b':1})", {'b': 1}),
        ],
        "reference": (
            "def solve(d, _p=''):\n"
            "    out = {}\n"
            "    for k, v in d.items():\n"
            "        key = _p + k\n"
            "        if isinstance(v, dict):\n"
            "            out.update(solve(v, key + '.'))\n"
            "        else:\n"
            "            out[key] = v\n"
            "    return out"
        ),
    },
    {
        "id": "set_symmetric_diff",
        "difficulty": "easy",
        "func": "solve",
        "prompt": "Write `solve(a, b)` returning the sorted list of elements that "
                  "appear in exactly one of the two lists `a` and `b`.",
        "tests": [
            ("solve([1,2,3], [3,4])", [1, 2, 4]),
            ("solve([], [1])", [1]),
            ("solve([1], [1])", []),
            ("solve([2,1], [])", [1, 2]),
            ("solve([5,5,1], [1])", [5]),
        ],
        "reference": "def solve(a, b):\n    return sorted(set(a) ^ set(b))",
    },

    # ---------------- math ----------------
    {
        "id": "math_gcd_list",
        "difficulty": "easy",
        "func": "solve",
        "prompt": "Write `solve(nums)` returning the greatest common divisor of a "
                  "non-empty list of positive integers.",
        "tests": [
            ("solve([12, 18])", 6),
            ("solve([7])", 7),
            ("solve([12, 18, 24])", 6),
            ("solve([5, 7])", 1),
            ("solve([100, 10, 10])", 10),
        ],
        "reference": (
            "def solve(nums):\n"
            "    from math import gcd\n"
            "    from functools import reduce\n"
            "    return reduce(gcd, nums)"
        ),
    },
    {
        "id": "math_count_primes",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(n)` returning how many primes are strictly less "
                  "than `n`.",
        "tests": [
            ("solve(10)", 4),
            ("solve(2)", 0),
            ("solve(3)", 1),
            ("solve(0)", 0),
            ("solve(20)", 8),
        ],
        "reference": (
            "def solve(n):\n"
            "    if n < 3:\n"
            "        return 0\n"
            "    sieve = bytearray([1]) * n\n"
            "    sieve[0] = sieve[1] = 0\n"
            "    for i in range(2, int(n ** 0.5) + 1):\n"
            "        if sieve[i]:\n"
            "            sieve[i*i::i] = bytearray(len(sieve[i*i::i]))\n"
            "    return sum(sieve)"
        ),
    },
    {
        "id": "math_base_convert",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(n, base)` converting non-negative integer `n` to "
                  "its string representation in `base` (2..16), using lowercase "
                  "digits a-f. solve(0, 2) == '0'.",
        "tests": [
            ("solve(10, 2)", "1010"),
            ("solve(0, 2)", "0"),
            ("solve(255, 16)", "ff"),
            ("solve(8, 8)", "10"),
            ("solve(35, 36)", "z"),
        ],
        "reference": (
            "def solve(n, base):\n"
            "    if n == 0:\n"
            "        return '0'\n"
            "    digits = '0123456789abcdefghijklmnopqrstuvwxyz'\n"
            "    out = ''\n"
            "    while n:\n"
            "        out = digits[n % base] + out\n"
            "        n //= base\n"
            "    return out"
        ),
    },
    {
        "id": "math_int_sqrt",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(n)` returning the integer floor of the square "
                  "root of non-negative `n`, WITHOUT using any square-root "
                  "function or **0.5.",
        "tests": [
            ("solve(0)", 0),
            ("solve(1)", 1),
            ("solve(8)", 2),
            ("solve(9)", 3),
            ("solve(10**12)", 10**6),
        ],
        "reference": (
            "def solve(n):\n"
            "    lo, hi = 0, n\n"
            "    while lo < hi:\n"
            "        mid = (lo + hi + 1) // 2\n"
            "        if mid * mid <= n:\n"
            "            lo = mid\n"
            "        else:\n"
            "            hi = mid - 1\n"
            "    return lo"
        ),
    },
    {
        "id": "math_is_power_of_two",
        "difficulty": "easy",
        "func": "solve",
        "prompt": "Write `solve(n)` returning True if positive integer `n` is a "
                  "power of two, else False.",
        "tests": [
            ("solve(1)", True),
            ("solve(2)", True),
            ("solve(6)", False),
            ("solve(0)", False),
            ("solve(1024)", True),
        ],
        "reference": "def solve(n):\n    return n > 0 and (n & (n - 1)) == 0",
    },
    {
        "id": "math_digit_sum",
        "difficulty": "easy",
        "func": "solve",
        "prompt": "Write `solve(n)` returning the sum of the decimal digits of "
                  "the absolute value of integer `n`.",
        "tests": [
            ("solve(123)", 6),
            ("solve(0)", 0),
            ("solve(-45)", 9),
            ("solve(9999)", 36),
            ("solve(-1)", 1),
        ],
        "reference": "def solve(n):\n    return sum(int(c) for c in str(abs(n)))",
    },

    # ---------------- algorithms ----------------
    {
        "id": "algo_binary_search",
        "difficulty": "easy",
        "func": "solve",
        "prompt": "Write `solve(nums, target)` returning the index of `target` in "
                  "the sorted list `nums`, or -1 if absent.",
        "tests": [
            ("solve([1,2,3,4,5], 3)", 2),
            ("solve([1,2,3], 9)", -1),
            ("solve([], 1)", -1),
            ("solve([2], 2)", 0),
            ("solve([1,3,5,7], 7)", 3),
        ],
        "reference": (
            "def solve(nums, target):\n"
            "    lo, hi = 0, len(nums) - 1\n"
            "    while lo <= hi:\n"
            "        mid = (lo + hi) // 2\n"
            "        if nums[mid] == target:\n"
            "            return mid\n"
            "        if nums[mid] < target:\n"
            "            lo = mid + 1\n"
            "        else:\n"
            "            hi = mid - 1\n"
            "    return -1"
        ),
    },
    {
        "id": "algo_longest_increasing",
        "difficulty": "hard",
        "func": "solve",
        "prompt": "Write `solve(nums)` returning the length of the longest "
                  "STRICTLY increasing subsequence of `nums`.",
        "tests": [
            ("solve([10,9,2,5,3,7,101,18])", 4),
            ("solve([])", 0),
            ("solve([1])", 1),
            ("solve([7,7,7,7])", 1),
            ("solve([1,2,3,4])", 4),
        ],
        "reference": (
            "def solve(nums):\n"
            "    import bisect\n"
            "    tails = []\n"
            "    for x in nums:\n"
            "        i = bisect.bisect_left(tails, x)\n"
            "        if i == len(tails):\n"
            "            tails.append(x)\n"
            "        else:\n"
            "            tails[i] = x\n"
            "    return len(tails)"
        ),
    },
    {
        "id": "algo_max_subarray",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(nums)` returning the largest sum of any "
                  "non-empty contiguous subarray.",
        "tests": [
            ("solve([-2,1,-3,4,-1,2,1,-5,4])", 6),
            ("solve([1])", 1),
            ("solve([-1])", -1),
            ("solve([-2,-1])", -1),
            ("solve([5,4,-1,7,8])", 23),
        ],
        "reference": (
            "def solve(nums):\n"
            "    best = cur = nums[0]\n"
            "    for x in nums[1:]:\n"
            "        cur = max(x, cur + x)\n"
            "        best = max(best, cur)\n"
            "    return best"
        ),
    },
    {
        "id": "algo_edit_distance",
        "difficulty": "hard",
        "func": "solve",
        "prompt": "Write `solve(a, b)` returning the Levenshtein edit distance "
                  "between strings `a` and `b`.",
        "tests": [
            ("solve('kitten', 'sitting')", 3),
            ("solve('', '')", 0),
            ("solve('abc', '')", 3),
            ("solve('same', 'same')", 0),
            ("solve('flaw', 'lawn')", 2),
        ],
        "reference": (
            "def solve(a, b):\n"
            "    prev = list(range(len(b) + 1))\n"
            "    for i, ca in enumerate(a, 1):\n"
            "        cur = [i]\n"
            "        for j, cb in enumerate(b, 1):\n"
            "            cur.append(min(prev[j] + 1, cur[j-1] + 1,\n"
            "                           prev[j-1] + (ca != cb)))\n"
            "        prev = cur\n"
            "    return prev[-1]"
        ),
    },
    {
        "id": "algo_coin_change",
        "difficulty": "hard",
        "func": "solve",
        "prompt": "Write `solve(coins, amount)` returning the fewest coins needed "
                  "to make `amount`, or -1 if impossible. Coins may be reused.",
        "tests": [
            ("solve([1,2,5], 11)", 3),
            ("solve([2], 3)", -1),
            ("solve([1], 0)", 0),
            ("solve([2,5], 10)", 2),
            ("solve([3,7], 5)", -1),
        ],
        "reference": (
            "def solve(coins, amount):\n"
            "    INF = float('inf')\n"
            "    dp = [0] + [INF] * amount\n"
            "    for i in range(1, amount + 1):\n"
            "        for c in coins:\n"
            "            if c <= i and dp[i-c] + 1 < dp[i]:\n"
            "                dp[i] = dp[i-c] + 1\n"
            "    return -1 if dp[amount] == INF else dp[amount]"
        ),
    },
    {
        "id": "algo_topo_sort",
        "difficulty": "hard",
        "func": "solve",
        "prompt": "Write `solve(n, edges)` returning a topological ordering of "
                  "nodes 0..n-1 for the directed edges [u, v] (u before v), or "
                  "an empty list if a cycle exists. Any valid order is accepted.",
        "tests": [
            ("solve(2, [[0,1]]) in ([0,1],)", True),
            ("solve(3, [[0,1],[1,2]])", [0, 1, 2]),
            ("solve(2, [[0,1],[1,0]])", []),
            ("solve(1, [])", [0]),
            ("solve(3, []) in ([0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0])", True),
        ],
        "reference": (
            "def solve(n, edges):\n"
            "    from collections import deque\n"
            "    adj = [[] for _ in range(n)]\n"
            "    indeg = [0] * n\n"
            "    for u, v in edges:\n"
            "        adj[u].append(v)\n"
            "        indeg[v] += 1\n"
            "    q = deque(i for i in range(n) if indeg[i] == 0)\n"
            "    out = []\n"
            "    while q:\n"
            "        u = q.popleft()\n"
            "        out.append(u)\n"
            "        for v in adj[u]:\n"
            "            indeg[v] -= 1\n"
            "            if indeg[v] == 0:\n"
            "                q.append(v)\n"
            "    return out if len(out) == n else []"
        ),
    },
    {
        "id": "algo_matrix_spiral",
        "difficulty": "hard",
        "func": "solve",
        "prompt": "Write `solve(m)` returning the elements of the 2-D list `m` in "
                  "clockwise spiral order starting at the top-left.",
        "tests": [
            ("solve([[1,2],[3,4]])", [1, 2, 4, 3]),
            ("solve([[1,2,3],[4,5,6],[7,8,9]])", [1, 2, 3, 6, 9, 8, 7, 4, 5]),
            ("solve([[1]])", [1]),
            ("solve([[1,2,3]])", [1, 2, 3]),
            ("solve([[1],[2]])", [1, 2]),
        ],
        "reference": (
            "def solve(m):\n"
            "    out = []\n"
            "    while m:\n"
            "        out += m.pop(0)\n"
            "        m = [list(r) for r in zip(*m)][::-1]\n"
            "    return out"
        ),
    },
    {
        "id": "algo_two_sum_indices",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(nums, target)` returning the [i, j] indices "
                  "(i < j) of the two numbers summing to target, or [] if none. "
                  "Exactly one solution exists when a solution exists.",
        "tests": [
            ("solve([2,7,11,15], 9)", [0, 1]),
            ("solve([3,2,4], 6)", [1, 2]),
            ("solve([3,3], 6)", [0, 1]),
            ("solve([1,2], 99)", []),
            ("solve([-1,-2,-3], -5)", [1, 2]),
        ],
        "reference": (
            "def solve(nums, target):\n"
            "    seen = {}\n"
            "    for i, x in enumerate(nums):\n"
            "        if target - x in seen:\n"
            "            return [seen[target - x], i]\n"
            "        seen[x] = i\n"
            "    return []"
        ),
    },

    # ---------------- parsing / formatting ----------------
    {
        "id": "parse_csv_row",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(line)` splitting ONE CSV line into fields, where "
                  "double quotes protect commas and a doubled quote inside a "
                  "quoted field means a literal quote. Do not use the csv module.",
        "tests": [
            ("solve('a,b,c')", ['a', 'b', 'c']),
            ("solve('a,\"b,c\",d')", ['a', 'b,c', 'd']),
            ("solve('\"a\"\"b\"')", ['a\"b']),
            ("solve('')", ['']),
            ("solve('x')", ['x']),
        ],
        "reference": (
            "def solve(line):\n"
            "    out, cur, q = [], '', False\n"
            "    i = 0\n"
            "    while i < len(line):\n"
            "        c = line[i]\n"
            "        if q:\n"
            "            if c == '\"':\n"
            "                if i + 1 < len(line) and line[i+1] == '\"':\n"
            "                    cur += '\"'; i += 1\n"
            "                else:\n"
            "                    q = False\n"
            "            else:\n"
            "                cur += c\n"
            "        else:\n"
            "            if c == '\"':\n"
            "                q = True\n"
            "            elif c == ',':\n"
            "                out.append(cur); cur = ''\n"
            "            else:\n"
            "                cur += c\n"
            "        i += 1\n"
            "    out.append(cur)\n"
            "    return out"
        ),
    },
    {
        "id": "parse_ini",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(text)` parsing INI-style text into a dict of "
                  "section -> {key: value}. Lines starting with # or ; are "
                  "comments; blank lines are skipped. Keys before any section "
                  "go under the '' section. Values are strings with surrounding "
                  "whitespace stripped.",
        "tests": [
            ("solve('[a]\\nx = 1')", {'a': {'x': '1'}}),
            ("solve('# c\\n[a]\\ny=2')", {'a': {'y': '2'}}),
            ("solve('k=v')", {'': {'k': 'v'}}),
            ("solve('')", {}),
            ("solve('[a]\\n;a\\n[b]\\nz=9')", {'a': {}, 'b': {'z': '9'}}),
        ],
        "reference": (
            "def solve(text):\n"
            "    out, sec = {}, ''\n"
            "    for raw in text.splitlines():\n"
            "        line = raw.strip()\n"
            "        if not line or line[0] in '#;':\n"
            "            continue\n"
            "        if line.startswith('[') and line.endswith(']'):\n"
            "            sec = line[1:-1].strip()\n"
            "            out.setdefault(sec, {})\n"
            "        elif '=' in line:\n"
            "            k, _, v = line.partition('=')\n"
            "            out.setdefault(sec, {})[k.strip()] = v.strip()\n"
            "    return out"
        ),
    },
    {
        "id": "fmt_human_bytes",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(n)` formatting a byte count as a human string "
                  "with one decimal place, using units B, KB, MB, GB, TB "
                  "(powers of 1000). Values below 1000 are 'N B' with no "
                  "decimal.",
        "tests": [
            ("solve(0)", "0 B"),
            ("solve(999)", "999 B"),
            ("solve(1000)", "1.0 KB"),
            ("solve(1500)", "1.5 KB"),
            ("solve(1000000)", "1.0 MB"),
        ],
        "reference": (
            "def solve(n):\n"
            "    if n < 1000:\n"
            "        return '%d B' % n\n"
            "    for u in ('KB', 'MB', 'GB', 'TB'):\n"
            "        n /= 1000.0\n"
            "        if n < 1000:\n"
            "            return '%.1f %s' % (n, u)\n"
            "    return '%.1f PB' % n"
        ),
    },
    {
        "id": "fmt_roman",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(n)` converting an integer 1..3999 to a Roman "
                  "numeral string, using subtractive notation.",
        "tests": [
            ("solve(1)", "I"),
            ("solve(4)", "IV"),
            ("solve(9)", "IX"),
            ("solve(1994)", "MCMXCIV"),
            ("solve(3999)", "MMMCMXCIX"),
        ],
        "reference": (
            "def solve(n):\n"
            "    vals = [(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),\n"
            "            (90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),\n"
            "            (5,'V'),(4,'IV'),(1,'I')]\n"
            "    out = ''\n"
            "    for v, s in vals:\n"
            "        while n >= v:\n"
            "            out += s; n -= v\n"
            "    return out"
        ),
    },
    {
        "id": "parse_simple_expr",
        "difficulty": "hard",
        "func": "solve",
        "prompt": "Write `solve(s)` evaluating an arithmetic expression string "
                  "containing non-negative integers, +, -, *, / (integer "
                  "division, truncating toward zero), parentheses and spaces, "
                  "with correct precedence. Do not use eval().",
        "tests": [
            ("solve('1+2*3')", 7),
            ("solve('(1+2)*3')", 9),
            ("solve('10/3')", 3),
            ("solve('2*(3+4)-5')", 9),
            ("solve('7')", 7),
        ],
        "reference": (
            "def solve(s):\n"
            "    import re\n"
            "    toks = re.findall(r'\\d+|[()*/+-]', s)\n"
            "    pos = [0]\n"
            "    def peek():\n"
            "        return toks[pos[0]] if pos[0] < len(toks) else None\n"
            "    def expr():\n"
            "        v = term()\n"
            "        while peek() in ('+', '-'):\n"
            "            op = toks[pos[0]]; pos[0] += 1\n"
            "            r = term(); v = v + r if op == '+' else v - r\n"
            "        return v\n"
            "    def term():\n"
            "        v = factor()\n"
            "        while peek() in ('*', '/'):\n"
            "            op = toks[pos[0]]; pos[0] += 1\n"
            "            r = factor()\n"
            "            v = v * r if op == '*' else int(v / r)\n"
            "        return v\n"
            "    def factor():\n"
            "        t = peek()\n"
            "        if t == '(':\n"
            "            pos[0] += 1; v = expr(); pos[0] += 1; return v\n"
            "        pos[0] += 1; return int(t)\n"
            "    return expr()"
        ),
    },

    # ---------------- edge-case heavy ----------------
    {
        "id": "edge_empty_inputs",
        "difficulty": "easy",
        "func": "solve",
        "prompt": "Write `solve(nums)` returning a dict with keys 'count', 'sum', "
                  "'min', 'max' for the list `nums`; for an empty list use 0 for "
                  "count and sum, and None for min and max.",
        "tests": [
            ("solve([1,2,3])", {'count': 3, 'sum': 6, 'min': 1, 'max': 3}),
            ("solve([])", {'count': 0, 'sum': 0, 'min': None, 'max': None}),
            ("solve([-1])", {'count': 1, 'sum': -1, 'min': -1, 'max': -1}),
            ("solve([0,0])", {'count': 2, 'sum': 0, 'min': 0, 'max': 0}),
            ("solve([5,-5])", {'count': 2, 'sum': 0, 'min': -5, 'max': 5}),
        ],
        "reference": (
            "def solve(nums):\n"
            "    return {'count': len(nums), 'sum': sum(nums),\n"
            "            'min': min(nums) if nums else None,\n"
            "            'max': max(nums) if nums else None}"
        ),
    },
    {
        "id": "edge_unicode_len",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(s)` returning the number of characters in `s` "
                  "counted as UNICODE CODE POINTS, so that a string containing "
                  "combining marks counts each code point separately.",
        "tests": [
            ("solve('abc')", 3),
            ("solve('')", 0),
            ("solve('\\u00e9')", 1),
            ("solve('e\\u0301')", 2),
            ("solve('\\U0001F600')", 1),
        ],
        "reference": "def solve(s):\n    return len(s)",
    },
    {
        "id": "edge_int_overflow",
        "difficulty": "easy",
        "func": "solve",
        "prompt": "Write `solve(a, b)` returning the product of two arbitrarily "
                  "large non-negative integers, as an integer (no wraparound, no "
                  "floating point).",
        "tests": [
            ("solve(2, 3)", 6),
            ("solve(0, 10**20)", 0),
            ("solve(10**10, 10**10)", 10**20),
            ("solve(1, 1)", 1),
            ("solve(999999937, 999999937)", 999999937 * 999999937),
        ],
        "reference": "def solve(a, b):\n    return a * b",
    },
    {
        "id": "edge_mutate_safety",
        "difficulty": "medium",
        "func": "solve",
        "prompt": "Write `solve(nums)` returning a NEW list containing the "
                  "elements of `nums` in sorted order, WITHOUT modifying the "
                  "caller's list.",
        "tests": [
            ("(lambda a: (solve(a), a)[0])([3,1,2])", [1, 2, 3]),
            ("(lambda a: (solve(a), a)[1])([3,1,2])", [3, 1, 2]),
            ("solve([])", []),
            ("(lambda a: (solve(a), a)[1])([])", []),
            ("(lambda a: (solve(a), a)[0])([1])", [1]),
        ],
        "reference": "def solve(nums):\n    return sorted(nums)",
    },
]
