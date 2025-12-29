import os
import sys
import argparse
import time

def run_scan(args):
    """Run standard directory scan"""
    if args.llm:
        print("[LLM AGENT] Using LLM Agents...")
        from core.llm_screener import LLMScreener
        screener = LLMScreener(use_gpu=args.gpu)
    else:
        print("[RULE-BASED] Using Rule-Based Screener...")
        from core.screener import RealisticResumeScreener
        screener = RealisticResumeScreener()
    
    # Handle sample creation if folder empty/not found
    if not os.path.exists("./resumes") or not os.listdir("./resumes"):
        print("Folder empty or not found. Creating samples...")
        if hasattr(screener, 'create_realistic_sample_resumes'):
             screener.create_realistic_sample_resumes()
        else:
             # LLMScreener doesn't have this method yet, fallback
             from core.screener import RealisticResumeScreener
             rs = RealisticResumeScreener()
             rs.create_realistic_sample_resumes()
             
    if args.llm:
        results = screener.batch_process(args.dir, target_position=args.position)
        # TODO: Implement Decision Making display for LLMScreener
        if results:
             decision = screener.make_hiring_decision(results)
             print("\n[CEO AGENT DECISION]:")
             print(f"Decision: {decision.get('reasoning')}")
    else:
        screener.run_screening(target_position=args.position)

def run_web_app(args):
    """Launch Streamlit Web UI"""
    print("[WEB] Launching Web UI...")
    os.system("streamlit run web_app.py")

def run_email_agent(args):
    """Run Email Agent"""
    from agents.email_agent.email_agent import EmailAgent
    
    print("[EMAIL] Starting Email Agent...")
    print(f"   Mode: {'Continuous' if args.continuous else 'Run Once'}")
    
    if args.llm:
         print(f"[LLM] Using LLM Agents for Email Screening (Position: {args.position})...")
         from core.llm_screener import LLMScreener
         screener = LLMScreener(use_gpu=args.gpu)
         agent = EmailAgent(screener=screener, target_position=args.position)
    else:
         print(f"[RULE-BASED] Starting Email Screening (Position: {args.position})...")
         agent = EmailAgent(target_position=args.position)
    
    if args.continuous:
        agent.run_continuously(interval_minutes=args.interval)
    else:
        agent.run_once(days_back=args.days, ignore_processed=args.force_rescan)

def main():
    parser = argparse.ArgumentParser(description="AI Resume Screening System")
    subparsers = parser.add_subparsers(dest="mode", help="Mode of operation")
    
    # Scan Mode
    scan_parser = subparsers.add_parser("scan", help="Scan a directory of resumes")
    scan_parser.add_argument("--dir", default="./resumes", help="Directory to scan")
    scan_parser.add_argument("--position", default="software_engineer", help="Target position")
    scan_parser.add_argument("--llm", action="store_true", help="Use LLM Agents")
    scan_parser.add_argument("--gpu", action="store_true", help="Force GPU usage for local models")
    
    # Web Mode
    web_parser = subparsers.add_parser("web", help="Launch Web Interface")
    
    # Email Mode
    email_parser = subparsers.add_parser("email", help="Run Email Agent")
    email_parser.add_argument("--continuous", action="store_true", help="Run continuously")
    email_parser.add_argument("--interval", type=int, default=5, help="Interval in minutes")
    email_parser.add_argument("--days", type=int, default=7, help="Days to look back for emails")
    email_parser.add_argument("--position", default="software_engineer", help="Target position")
    email_parser.add_argument("--force-rescan", action="store_true", help="Process already processed emails")
    email_parser.add_argument("--llm", action="store_true", help="Use LLM Agents")
    email_parser.add_argument("--gpu", action="store_true", help="Force GPU usage for local models")
    
    args = parser.parse_args()
    
    if args.mode == "scan":
        run_scan(args)
    elif args.mode == "web":
        run_web_app(args)
    elif args.mode == "email":
        run_email_agent(args)
    else:
        # Default behavior if no arguments
        print("No mode specified. Using default: scan")
        # You could verify if user wants web or scan by default, but let's default to scan for CLI users
        # For better UX, let's show help
        parser.print_help()
        
        # Or just run the scan as a fallback like the old main.py
        print("\n--- Defaulting to Scan Mode ---")
        class Args:
             position = "software_engineer"
        run_scan(Args())

if __name__ == "__main__":
    main()