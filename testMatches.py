from match import Match
from base import NLP

TESTS = {
    "test": {
        "HELLO": [
            "hello, world",
        ],
        "": [
            "I shall not be happy about no world",
        ],
    },
}

def test(mat, doc, correct):
    if correct == "":
        itr = mat(doc)
        return next(itr, None) is None
    for id, _ in mat(doc):
        if id == correct:
            return True
    return False

if __name__ == "__main__":
    doc = NLP()
    for nam, t in TESTS.items():
        print(f"Testing '{nam}'\n│ ", end="")
        m = Match(nam)
        success = 0
        amnt = 0
        for correct, li in t.items():
            for it in li:
                amnt += 1
                if test(m, doc(it), correct):
                    success += 1
                    print(".", end="")
                else:
                    print(f"\n│ TEST FAIL:\n│ │ {it}\n│ │ Failed to match '{correct or 'Dont match any'}'\n│ ", end="")
        print(f"\nResults for '{nam}': {success}/{amnt} passed")
