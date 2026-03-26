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
        # If False will save this to the list (will NOT combine with the next)
        # If True it WILL combine, meaning the next rule is skipped
        # If None will combine backwards (this object becomes None)
        return False
    def combineLast(self):
        return
    def soloCheck(self):
        pass
    def __call__(self, parsed):
        return False

    def __repr__(self):
        slots = {nam: getattr(self, nam) for nam in self.__slots__ if nam[0] != '_'}
        sltstxt = ", ".join(
                i+"="+(rpr if len(rpr:=repr(j)) < 25 else rpr[:25]+"...") for i, j in slots.items())
        if sltstxt != "":
            sltstxt = " "+sltstxt
        return f"<{self.__class__.__name__}{sltstxt}>"

class Joinable(Rule):
    __slots__ = ['_nodecache', '_finder', '_parserid']
    def __init__(self, _):
        self._nodecache = None
        self._finder = None
        self._parserid = None
    def combine(self, nxt):
        if isinstance(nxt, Joiner):
            nxt.bef = self
            return None
        return False

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

    def filter_nodes(self, parsed, frm):
        for n in frm:
            if self.isMatching(n, parsed):
                yield n

    def isMatching(self, tok, parsed):
        return False

    def find_nodes(self, parsed):
        yield from parsed.find(self.isMatching)

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
        if self.aft is None and isinstance(nxt, Joinable):
            self.aft = nxt
            return True
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

    def connecteds(self, tok):
        yield self.aft

class JoinableJoiner(Joinable, Joiner):
    def __init__(self, txt):
        Joiner.__init__(self, txt)
        Joinable.__init__(self, txt)

    def isMatching(self, tok, parsed):
        for _ in self.filter_nodes(self, parsed, tok):
            return True
        return False

    def filter_nodes(self, parsed, frm):
        if self.bef is None or self.aft is None:
            # Just in case; you never know
            return
        for n in frm:
            if self.bef.isMatching(n, parsed):
                for n2 in self.connecteds(n):
                    if self.aft.isMatching(n2, parsed):
                        yield n2

    def combine(self, nxt):
        if self.aft is None:
            if isinstance(nxt, Joinable):
                self.aft = nxt
                return True
        else:
            if isinstance(self.aft, Joiner):
                return self.aft.combine(nxt)
            elif isinstance(nxt, Joiner):
                nxt.bef = self.aft
                self.aft = nxt
                return True
        return False

    def find_nodes(self, parsed):
        if self.bef is None:
            return
        yield from self.filter_nodes(parsed, self.bef.get_nodes())

    def soloCheck(self, single=False):
        Joiner.soloCheck(self, single)

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
            againsts = set(t.info + t.personalInfo)

        elif m == "%":
            against = tok.pos_
        elif m == "$":
            against = tok.dep_
        elif m == "=":
            against = t.Usage()
        elif m == "?":
            against = t.Type()

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
        against = against if caseSense else against.lower()
        if mina or ainm:
            if mina and match in against:
                return True
            if ainm and against in match:
                return True
            return False
        return match == against

class Connection(JoinableJoiner):
    _CONS = {"--", "~~"}
    _WORD = ("Connection", "Connecting unconnectable")
    __slots__ = ['directions', 'link']
    def __init__(self, txt):
        super().__init__(txt)
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
            .replace('#', ':=')
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
                    idx += 1
            if bef:
                idx -= 1
                while idx >= 0:
                    c = children[idx]
                    if c.Usage() != "":
                        yield c
                        if dir["before"] == 1:
                            break
                    idx -= 1
        if dir["parent"] >= 1:
            yield par
            if dir["parent"] >= 2:
                p = par.parent
                while p is not None:
                    yield p
                    p = p.parent

class Funcs:
    def __new__(cls):
        raise RuntimeError("Class not instantiateable!")

