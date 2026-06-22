#!/usr/bin/env python3
"""
research_with_xai.py — use xAI Grok deep reasoning to find niche sources for the ItoMarkets film.
"""
import json, os, urllib.request

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


def grok_ask(prompt, model="grok-3-beta"):
    env = load_env()
    key = env.get("GROK_API_KEY")
    if not key:
        raise RuntimeError("GROK_API_KEY not found")
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
    }).encode()
    req = urllib.request.Request(
        "https://api.x.ai/v1/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.loads(r.read().decode())
    return res["choices"][0]["message"]["content"]


def main():
    prompts = [
        "Find the best free/public-domain archival footage sources for the 1990 Toronto Stock Exchange launch of the first ETF (TIPs). Include specific archive collections, NFB clips, CBC archives, Internet Archive items, and any YouTube channels with archival footage. Give direct URLs where possible.",
        "Find free stock footage sources for an institutional finance brand film: Wall Street, New York Stock Exchange, trading floors, skyscrapers, marble/gold luxury backgrounds. Focus on CC0, public domain, or attribution-only sites. Give direct download links or search URLs.",
        "Find niche social media, forum, and creator sources for prediction market content and ETF imagery. Include Twitter/X accounts, Reddit communities, Discord servers, YouTube channels, and niche blogs that discuss prediction markets or ItoMarkets-adjacent themes. Give handles and URLs.",
        "Find free/public domain images and footage of historical mathematicians: Al-Khwarizmi, Euler, Riemann, Ito Kiyoshi, Jim Simons. Include museums, university archives, and specific Wikimedia Commons file URLs. Also suggest any free short video clips of Jim Simons interviews or lectures.",
    ]

    results = {}
    for i, p in enumerate(prompts):
        print(f"grok query {i+1}/{len(prompts)}...")
        try:
            results[p] = grok_ask(p)
        except Exception as e:
            print(f"  FAIL: {e}")
            results[p] = str(e)

    out_path = os.path.join(BUILD, "research_xai_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
