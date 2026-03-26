from match import Match
from parse import Parser

TESTS = {
    "test": {
        "HELLO": [
            "please print hello, world",
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
    for _ in mat(doc, whitelist=[correct]):
        # The whitelist ensures it's only matching the correct thing anyway
        return True
    return False

if __name__ == "__main__":
    p = Parser()
    for nam, t in TESTS.items():
        print(f"Testing '{nam}'\n│ ", end="")
        m = Match(nam)
        success = 0
        amnt = 0
        for correct, li in t.items():
            for it in li:
                amnt += 1
                if test(m, p(it), correct):
                    success += 1
                    print(".", end="")
                else:
                    print(f"\n│ TEST FAIL:\n│ │ {it}\n│ │ Failed to match '{correct or 'Dont match any'}'\n│ ", end="")
        print(f"\nResults for '{nam}': {success}/{amnt} passed")
