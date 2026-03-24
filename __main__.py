from __init__ import Parser

print("Loading...")

p = Parser()
print("\033[2J", end="", flush=True)

txt = ""
brk = False
while True:
    print("\033[2J\033[1;1H\033[0m", end="")
    print(txt)
    if txt == "":
        parsed = "\n\033[90mNo text yet"
    else:
        parsed = "\n\033[33m"+p(txt)
    if brk:
        print(parsed)
        break
    print(parsed, end=f"\033[1;{len(txt)+1}H\033[90m", flush=True)
    try:
        txt += input()
    except KeyboardInterrupt:
        txt = ""
    except EOFError:
        brk = True
