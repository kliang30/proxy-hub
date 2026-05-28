#!/usr/bin/env python3
"""Fetch and merge proxy entries from subscription sources."""
import sys, yaml, base64, re, json, os

urls_file = sys.argv[1] if len(sys.argv) > 1 else "sub-urls.txt"
out_file = sys.argv[2] if len(sys.argv) > 2 else "raw-proxies.yaml"

with open(urls_file) as f:
    urls = [l.strip() for l in f if l.strip() and not l.startswith('#')]

import urllib.request, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

total, success = 0, 0
all_entries = []

for url in urls:
    total += 1
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'clash.meta/1.19'})
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        content = resp.read().decode('utf-8', errors='ignore')
        entries = []

        # Clash YAML
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and 'proxies' in data:
                for p in data['proxies']:
                    if isinstance(p, dict) and 'server' in p:
                        entries.append(p)
        except: pass

        # Base64
        if not entries:
            try:
                d = base64.b64decode(content.strip()).decode('utf-8', errors='ignore')
                for line in d.split('\n'):
                    line = line.strip()
                    if line and any(line.startswith(p+'://') for p in ['vmess','vless','trojan','ss','ssr','hysteria','tuic','juicity']):
                        entries.append({'url': line, 'type': line.split('://')[0]})
            except: pass

        # Regex
        if not entries:
            for m in re.finditer(r'(vmess|vless|trojan|ss|ssr|hysteria2?|tuic|juicity)://\S+', content):
                entries.append({'url': m.group(0), 'type': m.group(0).split('://')[0]})

        all_entries.extend(entries)
        success += 1
        print(f"  OK [{len(entries)}]: {url[:55]}...", file=sys.stderr)
    except Exception as e:
        print(f"  FAIL: {url[:55]}... ({e})", file=sys.stderr)

# Deduplicate
seen = set()
unique = []
for e in all_entries:
    key = str(e.get('server','')) + ':' + str(e.get('port',''))
    if key == ':': key = e.get('url', str(e))
    if key and key not in seen:
        seen.add(key)
        unique.append(e)

# Write output
with open(out_file, 'w') as f:
    f.write(f"# ProxyHub Full Proxy Entries\n")
    f.write(f"# Sources: {success}/{total}\n")
    f.write(f"# Count: {len(unique)}\n\n")
    for e in unique:
        f.write(json.dumps(e, ensure_ascii=False) + '\n')

print(f"\nDone: {success}/{total} sources, {len(unique)} unique entries", file=sys.stderr)
print(len(unique))  # stdout for count
