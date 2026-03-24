from spacy.matcher import Matcher
from base import NLP
import json
import os

class Match:
    __slots__ = ['nlp', 'matcher']
    def __init__(self, set):
        self.nlp = NLP()
        self.matcher = Matcher(self.nlp.vocab)
        with open(os.path.abspath(os.path.join(__file__, "..", "matches", set+".json"))) as f:
            for title, conts in json.load(f).items():
                self.matcher.add(title, conts)

    def __call__(self, doc):
        for mid, start, end in self.matcher(doc):
            yield self.nlp.vocab.strings[mid], (start, end)

