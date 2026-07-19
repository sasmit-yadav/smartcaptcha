"""
Orchestrate the tool-diversity bots (strategy doc step 5).

Usage:
    python -m ml.bots.real_bots.run_all --tool selenium --runs 15
    python -m ml.bots.real_bots.run_all --tool all --runs 15
"""
import argparse
import time

try:
    from . import playwright_bot, raw_api_bot, selenium_plain_bot, undetected_bot
except ImportError:
    import playwright_bot
    import raw_api_bot
    import selenium_plain_bot
    import undetected_bot

TOOL_RUNNERS = {
    "selenium": lambda headless: selenium_plain_bot.run(headless=headless),
    "playwright": lambda headless: playwright_bot.run(headless=headless),
    "undetected": lambda headless: undetected_bot.run(headless=headless),
    "raw_api": lambda headless: raw_api_bot.run(),
}


def run_tool(tool, runs, headless=True):
    runner = TOOL_RUNNERS[tool]
    ok = 0
    for i in range(runs):
        print(f"\n--- {tool} run {i + 1}/{runs} ---")
        try:
            session_id = runner(headless)
            if session_id:
                ok += 1
        except Exception as e:
            print(f"[run_all] {tool} run {i + 1} failed: {e}")
        time.sleep(1)
    print(f"\n{tool}: {ok}/{runs} sessions labeled")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Run tool-diversity bots")
    parser.add_argument("--tool", choices=[*TOOL_RUNNERS.keys(), "all"], default="all")
    parser.add_argument("--runs", type=int, default=15)
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    args = parser.parse_args()

    tools = list(TOOL_RUNNERS.keys()) if args.tool == "all" else [args.tool]
    totals = {}
    for tool in tools:
        totals[tool] = run_tool(tool, args.runs, args.headless)

    print("\n=== SUMMARY ===")
    for tool, count in totals.items():
        print(f"{tool:12s}: {count}/{args.runs}")


if __name__ == "__main__":
    main()
