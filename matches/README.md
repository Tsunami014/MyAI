# Contents of matches files
Matches files are broken up into named segments beginning with `### Title` on the start of a line, 'Title' obviously being replaced with the match group name below there.
`###` by itself uses the same title as the last, and the same titles are different versions that can match

Matches are made up of a bunch of criteria, separated by nothing or optional connectors between any 2

## Criteria
These are all case insensitive
- `*` any token
- `word` word must be exactly that
- `'root` the root (lemma) or normalised (norm) version of that token must fit that criteria (lowercase again) (This changes e.g. "went" to "go" and "'t" to "not")
- `%pos` the word pos, e.g. "AUX" or "ADJ"
- `$dep` is the word dep, e.g. "nsubj"
The below are not from the original library but I made some criteria that tokens can be:
- `#tag` is a rendition of a morph tag (e.g. "statement", "happening", "1stPerson") - the stuff in `V()` (and ONLY `V`)
- `=usage` is the usage of the token, e.g. "clause" or "description"
- `?type` is the type of token, e.g. "event" or "object"

### Prefixes
All the below may not apply if it does not make sense to, e.g. for `*` (but is still allowed)
These can be in any order
- `^` indicates it is case SENSITIVE (but why would you use this?)
- `[` means it matches if the word provided is present in the required text
- `]` means it matches if the required text is present in the word provided

These cannot be in any order (see structure below)
- `"` to use special characters (must be innermost)

### Criteria structure
`<prefixes><symbols><"><text>`
For combined criteria:
`<variable>(<criterion and combining things>)`

Setting a variable can only be on the outside of combined criteria, so you can have a 'combined' criteria with only one criteria to assign to a variable

## Connectors
If 2 names are not connected then they must just exist to meet the criteria. Each connector must contain a link in it at the start or end, but below are the best looking places for `--`. Multiple nodes can be connected simultaniously, e.g. `A -- B -- C`. These can be combined, e.g. `--^>` or `<|--`. You can put these between names to connect them:

Siblings:
- `A --} B` B must be a sibling that comes after A
- `A {-- B` B must be a sibling that comes before A
- `A --> B` B must be a sibling that comes directly after A
- `A <-- B` B must be a sibling that comes directly before A
Children/parents:
- `A --v B` B must be a child of A
- `A --. B` B must be a direct child of A
- `A --^ B` B must be the direct parent of A
- `A --`\`` B` B must be any parent of A
Combinations:
- `A --" B` B must be a direct sibling of A
- `A --: B` B must be a direct child or parent of A
- `A --= B` B must be a sibling of A
- `A --| B` B must be a child or direct parent of A
- `A --+ B` B must be a direct sibling, child or parent of A
- `A --# B` B must be a sibling or direct child or parent of A
- `A --* B` B must be a sibling, child or direct parent of A

Extra:
- `A -- B` Shorthand for `A --+ B` (if using another connector looks like e.g. `A ~~ B`)

I do not recommend including 2 directions in one statement, and it's probably best to also go left-right up-down to be nice

### Connector links
A connector must contain at least one of the following in it somewhere (and not multiple different ones):
- `--` a regular connection
- `~~` ignoring "useless" tokens (ones with no use value)

## Combining
Can use brackets `()` for control over the ordering of these
These can apply to either criteria or connections (a criteria is just a node existing)
They are calculated in this order of operations:
- `!A` A must not be satisfied
- `?A` A is evaluated and doesn't have to be satisfied
- `A & B` both A and B must be satisfied
- `A | B` either A or B must be satisfied


## Variables
Variables are criteria that can be used in multiple places. If the variable name starts with a `!`, the variable will be exported and the node it refers to will be accessible!
`{text}criteria` and `{text}` set and use a variable node, respectively (so you can connect a node to multiple things)

## Extra
- `\ Comment` and `\ Comment \` - self explanatory

