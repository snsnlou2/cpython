
import textwrap
from io import StringIO
from test.test_json import PyTest, CTest

class TestIndent():

    def test_indent(self):
        h = [['blorpie'], ['whoops'], [], 'd-shtaeou', 'd-nthiouh', 'i-vhbjkhnth', {'nifty': 87}, {'field': 'yes', 'morefield': False}]
        expect = textwrap.dedent('        [\n        \t[\n        \t\t"blorpie"\n        \t],\n        \t[\n        \t\t"whoops"\n        \t],\n        \t[],\n        \t"d-shtaeou",\n        \t"d-nthiouh",\n        \t"i-vhbjkhnth",\n        \t{\n        \t\t"nifty": 87\n        \t},\n        \t{\n        \t\t"field": "yes",\n        \t\t"morefield": false\n        \t}\n        ]')
        d1 = self.dumps(h)
        d2 = self.dumps(h, indent=2, sort_keys=True, separators=(',', ': '))
        d3 = self.dumps(h, indent='\t', sort_keys=True, separators=(',', ': '))
        d4 = self.dumps(h, indent=2, sort_keys=True)
        d5 = self.dumps(h, indent='\t', sort_keys=True)
        h1 = self.loads(d1)
        h2 = self.loads(d2)
        h3 = self.loads(d3)
        self.assertEqual(h1, h)
        self.assertEqual(h2, h)
        self.assertEqual(h3, h)
        self.assertEqual(d2, expect.expandtabs(2))
        self.assertEqual(d3, expect)
        self.assertEqual(d4, d2)
        self.assertEqual(d5, d3)

    def test_indent0(self):
        h = {3: 1}

        def check(indent, expected):
            d1 = self.dumps(h, indent=indent)
            self.assertEqual(d1, expected)
            sio = StringIO()
            self.json.dump(h, sio, indent=indent)
            self.assertEqual(sio.getvalue(), expected)
        check(0, '{\n"3": 1\n}')
        check(None, '{"3": 1}')

class TestPyIndent(TestIndent, PyTest):
    pass

class TestCIndent(TestIndent, CTest):
    pass
