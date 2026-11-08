"""Unit tests for the grounded vision rubric. Run: python3 test_vision_rubric.py"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "vg", os.path.join(HERE, "prompts", "vision_grounded.py"))
vg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vg)

CASES = [
    # (prompt_name, response, should_score_above, label)
    ("count_people",
     "There are three people in this image. One is at the bench, one at the lathe, "
     "one by the tool chest.", 0.95, "correct count + reasoning"),
    ("count_people",
     "I can see 3 people working in the shop.", 0.95, "digit form"),
    ("count_people",
     "There are five people in the image.", 0.30, "wrong count, partial credit "
     "only — linear curve: off-by-1 = 0.67, off-by-2 = 0.33, and it must not "
     "collapse to 0 for simply being wrong"),
    ("count_people",
     "I cannot determine an exact number from this image.", 0.0, "refusal scores low"),
    ("identify_objects",
     "I can see a wooden workbench, a bench lathe for turning spindles, and a red "
     "tool chest with drawers for storing hand tools.", 0.95, "all three named"),
    ("identify_objects",
     "There is a workbench and a cabinet with many drawers.", 0.15, "two of three, "
     "synonym 'cabinet' accepted for tool chest"),
    ("identify_objects",
     "Mostly wood and some metal objects.", 0.0, "vague, no real names"),
    ("describe_setting",
     "This is a woodworking workshop. Someone is doing carpentry at the bench.",
     0.95, "setting + activity"),
    ("describe_setting",
     "It looks like an indoor space with some furniture.", 0.0, "neither axis hit"),
    ("count_and_locate",
     "Three people: one planing a board at the workbench, one seated at the lathe, "
     "one standing near the tool chest. There is a lathe and a workbench visible.",
     0.95, "both axes strong"),
    # --- the critical one: negation must NOT count as hallucination ---
    ("identify_objects",
     "A workbench, lathe, and tool chest. There is no dog, car, or laptop anywhere "
     "in the image.", 0.95, "mentions absent objects only to DENY them"),
    ("identify_objects",
     "A workbench and a lathe. Also I see a dog sitting in the corner and a laptop "
     "on the bench.", 0.60, "positively asserts absent objects -> penalized"),
]


def main():
    failures = []
    for name, resp, floor, label in CASES:
        score, detail = vg.SCORERS[name](resp)
        ok = score >= floor
        flag = "PASS" if ok else "FAIL"
        if not ok:
            failures.append((name, label, score, floor, detail))
        print(f"[{flag}] {name:<18} {score:.3f} (floor {floor:.2f})  {label}")
        print(f"         {detail}")

    # the negation case must score HIGHER than the positive-assertion case
    neg = vg.SCORERS["identify_objects"](
        "A workbench, lathe, and tool chest. There is no dog, car, or laptop.")[0]
    pos = vg.SCORERS["identify_objects"](
        "A workbench, lathe, tool chest. I also see a dog, a car, and a laptop.")[0]
    print(f"\nnegation-safe={neg:.3f} vs hallucinating={pos:.3f} "
          f"-> {'PASS' if neg > pos else 'FAIL'}")
    if neg <= pos:
        failures.append(("negation", "denying an absent object must outscore "
                        "asserting it", neg, pos, "ordering inverted"))

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print("  ", f)
        return 1
    print("all rubric tests pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
