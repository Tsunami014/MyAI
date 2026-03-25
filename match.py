from collections import defaultdict
from itertools import chain as chain_iter
import os

class Rule:
    __slots__ = []
    def __new__(cls, txt, *args):
        if cls is not Rule:
            return super().__new__(cls)
        if txt == '(':
            cls = Group
        elif txt == ')':
            cls = GroupEnd
        elif txt in Combination._OPTS:
            cls = Combination
        elif len(txt) >= 2 and (txt[:2] in Connection._CONS or txt[-2:] in Connection._CONS):
            cls = Connection
        else:
            cls = Criteria
        return super().__new__(cls)

    def __init__(self, txt):
        pass
    def combine(self, nxt):
        return False
    def combineLast(self):
        return
    def soloCheck(self):
        pass
    def __call__(self, parsed):
        return False

class Joinable(Rule):
    __slots__ = ['_nodecache', '_finder', '_parserid']
    def __init__(self, _):
        self._nodecache = None
        self._finder = None
        self._parserid = None
    def combine(self, nxt):
        if isinstance(nxt, Joiner):
            nxt.bef = self
            return False
        return True

    def get_nodes(self, parsed):
        pid = id(parsed)
        if self._parserid is not pid:
            self._parserid = pid
            self._nodecache = []
            self._finder = self.find_nodes(parsed)
        idx = 0
        while True:
            if self._parserid != pid:
                raise RuntimeError(
                    "Multiple parsing jobs were ran on this node at the same time for different parsers!"
                )
            if idx < len(self._nodecache):
                yield self._nodecache[idx]
            elif self._finder is not None:
                nxt = next(self._finder, None)
                if nxt is None:
                    self._finder = None
                    return
                else:
                    self._nodecache.append(nxt)
                    yield nxt
            else:
                return
            idx += 1

    def isMatching(self, tok, parsed):
        return False

    def find_nodes(self, parsed):
        yield from ()

    def __call__(self, parsed):
        for n in self.get_nodes(parsed):
            return True
        return False

class Joiner:
    _WORD = ("Join", "Joining unjoinable")
    def __init__(self, txt):
        self.bef = None
        self.aft = None
        self.typ = txt
    def combine(self, nxt):
        if isinstance(nxt, Joinable):
            self.aft = nxt
        return False
    def combineLast(self):
        raise ValueError(
            f"{self._WORD[0]} does not have anything after it!"
        )
    def soloCheck(self, single=False):
        noaft = self.aft is None
        nobef = self.bef is None
        if (not single) and noaft and nobef:
            raise ValueError(
                f"{self._WORD[1]} objects or {self._WORD[0].lower()} has nothing both before and after it!"
            )
        if noaft:
            raise ValueError(
                f"{self._WORD[1]} objects or {self._WORD[0].lower()} has nothing after it!"
            )
        if single:
            return
        if nobef:
            raise ValueError(
                f"{self._WORD[1]} objects or{self._WORD[0].lower()} has nothing before it!"
                )
        if type(self.bef) is not type(self.aft):
            raise ValueError(
                f"{self._WORD[1]} objects!"
            )

