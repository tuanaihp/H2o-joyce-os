"""Trich hang loat: python tools/batch_extract.py <dir> <pattern> <out.txt> [max]"""
import sys, io, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_text as E

def main():
    d, pat, out = sys.argv[1], sys.argv[2], sys.argv[3]
    mx = int(sys.argv[4]) if len(sys.argv) > 4 else 12000
    files = sorted(glob.glob(os.path.join(d, pat), recursive=True))
    files = [f for f in files if not os.path.basename(f).startswith("~$")]
    with io.open(out, "w", encoding="utf-8") as w:
        for f in files:
            rel = os.path.relpath(f, d)
            w.write("\n\n" + "="*70 + "\nFILE: " + rel + "\n" + "="*70 + "\n")
            try:
                t = E.extract(f)[:mx]
                w.write(t if t.strip() else "[EMPTY]")
            except Exception as e:
                w.write("[ERR %s]" % e)
    os.write(2, ("%d files -> %s\n" % (len(files), out)).encode())

if __name__ == "__main__":
    main()
