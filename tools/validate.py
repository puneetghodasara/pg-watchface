import sys, xmlschema
schema = xmlschema.XMLSchema11(sys.argv[1])
errs = list(schema.iter_errors(sys.argv[2]))
print('schema: VALID' if not errs else 'schema: INVALID (%d)' % len(errs))
for e in errs[:8]: print(' -', e.path, '|', (e.reason or '')[:200])
sys.exit(1 if errs else 0)
