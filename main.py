import os
import sys
import json
from pathlib import Path
import argparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import after path is set
from simple_resume_screener import SimpleResumeScreener

def main():
    """Main function - simplified version"""
    
    parser = argparse.ArgumentParser(description="Resume Screening System")
    parser.add_argument("--resumes", type=str, help="Path to resume file or directory")
    parser.add_argument("--top-n", type=int, default=5, help="Number of top candidates")
    parser.add_argument("--criteria", type=str, help="JSON criteria for selection")
    
    args = parser.parse_args()
    
    # Parse criteria if provided
    criteria = {}
    if args.criteria:
        try:
            criteria = json.loads(args.criteria)
        except:
            print("Warning: Invalid criteria JSON, using defaults")
    
    print("\n" + "="*60)
    print("RESUME SCREENING SYSTEM")
    print("="*60)
    
    # Use the SimpleResumeScreener (works without LLMs)
    screener = SimpleResumeScreener()
    
    # Determine input folder
    if args.resumes:
        if os.path.isdir(args.resumes):
            input_folder = args.resumes
        elif os.path.isfile(args.resumes):
            # Create temp folder for single file
            import tempfile
            temp_dir = tempfile.mkdtemp()
            import shutil
            shutil.copy(args.resumes, temp_dir)
            input_folder = temp_dir
        else:
            print(f"Error: {args.resumes} not found")
            return
    else:
        input_folder = "./resumes"  # Default folder
    
    # Run the screener
    report = screener.run_pipeline(input_folder=input_folder, criteria=criteria)
    
    print("\n✅ Process completed!")

if __name__ == "__main__":
    main()