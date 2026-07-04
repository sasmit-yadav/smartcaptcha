"""
Orchestrate running all bot types to generate synthetic bot telemetry data.
Usage:
    python run_all_bots.py --bot instant --runs 10
    python run_all_bots.py --all --runs 20
"""
import argparse
import sys
import os
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bots.instant_bot import InstantBot
from bots.linear_bot import LinearBot
from bots.timed_bot import TimedBot
from bots.smart_bot import SmartBot
from bots.aggressive_bot import AggressiveBot
from bots.test_human_like_bot import StealthBot
from bots.adversarial_bot import AdversarialBot
from bots.multi_page_bot import MultiPageBot


BOT_CLASSES = {
    'instant': InstantBot,
    'linear': LinearBot,
    'timed': TimedBot,
    'smart': SmartBot,
    'aggressive': AggressiveBot,
    'stealth': StealthBot,
    'adversarial': AdversarialBot,
    'multi_page': MultiPageBot,
}


def run_bot(bot_type, runs, headless=True, target='demo'):
    """Run a specific bot type multiple times."""
    bot_class = BOT_CLASSES.get(bot_type)
    if not bot_class:
        print(f"Unknown bot type: {bot_type}")
        return []
    
    session_ids = []
    print(f"\n{'='*60}")
    print(f"Running {bot_type.upper()} BOT - {runs} iterations on {target.upper()} site")
    print(f"{'='*60}")
    
    for i in range(runs):
        print(f"\n--- Run {i+1}/{runs} ---")
        try:
            bot = bot_class(headless=headless, target=target)
            session_id = bot.run()
            if session_id:
                session_ids.append(session_id)
                print(f"✓ Session ID: {session_id[:8]}...")
            else:
                print("✗ No session ID captured")
            
            # Brief pause between runs
            time.sleep(1)
            
        except Exception as e:
            print(f"✗ Run {i+1} failed: {e}")
    
    print(f"\n{bot_type.upper()} BOT completed: {len(session_ids)}/{runs} successful")
    return session_ids


def run_all_bots(runs_per_bot, headless=True, target='demo'):
    """Run all bot types."""
    all_session_ids = {}
    
    for bot_type in BOT_CLASSES.keys():
        session_ids = run_bot(bot_type, runs_per_bot, headless, target)
        all_session_ids[bot_type] = session_ids
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    total_sessions = 0
    for bot_type, session_ids in all_session_ids.items():
        count = len(session_ids)
        total_sessions += count
        print(f"{bot_type:10s}: {count:3d} sessions")
    
    print(f"\nTotal bot sessions generated: {total_sessions}")
    
    # Save session IDs to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"bot_sessions_{timestamp}.txt"
    with open(output_file, 'w') as f:
        f.write(f"Bot Sessions Generated - {timestamp}\n")
        f.write(f"Total: {total_sessions} sessions\n\n")
        for bot_type, session_ids in all_session_ids.items():
            f.write(f"{bot_type.upper()}:\n")
            for sid in session_ids:
                f.write(f"  {sid}\n")
            f.write("\n")
    
    print(f"Session IDs saved to: {output_file}")
    
    return all_session_ids


def main():
    parser = argparse.ArgumentParser(description="Run synthetic bots to generate telemetry data")
    parser.add_argument('--bot', choices=[*BOT_CLASSES.keys(), 'all'], 
                       default='all', help='Bot type to run (default: all)')
    parser.add_argument('--runs', type=int, default=10, 
                       help='Number of runs per bot (default: 10)')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run browsers in headless mode (default: True)')
    parser.add_argument('--no-headless', dest='headless', action='store_false',
                       help='Run browsers with visible window')
    parser.add_argument('--target', choices=['demo', 'testing'], default='demo',
                       help='Target site: demo-site for training data, testing-website for evaluation (default: demo)')
    
    args = parser.parse_args()
    
    print(f"Bot Runner - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Headless mode: {args.headless}")
    print(f"Target site: {args.target.upper()}")
    print(f"Runs per bot: {args.runs}")
    
    if args.bot == 'all':
        run_all_bots(args.runs, args.headless, args.target)
    else:
        run_bot(args.bot, args.runs, args.headless, args.target)


if __name__ == "__main__":
    main()