class Combination(JoinableJoiner):
    _OPTS = {
            # (single, output afts too?, criteria)
        "!": (True, False, (lambda a, afts: a not in afts)),
        "?": (True, False, (lambda a, afts: True)),
        "|": (False, True, (lambda a, afts: True)),
        "&": (False, False, (lambda a, afts: a in afts)),
    }
    _WORD = ("Combination", "Combining uncombineable")
    @property
    def isSingle(self):
        return self._OPTS[self.typ][0]
    def soloCheck(self):
        super().soloCheck(self.isSingle)

    def filter_nodes(self, parsed, frm):
        if self.bef is None:
            # Just in case
            return
        typ = self._OPTS[self.typ]
        if typ[0]: # isSingle
            origafts = parsed.flatten()
        else:
            if self.aft is None:
                return
            origafts = self.aft.get_nodes(parsed)
        if typ[1]: # use afts too
            afts = set()
            for a in origafts:
                yield a
                afts.add(a)
        else:
            afts = set(origafts)
        for n in frm:
            if (not typ[1]) or n not in afts:
                if typ[2](n, afts):
                    yield n

class Group(JoinableJoiner):
    __slots__ = ['last', 'children', 'func', 'done']
    def __init__(self, _, children=None, func=all):
        self.children = []
        self.func = func
        self.done = False
        self.last = None
        super().__init__(None)

        for c in children or []:
            if self.combine(c) is not True:
                break

    @property
    def bef(self):
        if len(self.children) == 0:
            return None
        return self.children[0]
    @bef.setter
    def bef(self, new):
        if new is None:
            # Just in case
            if len(self.children) == 0:
                return
            self.children.pop(0)
            return
        if len(self.children) == 0:
            self.children.append(new)
        else:
            self.children[0] = new
    @property
    def aft(self):
        if len(self.children) < 2:
            return None
        return self.children[-1]
    @aft.setter
    def aft(self, new):
        if new is None:
            if len(self.children) >= 2:
                self.children.pop()
            return
        if len(self.children) < 2:
            self.children.append(new)
        else:
            self.children[-1] = new

    def _filter_node_inner(self, parsed, n, child=0):
        c = self.children[child]
        if not c.isMatching(n, parsed):
            return
        nxt = child + 1
        if nxt < len(self.children):
            for n2 in self.connecteds(n):
                yield from self._filter_node_inner(parsed, n2, nxt)
        else:
            yield from self.connecteds(n)
    def filter_nodes(self, parsed, frm):
        for n in frm:
            yield from self._filter_node_inner(parsed, n)

    def combine(self, nxt):
        if self.done:
            if isinstance(nxt, Joiner):
                nxt.bef = self
                return None
            return False
        if type(self.last) is not Group and type(nxt) is GroupEnd:
            self.done = True
            if self.last is not None:
                self.last.combineLast() # Checks if the node finished parsing
                self.children.append(self.last)
            if len(self.children) == 0:
                return None
            for o in self.children:
                o.soloCheck() # Checks if the nodes are allowed to be by themself
            return True
        if self.last is None:
            self.last = nxt
        else:
            comb = self.last.combine(nxt)
            if comb is False:
                self.children.append(self.last)
                self.last = nxt
            elif comb is None:
                self.last = nxt
        return True
    def combineLast(self):
        if self.done:
            return
        raise ValueError(
            "Too many group beginnings!"
        )

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
                nam: Group(None, i, any) for nam, i in rules.items()
            }

    def parser(self):
        collected = ""
        out = Group(None, [], all)
        comment = False

        def end():
            nonlocal collected
            if collected != "":
                if out.combine(Rule(collected)) is not True:
                    raise ValueError(
                        "The main group stopped being greedy, something's wrong - are there too many group endings?"
                    )
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

        if out.done:
            raise ValueError("Main group finished prematurely, maybe too many group endings?")
        out.combine(GroupEnd(None))
        if not out.done:
            raise ValueError("Main group isn't finished yet! Are there too many group openings?")
        yield out

    def __call__(self, parsed, *, blacklist=None, whitelist=None):
        for nam, r in self.rules.items():
            if ((blacklist is None or nam not in blacklist) and
                (whitelist is None or nam in whitelist) and
                r(parsed)):
                    yield nam

