#!/usr/bin/env python3
"""
research_with_exa.py — deep asset research for the ItoMarkets brand film using EXA.
Searches for free/public domain footage, images, and sources for each beat.
"""
import json, os, urllib.request, urllib.parse

BUILD = os.path.dirname(os.path.abspath(__file__))

def load_env():
    env = {}
    with open(os.path.join(BUILD, ".env.hermes")) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k] = v
    return env


def exa_search(query, num_results=10, search_type="keyword"):
    env = load_env()
    key = env.get("EXA_API_KEY")
    if not key:
        raise RuntimeError("EXA_API_KEY not found")
    data = json.dumps({
        "query": query,
        "numResults": num_results,
        "type": search_type,
        "useAutoprompt": True,
    }).encode()
    req = urllib.request.Request(
        "https://api.exa.ai/search",
        data=data,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    queries = [
        "free public domain archival footage Toronto Stock Exchange 1990 TIPs ETF launch",
        "free stock footage Wall Street New York financial district 4K CC0 creative commons",
        "free public domain stock footage marble gold black luxury background loop",
        "free public domain footage stock exchange trading floor 1980s 1990s",
        "free stock footage prediction market interface screen recording creative commons",
        "public domain image Al-Khwarizmi mathematician manuscript",
        "public domain image Kiyoshi Ito mathematician stochastic calculus",
        "public domain image Bernhard Riemann mathematician",
        "public domain image Leonhard Euler portrait",
        "Farnese Atlas statue public domain image high resolution",
    ]

    results = {}
    for q in queries:
        print(f"researching: {q[:60]}...")
        try:
            res = exa_search(q, num_results=8)
            results[q] = res.get("results", [])
        except Exception as e:
            print(f"  FAIL: {e}")
            results[q] = []

    out_path = os.path.join(BUILD, "research_exa_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
