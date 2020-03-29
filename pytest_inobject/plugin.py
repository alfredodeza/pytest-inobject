from difflib import SequenceMatcher, Differ, IS_CHARACTER_JUNK
from difflib import get_close_matches as difflib_close_matches


def ndiff(a, b, linejunk=None, charjunk=IS_CHARACTER_JUNK):
    return FullContextDiffer(linejunk, charjunk).compare(a, b)


def get_close_matches(left, right):
    if isinstance(right, (str, unicode)):
        right = right.split()
    return difflib_close_matches(left, [str(i) for i in right])


class FullContextDiffer(Differ):

    def _fancy_replace(self, a, alo, ahi, b, blo, bhi):
        r"""
        When replacing one block of lines with another, search the blocks
        for *similar* lines; the best-matching pair (if any) is used as a
        synch point, and intraline difference marking is done on the
        similar pair. Lots of work, but often worth it.

        Example:

        >>> d = Differ()
        >>> results = d._fancy_replace(['abcDefghiJkl\n'], 0, 1,
        ...                            ['abcdefGhijkl\n'], 0, 1)
        >>> print ''.join(results),
        - abcDefghiJkl
        ?    ^  ^  ^
        + abcdefGhijkl
        ?    ^  ^  ^
        """

        # don't synch up unless the lines have a similarity score of at
        # least cutoff; best_ratio tracks the best score seen so far
        best_ratio, cutoff = 0.14, 0.15
        cruncher = SequenceMatcher(self.charjunk)
        eqi, eqj = None, None   # 1st indices of equal lines (if any)

        # search for the pair that matches best without being identical
        # (identical lines must be junk lines, & we don't want to synch up
        # on junk -- unless we have to)
        for j in xrange(blo, bhi):
            bj = b[j]
            cruncher.set_seq2(bj)
            for i in xrange(alo, ahi):
                ai = a[i]
                if ai == bj:
                    if eqi is None:
                        eqi, eqj = i, j
                    continue
                cruncher.set_seq1(ai)
                # computing similarity is expensive, so use the quick
                # upper bounds first -- have seen this speed up messy
                # compares by a factor of 3.
                # note that ratio() is only expensive to compute the first
                # time it's called on a sequence pair; the expensive part
                # of the computation is cached by cruncher
                if cruncher.real_quick_ratio() > best_ratio and \
                      cruncher.quick_ratio() > best_ratio and \
                      cruncher.ratio() > best_ratio:
                    best_ratio, best_i, best_j = cruncher.ratio(), i, j
        if best_ratio < cutoff:
            # no non-identical "pretty close" pair
            if eqi is None:
                # no identical pair either -- treat it as a straight replace
                for line in self._plain_replace(a, alo, ahi, b, blo, bhi):
                    yield line
                return
            # no close pair, but an identical pair -- synch up on that
            best_i, best_j, best_ratio = eqi, eqj, 1.0
        else:
            # there's a close pair, so forget the identical pair (if any)
            eqi = None

        # a[best_i] very similar to b[best_j]; eqi is None iff they're not
        # identical

        # pump out diffs from before the synch point
        for line in self._fancy_helper(a, alo, best_i, b, blo, best_j):
            yield line

        # do intraline marking on the synch pair
        aelt, belt = a[best_i], b[best_j]
        if eqi is None:
            # pump out a '-', '?', '+', '?' quad for the synched lines
            atags = btags = ""
            cruncher.set_seqs(aelt, belt)
            for tag, ai1, ai2, bj1, bj2 in cruncher.get_opcodes():
                la, lb = ai2 - ai1, bj2 - bj1
                if tag == 'replace':
                    atags += '^' * la
                    btags += '^' * lb
                elif tag == 'delete':
                    atags += '-' * la
                elif tag == 'insert':
                    btags += '+' * lb
                elif tag == 'equal':
                    atags += ' ' * la
                    btags += ' ' * lb
                else:
                    raise ValueError, 'unknown tag %r' % (tag,)
            for line in self._qformat(aelt, belt, atags, btags):
                yield line
        else:
            # the synch pair is identical
            yield '  ' + aelt

        # pump out diffs from after the synch point
        for line in self._fancy_helper(a, best_i+1, ahi, b, best_j+1, bhi):
            yield line


def as_string(string):
    """
    Ensure that whatever type of string is incoming, it is returned as an
    actual string, versus 'bytes' which Python 3 likes to use.
    """
    if isinstance(string, bytes):
        # we really ignore here if we can't properly decode with utf-8
        return string.decode('utf-8', 'ignore')
    return string


def is_single_line(string):
    try:
        return len(string.split('\n')) == 1
    except AttributeError:
        return True


def get_ratio(left, right):
    return SequenceMatcher(None, left, right).ratio()