class Criteria(Joinable):
    __slots__ = ['modifs', 'match', 'txt', '_node']
    _MODIFS = {"^", "[", "]"}
    _MATCHES = {"*", "'", "%", "$", "#", "=", "?"}
    def __init__(self, txt):
        super().__init__(txt)
        self._node = None
        self.modifs = set()
        for idx, c in enumerate(txt):
            if c in self._MODIFS:
                if c in self.modifs:
                    raise ValueError(
                        "Modifier specified multiple times: "+c
                    )
                self.modifs.add(c)
            else:
                break
        if txt[idx] in self._MATCHES:
            self.match = txt[idx]
            self.txt = txt[idx+1:]
        else:
            self.match = ""
            self.txt = txt[idx:]
        if self.match == '*' and self.txt != '':
            raise ValueError(
                "Cannot have text with '*' matcher!"
            )
        if self.txt[0] == '"':
            self.txt = self.txt[1:]

    def isMatching(self, t, _=None):
        if self.match == '*':
            return True
        tok = t.tok
        m = self.match

        caseSense = "^" in self.modifs
        mina = "[" in self.modifs
        ainm = "]" in self.modifs
        match = self.txt if caseSense else self.txt.lower()

        against = None
        againsts = None

        if m == "'":
            againsts = {tok.lemma_, tok.norm_}
        elif m == "#":
            againsts = set(tok.info + tok.personalInfo)

        elif m == "%":
            against = tok.pos_
        elif m == "$":
            against = tok.dep_
        elif m == "=":
            against = tok.Usage()
        elif m == "?":
            against = tok.Type()

        else:
            against = tok.text

        if against is None:
            if caseSense:
                againsts = {i.lower() for i in againsts}
            if mina or ainm:
                for a in againsts:
                    if mina and match in a:
                        return True
                    if ainm and a in match:
                        return True
                return False
            return match in againsts
        if mina or ainm:
            if mina and match in a:
                return True
            if ainm and a in match:
                return True
            return False
        return match == against

    def find_nodes(self, parsed):
        yield from parsed.find(self.isMatching)

class Connection(Joinable, Joiner):
    _CONS = {"--", "~~"}
    _WORD = ("Connection", "Connecting unconnectable")
    __slots__ = ['directions', 'link']
    def __init__(self, txt):
        Joiner.__init__(self, txt)
        Joinable.__init__(self, txt)
        if txt[:2] in self._CONS:
            typ = txt[2:]
            self.link = txt[:2]
        else:
            typ = txt[:-2]
            self.link = txt[-2:]
        dir = defaultdict(int)
        if typ == "":
            typ = "+"
        typ = (typ
            .replace('*', '|=')
            .replace('+', ':"')
            .replace('|', '^v')
            .replace(':', '^.')
            .replace('=', '{}')
            .replace('"', '<>')
        )
        for c in typ:
            if c == '}':
                dir["aft"] = max(2, dir["aft"])
            elif c == '>':
                dir["aft"] = max(1, dir["aft"])
            elif c == '{':
                dir["bef"] = max(2, dir["bef"])
            elif c == '<':
                dir["bef"] = max(1, dir["bef"])
            elif c == '^':
                dir["parent"] = max(1, dir["parent"])
            elif c == '`':
                dir["parent"] = max(2, dir["parent"])
            elif c == 'v':
                dir["child"] = max(2, dir["child"])
            elif c == '.':
                dir["child"] = max(1, dir["child"])
            else:
                raise ValueError(
                    "Unknown connection type: "+txt
                )
        self.directions = dir

    def isMatching(self, tok, parsed):
        return (self.aft is not None and
                self.aft.isMatching(tok, parsed) and
            tok in self.get_nodes(parsed)
        )

    def connecteds(self, tok):
        dir = self.directions
        if dir["child"] >= 1:
            yield from (tok.flatten(self.link != "~~", False) if dir["child"] >= 2 else
                    (tok.usefulChildren if self.link == "~~" else tok.children))

        par = tok.parent
        children = par.children
        if par is None:
            return
        idx = None
        bef = dir["bef"] > 0
        aft = dir["aft"] > 0
        if bef or aft:
            try:
                idx = children.index(tok)
            except IndexError:
                raise RuntimeWarning(
                    "A child token I should be using has become detached from its parent!"
                )
        if idx is not None:
            if aft:
                childamnt = len(children)
                idx += 1
                while idx < childamnt:
                    c = children[idx]
                    if c.Usage() != "":
                        yield c
                        if dir["after"] == 1:
                            break
            if bef:
                idx -= 1
                while idx >= 0:
                    c = children[idx]
                    if c.Usage() != "":
                        yield c
                        if dir["before"] == 1:
                            break
        if dir["parent"] >= 1:
            yield par
            if dir["parent"] >= 2:
                p = par.parent
                while p is not None:
                    yield p
                    p = p.parent

    def find_nodes(self, parsed):
        if self.bef is None or self.aft is None:
            # Just in case; you never know
            return
        for n in self.bef.get_nodes(parsed):
            for o in self.connecteds(n):
                if self.aft.isMatching(o, parsed):
                    yield o

    def combine(self, nxt):
        if isinstance(nxt, Joiner):
            nxt.bef = self
            self.aft = nxt
        elif isinstance(nxt, Joinable):
            self.aft = nxt
        return False

