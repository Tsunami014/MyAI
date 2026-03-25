from __init__ import Parser

DBUG = 1 # Debug level; 0 no debug - 4 entirely debug

print("Loading...")

p = Parser([
    # Every matcher we want to use
    "test"
])
print("\033[2J", end="", flush=True)

txt = ""
brk = False
while True:
    print("\033[2J\033[1;1H\033[0m", end="")
    print("\033[34m"+txt)
    parsed = p.tree(txt,DBUG)
    if parsed == "":
        parsed = "\n\033[90mNo output"
    if brk:
        print(parsed+"\033[0m")
        break
    print("\033[0m"+parsed, end=f"\033[1;{len(txt)+1}H\033[90m", flush=True)
    try:
        txt += input()
    except KeyboardInterrupt:
        txt = ""
    except EOFError:
        brk = True