def calculate_ratio(left, line, single_word=True):
    """
    Calculate the ratio from comparing the "left" value of an assertion with
    a line, this `line` value can also be a single word.
    """
    if not isinstance(line, str):
        return None
    compare_against = line.strip()
    if single_word:
        matches = get_close_matches(left, line.split())
        if matches:
            compare_against = matches[0]
        else:
            return None

    #return SequenceMatcher(None, left, compare_against).ratio()
    return get_ratio(left, line)


def best_right_comparison(left, line):
    """
    When there is too much drift from the beginning and the tail of ``line``
    against left, then it is useful to start trimming out from line until we
    get a better ratio (if any).

    This heuristic is done by measuring the ratio every time an item from
    ``line.split()`` is taken off. If the ratio improves it keeps going until
    it doesn't. Then it tries from the tail.

    This only is done against ``line`` because the common usage is comparing
    a small string in a long line.
    """
    left = left.strip()
    line = line.strip()
    baseline_ratio = get_ratio(left, line)
    # set a max ratio to improve the sequence, since trimming leading/trailing items
    # might lead to a perfectly matching line with no need to compare anything
    max_ratio = 0.75
    #baseline_parts = line.split()
    line_parts = line.split()

    # start by the head
    better_previous = lambda: previous_ratio > current_ratio
    best_line = line
    current_line = line
    previous_line = line
    current_ratio = baseline_ratio
    previous_ratio = baseline_ratio

    for count in range(len(line_parts)):
        current_line = ' '.join(line_parts[count:])
        current_ratio = get_ratio(left, current_line)
        if current_ratio >= max_ratio:
            break
        if current_ratio < previous_ratio:
            if better_previous():
                best_line = previous_line
                break
        previous_line = current_line
        previous_ratio = current_ratio
        best_line = current_line

    if current_ratio >= max_ratio:
        return best_line

    # check if the current line is now better
    if get_ratio(left, best_line) > baseline_ratio:
        line_parts = current_line.split()

    # Now do it by reversing
    for count in range(len(line_parts)-1, 1, -1):
        current_line = ' '.join(line_parts[:count])
        current_ratio = get_ratio(left, current_line)
        if current_ratio >= max_ratio:
            break
        if current_ratio < previous_ratio:
            if better_previous():
                best_line = previous_line
                break
        previous_line = current_line
        previous_ratio = current_ratio
        best_line = current_line

    return best_line


def closest_line_match(left, text):
    # if left is one word, then we try to get close matches
    single_word = len(left.split()) == 1
    ratios = {}

    if isinstance(text, (str, unicode)):
        text_parts = text.split('\n')
    else:
        text_parts = text

    for count, line in enumerate(text_parts):
        ratio = calculate_ratio(left, line, single_word)
        if ratio:
            ratios[count] = {'ratio': ratio, 'line': line}

    if not ratios:
        return text, []
    sorted_lines = sorted(ratios.items(), key=lambda x: x[1]['ratio'], reverse=True)
    # return the closest match
    return sorted_lines[0][1]['line'], sorted_lines


def string_repr(string):
    """
    It is nicer to see strings displayed with quotes when reporting, otherwise
    whitespace might not be apparent.
    """
    return "'%s'" % string


def pytest_assertrepr_compare(config, op, left, right):
    valid_scenario = False
    # We can only be useful up to a single line from left
    if not is_single_line(left):
        return

    if isinstance(left, (str, unicode)) and isinstance(right, list) and op == "in":
        report = ['string in list:', '  comparing against best matching line']
        valid_scenario = "list"
    if isinstance(left, (str, unicode)) and isinstance(right, (str, unicode)) and op == "in":
        report = ['string in string:', '  comparing against best item in list']
        valid_scenario = "string"

    if valid_scenario:
        closest_line, ratios = closest_line_match(left, right)
        left_repr = string_repr(left)
        right_repr = string_repr(right)

        # single word will trigger closest matches
        if len(left.split()) == 1:
            matches = get_close_matches(left, right)
            if not matches:
                report = report + [
                    'Completely unable to find an approximate match',
                    'AssertionError: %s in %s' % (left_repr, right_repr)]
            else:
                report = report + [
                    'Closest matches: %s' % str(list(set(matches)))] + [
                    line.strip('\n') for line in
                    ndiff([left], [closest_line])]

        else: # we have a multi-word string
            #best_ndiff([left], [best_right_comparison(left, closest_line)])]
            report = report + ['Closest match: %s'] + [
                line.strip('\n') for line in
                ndiff([left], [best_right_comparison(left, closest_line)])]

        if config.option.verbose > 1:
            if valid_scenario == "string":
                report = report + ["Full text:"] + right.split('\n')
            else:
                report = report + ["Full list:"] + [str(right)]
        if config.option.verbose > 2:
            report = report + ["Line Ratios:"] + [str(i[1]) for i in ratios]
        return report
