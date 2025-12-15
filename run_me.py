"""
ONE-FILE RESUME SCREENER
Just run this file!
"""

import os
import json
import re
import pdfplumber
from docx import Document
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime

print("\n" + "="*60)
print("🚀 RESUME SCREENING SYSTEM - SIMPLE VERSION")
print("="*60)
print("Based on the research paper: 'Application of LLM Agents in Recruitment'")
print()

class ResumeScreener:
    """Simple resume screening system"""
    
    def __init__(self):
        self.categories = ["personal", "experience", "education", "skills", "other"]
    
    def parse_resume(self, file_path):
        """Read resume file"""
        try:
            if file_path.endswith('.pdf'):
                with pdfplumber.open(file_path) as pdf:
                    text = "\n".join([page.extract_text() for page in pdf.pages])
            elif file_path.endswith('.docx'):
                doc = Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])
            elif file_path.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            else:
                return None
            return text.strip()
        except:
            return None
    
    def grade_resume(self, text):
        """Simple grading algorithm"""
        if not text:
            return 0
        
        score = 50
        text_lower = text.lower()
        
        # Check for experience
        if "experience" in text_lower:
            score += 20
        if "year" in text_lower:
            score += 10
        
        # Check for education
        if "education" in text_lower:
            score += 10
        if "degree" in text_lower or "bachelor" in text_lower or "master" in text_lower:
            score += 10
        
        # Check for skills
        skills = ["python", "java", "javascript", "sql", "aws", "docker"]
        for skill in skills:
            if skill in text_lower:
                score += 5
        
        return min(100, score)
    
    def process_folder(self, folder_path):
        """Process all resumes in folder"""
        results = []
        
        if not os.path.exists(folder_path):
            print(f"❌ Folder not found: {folder_path}")
            print("📁 Creating sample resumes...")
            self.create_sample_resumes()
            folder_path = "./resumes"
        
        print(f"\n📂 Processing resumes from: {folder_path}")
        
        for filename in os.listdir(folder_path):
            if filename.endswith(('.pdf', '.docx', '.txt')):
                file_path = os.path.join(folder_path, filename)
                print(f"  📄 Reading: {filename}")
                
                text = self.parse_resume(file_path)
                if text:
                    grade = self.grade_resume(text)
                    
                    # Create summary (first 100 words)
                    words = text.split()[:100]
                    summary = " ".join(words) + ("..." if len(text.split()) > 100 else "")
                    
                    results.append({
                        "filename": filename,
                        "grade": grade,
                        "summary": summary,
                        "word_count": len(text.split())
                    })
        
        return results
    
    def create_sample_resumes(self):
        """Create sample resumes for testing"""
        os.makedirs("./resumes", exist_ok=True)
        
        samples = [
            ("john_doe.txt", """
            John Doe - Senior Software Engineer
            
            EXPERIENCE:
            - Senior Software Engineer at Google (2020-2024)
              * Developed backend services in Python and Java
              * Led team of 5 engineers
              * Improved system performance by 40%
            
            - Software Developer at Microsoft (2016-2020)
              * Created web applications with React and Node.js
              * Worked on Azure cloud services
            
            EDUCATION:
            - Master of Science in Computer Science, Stanford University
            - Bachelor of Engineering, MIT
            
            SKILLS:
            Python, Java, JavaScript, AWS, Docker, Kubernetes, SQL
            
            CERTIFICATIONS:
            AWS Solutions Architect, Google Cloud Professional
            """),
            
            ("jane_smith.txt", """
            Jane Smith - Data Scientist
            
            PROFILE:
            Data Scientist with 5 years experience in machine learning.
            
            EXPERIENCE:
            - Data Scientist at Facebook (2019-2024)
              * Built ML models for recommendation systems
              * Used TensorFlow and PyTorch
              * Published research papers
            
            - Data Analyst at Amazon (2017-2019)
              * Analyzed customer data
              * Created dashboards and reports
            
            EDUCATION:
            - PhD in Data Science, Harvard University
            - MS in Statistics, University of Chicago
            
            SKILLS:
            Python, R, TensorFlow, PyTorch, SQL, Machine Learning
            
            CERTIFICATIONS:
            TensorFlow Developer Certificate
            """),
            
            ("bob_johnson.txt", """
            Bob Johnson - DevOps Engineer
            
            SUMMARY:
            DevOps Engineer with 4 years experience in cloud infrastructure.
            
            EXPERIENCE:
            - DevOps Engineer at Netflix (2020-2024)
              * Managed Kubernetes clusters
              * Automated deployment pipelines
              * Monitored system performance
            
            - System Administrator at IBM (2018-2020)
              * Managed servers and networks
              * Implemented security protocols
            
            EDUCATION:
            - Bachelor of Computer Science, University of Texas
            
            SKILLS:
            AWS, Docker, Kubernetes, Jenkins, Terraform, Linux, Python
            
            CERTIFICATIONS:
            AWS DevOps Engineer, Kubernetes Administrator
            """)
        ]
        
        for filename, content in samples:
            with open(f"./resumes/{filename}", "w") as f:
                f.write(content.strip())
        
        print("✅ Created 3 sample resumes in './resumes/' folder")
    
    def run_screening(self):
        """Run the complete screening process"""
        print("\n" + "="*60)
        print("📊 SCREENING PROCESS STARTING...")
        print("="*60)
        
        # Process resumes
        results = self.process_folder("./resumes")
        
        if not results:
            print("❌ No resumes found or processed")
            return
        
        # Sort by grade
        results.sort(key=lambda x: x["grade"], reverse=True)
        
        # Display results
        print(f"\n✅ Processed {len(results)} resumes")
        print("\n🏆 TOP CANDIDATES:")
        print("-" * 60)
        
        for i, result in enumerate(results[:10], 1):
            print(f"\n{i}. {result['filename']} - {result['grade']}/100")
            print(f"   Summary: {result['summary'][:150]}...")
        
        # Save to CSV
        df = pd.DataFrame(results)
        csv_file = f"./results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(csv_file, index=False)
        
        print(f"\n📄 Results saved to: {csv_file}")
        
        # Print statistics
        avg_grade = df["grade"].mean()
        max_grade = df["grade"].max()
        
        print(f"\n📊 STATISTICS:")
        print(f"   Average grade: {avg_grade:.1f}/100")
        print(f"   Highest grade: {max_grade}/100")
        print(f"   Total resumes: {len(results)}")
        
        # Show top candidate
        if len(results) > 0:
            top = results[0]
            print(f"\n🎯 RECOMMENDED CANDIDATE:")
            print(f"   {top['filename']} - {top['grade']}/100")
            print(f"   Key skills detected: {self.extract_skills(top['summary'])}")
        
        print("\n" + "="*60)
        print("✅ SCREENING COMPLETED SUCCESSFULLY!")
        print("="*60)
    
    def extract_skills(self, text):
        """Extract skills from text"""
        skills = []
        skill_list = ["python", "java", "javascript", "aws", "docker", 
                     "kubernetes", "sql", "react", "node", "tensorflow"]
        
        text_lower = text.lower()
        for skill in skill_list:
            if skill in text_lower:
                skills.append(skill)
        
        return ", ".join(skills) if skills else "General skills"

# Run the screener
if __name__ == "__main__":
    screener = ResumeScreener()
    screener.run_screening()
    
    # Optional: Wait for user input
    input("\nPress Enter to exit...")