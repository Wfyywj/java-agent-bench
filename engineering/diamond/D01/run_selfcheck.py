#!/usr/bin/env python3
import argparse,pathlib,json,run
p=argparse.ArgumentParser();p.add_argument('--candidate');a=p.parse_args()
if a.candidate:
 root=pathlib.Path(a.candidate).resolve();src=root/'src' if (root/'src').is_dir() else root
 r=run.evaluate(src);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['pass'] else 1)
raise SystemExit(run.main())