class Generator:
    AND = all
    OR = any
    def __new__(cls, parsed, vals, func=AND) -> bool:
        return func(cls.gen(vals, parsed))

    @classmethod
    def gen(cls, vals, parsed):
        for v in vals:
            yield v(parsed)

class Combination(Joiner, Rule):
    _OPTS = {
        "?": lambda _: True,
        "!": lambda a: not a,
        "|": Generator.OR,
        "&": Generator.AND,
    }
    _SINGLE = {"!"}
    _WORD = ("Combination", "Combining uncombineable")
    @property
    def isSingle(self):
        return self.typ in self._SINGLE
    def soloCheck(self):
        super().soloCheck(self.isSingle)
    def __call__(self, parsed):
        if self.isSingle:
            return self._OPTS[self.typ](self.aft(parsed))
        return Generator(parsed, (self.bef, self.aft), self._OPTS[self.typ])

class Group(Rule):
    __slots__ = ['children', 'func']
    def __init__(self, _, children=None, func=Generator.AND):
        self.children = children or []
        self.func = func
    def combine(self, nxt):
        if type(nxt) is GroupEnd:
            return False
        self.children.append(nxt)
        return True
    def combineLast(self):
        raise ValueError(
            "Too many group beginnings!"
        )
    def __call__(self, parsed):
        return Generator(parsed, self.children, self.func)

class GroupEnd(Rule):
    def soloCheck(self):
        raise ValueError(
            "Too many group endings!"
        )

class Match:
    __slots__ = ['rules']
    def __init__(self, set):
        with open(os.path.abspath(os.path.join(__file__, "..", "matches", set+".txt"))) as f:
            rules = defaultdict(list)
            title = None
            p = None
            for line in chain_iter(f, ("###",)):
                if line.startswith("###"):
                    ntit = line[3:].strip()
                    if ntit:
                        title = ntit
                    if p is not None:
                        rules[title].append(p.send(None))
                    p = self.parser()
                    next(p)
                else:
                    for c in line:
                        p.send(c)
            self.rules = {
                nam: Group(None, i, Generator.OR) for nam, i in rules.items()
            }

    def parser(self):
        collected = ""
        comment = False
        out = []
        last = None

        def end():
            nonlocal collected, last
            if collected != "":
                new = Rule(collected)
                if last is None:
                    last = new
                else:
                    if not last.combine(new):
                        out.append(last)
                        last = new
                collected = ""

        while True:
            c = yield
            if c is None:
                break
            if c == '\\':
                comment = not comment
            elif comment and c == '\n':
                comment = False
            if not comment:
                if c in '()':
                    end()
                    collected = c
                    end()
                elif c in '\n\t ':
                    end()
                else:
                    collected += c

        # Cleanup, check for incomplete parsing
        if last is not None:
            last.combineLast() # Checks if the node finished parsing
            out.append(last)
        if len(out) == 0:
            yield None
        for o in out:
            o.soloCheck() # Checks if the nodes are allowed to be by themself
        # Return collected rule
        yield Group(None, out, Generator.AND)

    def __call__(self, parsed, blacklist=None):
        for nam, r in self.rules.items():
            if (blacklist is None or nam in blacklist) and r(parsed):
                yield nam

