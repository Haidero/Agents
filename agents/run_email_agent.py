"""
Simple command-line interface for Email Agent
Run: python run_email_agent.py
"""

import argparse
import sys
from email_agent import EmailAgent
import json

def main():
    parser = argparse.ArgumentParser(description="Email Resume Screening Agent")
    parser.add_argument("--config", default="email_config.json", help="Configuration file")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=5, help="Check interval in minutes")
    parser.add_argument("--no-response", action="store_true", help="Don't send responses")
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("📧 EMAIL RESUME SCREENING AGENT")
    print("="*60)
    
    try:
        # Initialize agent
        agent = EmailAgent(args.config)
        
        # Check configuration
        with open(args.config, 'r') as f:
            config = json.load(f)
        
        print(f"\n✅ Configuration loaded from {args.config}")
        print(f"   Email: {config['email']['username']}")
        print(f"   Position: {config['screening']['target_position']}")
        print(f"   Min Score: {config['screening']['minimum_score']}")
        
        if args.once:
            print("\n🔍 Running single check...")
            summary = agent.run_once(send_responses=not args.no_response)
            print(f"\n📊 Summary: {summary}")
            
        elif args.continuous:
            print(f"\n🔄 Starting continuous monitoring (interval: {args.interval} minutes)")
            print("Press Ctrl+C to stop\n")
            agent.run_continuously(args.interval)
            
        else:
            # Interactive mode
            while True:
                print("\nOptions:")
                print("  1. Check for new resumes once")
                print("  2. Start continuous monitoring")
                print("  3. View configuration")
                print("  4. Exit")
                
                choice = input("\nSelect option (1-4): ").strip()
                
                if choice == '1':
                    print("\n🔍 Checking for new resumes...")
                    summary = agent.run_once(send_responses=not args.no_response)
                    print(f"\n📊 Results: {summary}")
                    
                elif choice == '2':
                    interval = input("Check interval (minutes) [5]: ").strip()
                    interval = int(interval) if interval else 5
                    print(f"\n🔄 Starting continuous monitoring (every {interval} minutes)")
                    print("Press Ctrl+C in terminal to stop\n")
                    agent.run_continuously(interval)
                    break
                    
                elif choice == '3':
                    print("\n📋 Configuration:")
                    print(json.dumps(config, indent=2))
                    
                elif choice == '4':
                    print("\n👋 Goodbye!")
                    break
                    
                else:
                    print("Invalid choice")
    
    except KeyboardInterrupt:
        print("\n\n⏹️ Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()