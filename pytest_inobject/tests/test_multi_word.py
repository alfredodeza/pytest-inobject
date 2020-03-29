from pytest_inobject.plugin import closest_line_match, pytest_assertrepr_compare, best_right_comparison

text = """
One of the main features of pytest is the use of plain assert statements and
the detailed introspection of expressions upon assertion failures. This is
provided by "assertion rewriting" which modifies the parsed AST before it gets
compiled to bytecode. This is done via a PEP 302 import hook which gets
installed early on when pytest starts up and will perform this rewriting when
modules get imported. However since we do not want to test different bytecode
then you will run in production this hook only rewrites test modules themselves
as well as any modules which are part of plugins. Any other imported module
will not be rewritten and normal assertion behaviour will happen.
"""


class TestClosesLineMatch(object):

    def test_finds_best_line(self):
        left = "compiled to bitcode. This is done"
        match, _ = closest_line_match(left, text)
        assert match.startswith('compiled to bytecode. This')

    def test_left_is_complete_garbage(self):
        left = "garbage1111)"
        match = closest_line_match(left, text)
        assert match.startswith('\nOne of the')
        assert match.endswith('will happen.\n')

    def test_single_word_matches_best_line(self):
        left = 'rewriting"'
        match, ratio = closest_line_match(left, text)
        expected = 'provided by "assertion rewriting" which modifies the parsed AST before it gets'
        assert match == expected

    def test_whitespace_does_not_affect_ratio(self):
        text = '\n'.join([
            'this is a line with whitespace                    ',
            'this is a line with whitespace but lots of garbage',
        ])

        left = "this is a line with whitespace"
        match, _ = closest_line_match(left, text)
        expected = "this is a line with whitespace                    "
        assert match == expected


class TestBestRightComparison(object):

    def test_head_trimming(self):
        left = "long line here"
        line = " this is some very long line here"
        result = best_right_comparison(left, line)
        assert result == "some very long line here"

    def test_tail_trimming(self):
        left = "this is some"
        line = "this is some very long line here"
        result = best_right_comparison(left, line)
        assert result == "this is some very long"

class TestInList(object):

    def test_in_list(self):
        left = "some mul"
        right = ["some multi", "inf word", "here in", "ptjher", "inflex"]
        assert left in right
