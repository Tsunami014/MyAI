from __init__ import Parser

print("Loading...")

p = Parser()
print("\033[2J", end="", flush=True)

txt = ""
brk = False
while True:
    print("\033[2J\033[1;1H\033[0m", end="")
    print("\033[34m"+txt)
    parsed = p(txt)
    if parsed == "":
        parsed = "\n\033[90mNo output"
    if brk:
        print(parsed)
        break
    print("\033[0m"+parsed, end=f"\033[1;{len(txt)+1}H\033[90m", flush=True)
    try:
        txt += input()
    except KeyboardInterrupt:
        txt = ""
    except EOFError:
        brk = True
