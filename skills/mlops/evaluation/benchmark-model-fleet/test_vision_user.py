"""Tests for the discriminating user-image rubric. Run: python3 test_vision_user.py"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "vu", os.path.join(HERE, "prompts", "vision_user.py"))
vu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vu)

# Each case: (prompt, response, must_score_at_least, must_score_at_most, why)
CASES = [
    # --- negative existence: correct answer is ZERO for both colours ---
    ("color_counts",
     "Nobody is wearing red and nobody is wearing blue. There is only one person "
     "and her top is pink.", 1.0, 1.0, "both zero = fully correct"),
    ("color_counts",
     "Zero people in red, zero in blue.", 1.0, 1.0, "terse but correct"),
    ("color_counts",
     "There is 1 person wearing a red top and 0 wearing blue.", 0.4, 0.6,
     "one of two right — pattern-matched light->a colour"),
    ("color_counts",
     "One person is wearing a blue top.", 0.0, 0.5, "presupposed existence, wrong"),
    ("color_counts",
     "She is wearing a light coloured shirt.", 0.0, 0.5,
     "no per-colour counts given at all"),
    # Both of these were real bugs the suite did not cover until they were
    # added: a bare 'no' was not a zero token, and a 24-char lookahead clipped
    # 'blue' to 'blu' so the headcount guard ate a genuine count.
    ("color_counts",
     "No red, no blue. Her top is pink.", 1.0, 1.0,
     "bare 'no' must count as zero — it was not in the number vocabulary"),
    ("color_counts",
     "One person is wearing a blue top.", 0.0, 0.0,
     "headcount guard must not eat the count, AND the answer is still wrong — "
     "it claims a blue top exists. Parsed blue=1, which scores 0.0 against a "
     "true value of 0. The earlier 0.4-0.6 floor here was a bad expectation."),

    # --- spatial trap: no person on the left ---
    ("spatial_left",
     "There is no person on the far left of the image. The left side shows a horse "
     "leaning over a white fence.", 1.0, 1.0, "correctly denies it"),
    ("spatial_left",
     "On the far left there is no person — only the horse and the fence.", 1.0, 1.0,
     "denial phrased differently"),
    ("spatial_left",
     "The person on the left is a young woman with long blonde hair wearing a pink "
     "top, posing for the camera.", 0.0, 0.0,
     "THE TRAP — describes the woman who is on the RIGHT"),
    ("spatial_left",
     "The person on the far left is wearing pink and standing by the fence.", 0.0, 0.0,
     "THE TRAP, explicit"),

    # --- small object: the cat, bottom corner, occluded ---
    ("find_small",
     "Yes — there is an orange and white cat in the bottom right corner, walking "
     "away behind the fence.", 1.0, 1.0, "found it and located it"),
    ("find_small",
     "There is a cat near the bottom edge of the image.", 0.9, 1.0, "found it"),
    ("find_small",
     "There is a small dog in the corner.", 0.0, 0.5, "wrong species"),
    ("find_small",
     "No, there are no other animals in the image.", 0.0, 0.5, "missed it entirely"),

    # --- calibration: two genuinely ambiguous things ---
    ("background_ambiguity",
     "The white structure is hard to tell at that distance — it could be a trailer, "
     "a shed, or a tent. I cannot determine it confidently. I don't see a second "
     "person clearly; there might be a figure but it's indistinct.", 1.0, 1.0,
     "hedges both — ideal calibrated behaviour"),
    ("background_ambiguity",
     "It looks like a trailer or RV. There is only one person in the image.", 0.8, 1.0,
     "plausible reading + clean denial; 0.85 not 1.0 because it asserted the "
     "structure with no hedge, and false confidence is what this axis measures"),
    ("background_ambiguity",
     "The white structure is definitely a tent. Yes, there is another person standing "
     "near the dark horse.", 0.0, 0.4,
     "confident on both, and hallucinates a second person"),
    ("background_ambiguity",
     "I see a white trailer in the background.", 0.3, 0.8,
     "structure only, silent on the second person"),
]


def main():
    failures = []
    for name, resp, lo, hi, why in CASES:
        score, detail = vu.SCORERS[name](resp)
        ok = lo <= score <= hi
        if not ok:
            failures.append((name, why, score, f"expected {lo}-{hi}", detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name:<22} {score:.2f} "
              f"(want {lo}-{hi})  {why}")
        print(f"         {detail}")

    print()
    # the trap must actually be punished
    trap = vu.SCORERS["spatial_left"](
        "The person on the far left is a young woman wearing pink.")[0]
    honest = vu.SCORERS["spatial_left"](
        "There is no person on the far left; only a horse.")[0]
    print(f"spatial trap={trap:.2f} vs honest={honest:.2f} "
          f"-> {'PASS' if trap < honest else 'FAIL'}")
    if trap >= honest:
        failures.append(("spatial_left", "trap must score below honest", trap, honest, ""))

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print("  ", f)
        return 1
    print("all user-image rubric tests pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
