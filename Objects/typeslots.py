
import sys, re

def generate_typeslots(out=sys.stdout):
    out.write('/* Generated by typeslots.py */\n')
    res = {}
    for line in sys.stdin:
        m = re.match('#define Py_([a-z_]+) ([0-9]+)', line)
        if (not m):
            continue
        member = m.group(1)
        if member.startswith('tp_'):
            member = ('ht_type.' + member)
        elif member.startswith('am_'):
            member = ('as_async.' + member)
        elif member.startswith('nb_'):
            member = ('as_number.' + member)
        elif member.startswith('mp_'):
            member = ('as_mapping.' + member)
        elif member.startswith('sq_'):
            member = ('as_sequence.' + member)
        elif member.startswith('bf_'):
            member = ('as_buffer.' + member)
        res[int(m.group(2))] = member
    M = (max(res.keys()) + 1)
    for i in range(1, M):
        if (i in res):
            out.write(('offsetof(PyHeapTypeObject, %s),\n' % res[i]))
        else:
            out.write('0,\n')

def main():
    if (len(sys.argv) == 2):
        with open(sys.argv[1], 'w') as f:
            generate_typeslots(f)
    else:
        generate_typeslots()
if (__name__ == '__main__'):
    main()
