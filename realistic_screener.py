"""
REALISTIC Resume Screening System
With more realistic scoring (70-95 range instead of all 100s)
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
print("📊 REALISTIC RESUME SCREENING SYSTEM")
print("="*60)
print("Based on the research paper: 'Application of LLM Agents in Recruitment'")
print()

class RealisticResumeScreener:
    """Realistic resume screening with better scoring"""
    
    def __init__(self):
        # More realistic skill weights (max 40 points total)
        self.skill_weights = {
            "python": 8, "java": 8, "javascript": 6, "aws": 10, "docker": 8,
            "kubernetes": 10, "sql": 6, "react": 5, "node.js": 5, "tensorflow": 8,
            "pytorch": 8, "machine learning": 12, "ai": 12, "cloud": 8,
            "devops": 10, "azure": 6, "gcp": 6, "linux": 5, "git": 4,
            "spring": 6, "django": 5, "flask": 4, "fastapi": 4, "mongodb": 4,
            "postgresql": 4, "mysql": 4, "redis": 3, "kafka": 4, "spark": 5
        }
        
        # Position-specific requirements (like in the paper)
        self.position_requirements = {
            "software_engineer": ["python", "java", "javascript", "aws", "docker", "sql"],
            "data_scientist": ["python", "machine learning", "tensorflow", "pytorch", "sql"],
            "devops": ["aws", "docker", "kubernetes", "linux", "git", "cloud"],
            "full_stack": ["python", "javascript", "react", "node.js", "aws", "docker"]
        }
    
    def parse_resume(self, file_path):
        """Read resume file"""
        try:
            if file_path.endswith('.pdf'):
                with pdfplumber.open(file_path) as pdf:
                    text = "\n".join([page.extract_text() or "" for page in pdf.pages])
            elif file_path.endswith('.docx'):
                doc = Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])
            elif file_path.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            else:
                return None
            return text.strip()
        except Exception as e:
            print(f"    Error reading {file_path}: {str(e)}")
            return None
    
    def grade_resume(self, text, target_position="software_engineer"):
        """Realistic grading algorithm (based on paper methodology)"""
        if not text:
            return 0, []
        
        text_lower = text.lower()
        score = 40  # Base score (lower starting point)
        
        # 1. Experience Section (max 25 points)
        experience_score = 0
        
        # Check for experience section
        if "experience" in text_lower:
            experience_score += 10
            
            # Count years of experience (more realistic)
            year_matches = re.findall(r'(\d+)\s*years?\s*(?:of)?\s*experience', text_lower)
            if year_matches:
                years = sum(int(match) for match in year_matches[:3])  # Take first 3 mentions
                if years >= 10:
                    experience_score += 15
                elif years >= 5:
                    experience_score += 12
                elif years >= 3:
                    experience_score += 8
                elif years >= 1:
                    experience_score += 5
            else:
                # Estimate from dates
                date_patterns = re.findall(r'(?:19|20)\d{2}[-\s]\s*(?:19|20)\d{2}', text)
                if date_patterns:
                    experience_score += 7
        
        # Check for senior/lead roles
        if re.search(r'\b(senior|lead|principal|manager|director)\b', text_lower):
            experience_score += 8
        
        score += min(experience_score, 25)  # Cap experience at 25 points
        
        # 2. Education (max 15 points)
        education_score = 0
        
        if "phd" in text_lower or "doctorate" in text_lower:
            education_score += 15
        elif "master" in text_lower or "ms" in text_lower or "m.sc" in text_lower:
            education_score += 10
        elif "bachelor" in text_lower or "bs" in text_lower or "b.tech" in text_lower:
            education_score += 7
        elif "education" in text_lower:
            education_score += 5
        
        # Check for top universities
        top_universities = ["stanford", "mit", "harvard", "caltech", "princeton", 
                          "cambridge", "oxford", "carnegie", "berkeley"]
        for uni in top_universities:
            if uni in text_lower:
                education_score += 3
        
        score += min(education_score, 15)  # Cap education at 15 points
        
        # 3. Skills with weights (max 30 points)
        skills_found = []
        skills_score = 0
        
        # Get required skills for target position
        required_skills = self.position_requirements.get(target_position, [])
        
        for skill, weight in self.skill_weights.items():
            if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
                skills_found.append(skill)
                skills_score += weight
                
                # Bonus for required skills
                if skill in required_skills:
                    skills_score += 2  # Small bonus for required skills
        
        # Normalize skills score to max 30
        max_possible_skills = sum(sorted(self.skill_weights.values(), reverse=True)[:10])  # Top 10 skills
        if max_possible_skills > 0:
            skills_score_normalized = (skills_score / max_possible_skills) * 30
            score += skills_score_normalized
        
        # 4. Company reputation (max 10 points)
        company_score = 0
        faang_companies = ["google", "microsoft", "amazon", "facebook", "apple", 
                          "netflix", "meta", "tesla", "spacex", "uber", "airbnb"]
        for company in faang_companies:
            if company in text_lower:
                company_score += 3
        
        score += min(company_score, 10)  # Cap company at 10 points
        
        # 5. Certifications (max 5 points)
        if "certification" in text_lower or "certified" in text_lower:
            score += 3
        
        # 6. Projects/Achievements (max 10 points)
        achievement_keywords = ["achievement", "award", "published", "patent", 
                              "improved", "increased", "reduced", "optimized"]
        achievement_count = sum(1 for keyword in achievement_keywords if keyword in text_lower)
        score += min(achievement_count * 2, 10)
        
        # Apply position-specific adjustments
        if target_position == "data_scientist":
            # Data scientists need more ML/AI skills
            ml_skills = [s for s in skills_found if s in ["machine learning", "ai", "tensorflow", "pytorch"]]
            if len(ml_skills) >= 2:
                score += 5
        elif target_position == "devops":
            # DevOps need cloud and container skills
            devops_skills = [s for s in skills_found if s in ["aws", "docker", "kubernetes", "cloud"]]
            if len(devops_skills) >= 3:
                score += 5
        
        # Cap at 95 (never perfect) and minimum of 30
        final_score = min(95, max(30, score))
        
        return round(final_score), skills_found
    
    def process_folder(self, folder_path, target_position="software_engineer"):
        """Process all resumes in folder"""
        results = []
        
        if not os.path.exists(folder_path):
            print(f"❌ Folder not found: {folder_path}")
            print("📁 Creating NEW realistic sample resumes...")
            self.create_realistic_sample_resumes()
            folder_path = "./resumes"
        
        print(f"\n📂 Processing resumes from: {folder_path}")
        print(f"🎯 Target position: {target_position.replace('_', ' ').title()}")
        
        for filename in os.listdir(folder_path):
            if filename.endswith(('.pdf', '.docx', '.txt')):
                file_path = os.path.join(folder_path, filename)
                print(f"  📄 Analyzing: {filename}")
                
                text = self.parse_resume(file_path)
                if text:
                    grade, skills = self.grade_resume(text, target_position)
                    
                    # Extract years of experience
                    years_exp = 0
                    year_match = re.search(r'(\d+)\s+years?\s+experience', text.lower())
                    if year_match:
                        years_exp = int(year_match.group(1))
                    else:
                        # Try to estimate from dates
                        year_pattern = r'(?:19|20)\d{2}'
                        years = re.findall(year_pattern, text)
                        if len(years) >= 2:
                            try:
                                years_numeric = [int(y) for y in years if 1900 <= int(y) <= 2024]
                                if years_numeric:
                                    years_exp = (max(years_numeric) - min(years_numeric)) / 10
                                    if years_exp > 20:
                                        years_exp = 20
                            except:
                                pass
                    
                    # Create summary
                    words = text.split()[:120]
                    summary = " ".join(words) + ("..." if len(text.split()) > 120 else "")
                    
                    # Categorize (simple version)
                    categories = []
                    if any(skill in ["python", "java", "javascript"] for skill in skills):
                        categories.append("Developer")
                    if any(skill in ["aws", "docker", "kubernetes", "cloud"] for skill in skills):
                        categories.append("Cloud/DevOps")
                    if any(skill in ["machine learning", "ai", "tensorflow", "pytorch"] for skill in skills):
                        categories.append("Data Science")
                    
                    results.append({
                        "filename": filename,
                        "grade": grade,
                        "skills": skills,
                        "summary": summary,
                        "word_count": len(text.split()),
                        "years_experience": round(years_exp, 1),
                        "categories": categories,
                        "position_match": self.calculate_position_match(skills, target_position)
                    })
        
        return results
    
    def calculate_position_match(self, skills, target_position):
        """Calculate how well skills match target position (0-100%)"""
        required_skills = self.position_requirements.get(target_position, [])
        if not required_skills:
            return 0
        
        matched = [skill for skill in skills if skill in required_skills]
        match_percentage = (len(matched) / len(required_skills)) * 100
        return min(100, round(match_percentage))
    
    def create_realistic_sample_resumes(self):
        """Create sample resumes with varying quality"""
        os.makedirs("./resumes", exist_ok=True)
        
        samples = [
            ("expert_devops.txt", """
            Bob Johnson - Expert DevOps Engineer
            Experience: 8 years
            
            SUMMARY:
            Senior DevOps Engineer with 8 years experience at Netflix and Google.
            Expert in AWS, Kubernetes, Docker, and cloud architecture.
            
            EXPERIENCE:
            - Senior DevOps Engineer, Netflix (2020-2024)
              * Managed 1000+ node Kubernetes clusters
              * Reduced infrastructure costs by 35%
              * Led migration to multi-cloud architecture
              * Technologies: AWS, Kubernetes, Docker, Terraform, Python
            
            - DevOps Engineer, Google (2016-2020)
              * Automated deployment for 500+ microservices
              * Implemented zero-downtime deployment
              * Built monitoring with Prometheus/Grafana
            
            EDUCATION:
            - MS in Computer Science, Stanford University
            
            SKILLS:
            Expert: AWS, Kubernetes, Docker, Terraform, Linux
            Proficient: Python, Bash, Jenkins, Git, Prometheus
            Familiar: GCP, Azure, Ansible, Chef
            
            CERTIFICATIONS:
            - AWS DevOps Engineer Professional
            - Certified Kubernetes Administrator (CKA)
            - Google Cloud Professional
            
            ACHIEVEMENTS:
            - Reduced deployment time from 2 hours to 10 minutes
            - Saved company $2M in cloud costs
            - Published article on scaling Kubernetes
            """),
            
            ("good_data_scientist.txt", """
            Jane Smith - Data Scientist
            Experience: 4 years
            
            PROFILE:
            Data Scientist with 4 years experience in ML and analytics.
            Strong background in Python, SQL, and statistical modeling.
            
            EXPERIENCE:
            - Data Scientist, Medium Tech Company (2021-2024)
              * Built recommendation systems for e-commerce
              * Developed fraud detection models
              * Created dashboards for business insights
              * Technologies: Python, SQL, Scikit-learn, XGBoost
            
            - Junior Data Analyst, Startup (2019-2021)
              * Cleaned and analyzed datasets
              * Created basic ML models
              * Assisted senior data scientists
            
            EDUCATION:
            - MS in Data Science, State University
            
            SKILLS:
            Strong: Python, SQL, Machine Learning, Pandas, NumPy
            Intermediate: TensorFlow, PyTorch, AWS, Docker
            Basic: JavaScript, React
            
            CERTIFICATIONS:
            - TensorFlow Developer Certificate
            
            PROJECTS:
            - Customer churn prediction (85% accuracy)
            - Sales forecasting model
            """),
            
            ("junior_developer.txt", """
            Alex Chen - Junior Software Developer
            Experience: 1 year
            
            SUMMARY:
            Junior developer with 1 year of internship experience.
            Eager to learn and grow in software development.
            
            EXPERIENCE:
            - Software Developer Intern, Local Tech (2023-2024)
              * Assisted in building web applications
              * Fixed bugs and implemented small features
              * Participated in code reviews
              * Technologies: Python, JavaScript, HTML/CSS
            
            EDUCATION:
            - BS in Computer Science, Community College
            
            SKILLS:
            Programming: Python (Basic), JavaScript (Basic), HTML/CSS
            Tools: Git, VS Code, Linux basics
            Concepts: OOP, Databases, Algorithms
            
            PROJECTS:
            - Todo app with React
            - Weather API integration
            - Student management system
            
            INTERESTS:
            Learning cloud computing, open source contributions
            """),
            
            ("average_engineer.txt", """
            John Doe - Software Engineer
            Experience: 3 years
            
            SUMMARY:
            Software engineer with 3 years of experience in web development.
            Comfortable with full-stack development.
            
            EXPERIENCE:
            - Software Engineer, Small Tech Firm (2021-2024)
              * Developed web applications using Django
              * Worked on both frontend and backend
              * Collaborated in Agile team
            
            EDUCATION:
            - BS in Software Engineering, University
            
            SKILLS:
            Backend: Python, Django, SQL
            Frontend: JavaScript, HTML, CSS
            Other: Git, Docker basics, AWS basics
            
            CERTIFICATIONS:
            - None listed
            
            PROJECTS:
            - E-commerce website
            - Blog platform
            - API for mobile app
            """)
        ]
        
        for filename, content in samples:
            with open(f"./resumes/{filename}", "w", encoding='utf-8') as f:
                f.write(content.strip())
        
        print("✅ Created 4 realistic resumes (varying quality) in './resumes/'")
        print("   - expert_devops.txt (Expert level)")
        print("   - good_data_scientist.txt (Good level)")
        print("   - average_engineer.txt (Average level)")
        print("   - junior_developer.txt (Junior level)")
    
    def run_screening(self, target_position="software_engineer"):
        """Run the complete screening process"""
        print("\n" + "="*60)
        print("📊 REALISTIC SCREENING PROCESS")
        print("="*60)
        
        # Process resumes
        results = self.process_folder("./resumes", target_position)
        
        if not results:
            print("❌ No resumes found or processed")
            return
        
        # Sort by grade
        results.sort(key=lambda x: x["grade"], reverse=True)
        
        # Display results
        print(f"\n✅ Processed {len(results)} resumes")
        print("\n🏆 CANDIDATE RANKINGS:")
        print("="*60)
        
        for i, result in enumerate(results, 1):
            skills_str = ", ".join(result["skills"][:5]) if result["skills"] else "Basic skills"
            categories_str = ", ".join(result["categories"]) if result["categories"] else "General"
            
            print(f"\n{i}. {result['filename']}")
            print(f"   Score: {result['grade']}/100")
            print(f"   Position Match: {result['position_match']}%")
            print(f"   Experience: {result['years_experience']} years")
            print(f"   Category: {categories_str}")
            print(f"   Top Skills: {skills_str}")
        
        # Save to CSV
        df = pd.DataFrame(results)
        
        # Ensure results directory exists
        os.makedirs("./results", exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f"./results/realistic_results_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        
        # Save detailed JSON
        json_file = csv_file.replace('.csv', '.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "screening_date": datetime.now().isoformat(),
                "target_position": target_position,
                "total_candidates": len(results),
                "results": results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Results saved to:")
        print(f"   CSV: {csv_file}")
        print(f"   JSON: {json_file}")
        
        # Print statistics
        grades = [r["grade"] for r in results]
        avg_grade = sum(grades) / len(grades)
        
        print(f"\n📊 SCREENING STATISTICS:")
        print(f"   Average Score: {avg_grade:.1f}/100")
        print(f"   Highest Score: {max(grades)}/100")
        print(f"   Lowest Score: {min(grades)}/100")
        print(f"   Score Range: {max(grades) - min(grades)} points")
        print(f"   Total Candidates: {len(results)}")
        
        # Show recommendations based on position
        print(f"\n🎯 RECOMMENDATIONS FOR {target_position.replace('_', ' ').upper()}:")
        print("-" * 50)
        
        for i, result in enumerate(results[:3], 1):
            print(f"\n{i}. {result['filename']} - {result['grade']}/100")
            print(f"   Why: {self.generate_recommendation_reason(result, target_position)}")
        
        # Time savings calculation (from paper: 11x faster)
        estimated_manual_time = len(results) * 0.25  # 15 minutes per resume
        automated_time = estimated_manual_time / 11  # 11x faster per paper
        
        print(f"\n⏱️  TIME SAVINGS (from paper findings):")
        print(f"   Estimated manual screening: {estimated_manual_time:.1f} hours")
        print(f"   Automated screening: {automated_time:.1f} hours")
        print(f"   Time saved: {estimated_manual_time - automated_time:.1f} hours")
        print(f"   Efficiency: 11x faster than manual (per research paper)")
        
        print("\n" + "="*60)
        print("✅ REALISTIC SCREENING COMPLETED!")
        print("="*60)
        
        return results
    
    def generate_recommendation_reason(self, candidate, target_position):
        """Generate reason for recommendation (like in paper)"""
        reasons = []
        
        if candidate["grade"] >= 85:
            reasons.append("High overall score")
        elif candidate["grade"] >= 70:
            reasons.append("Good overall score")
        
        if candidate["position_match"] >= 80:
            reasons.append("Excellent skill match for position")
        elif candidate["position_match"] >= 60:
            reasons.append("Good skill match")
        
        if candidate["years_experience"] >= 5:
            reasons.append("Significant experience")
        elif candidate["years_experience"] >= 3:
            reasons.append("Adequate experience")
        
        if "Developer" in candidate["categories"] and target_position == "software_engineer":
            reasons.append("Strong developer profile")
        
        if "Data Science" in candidate["categories"] and target_position == "data_scientist":
            reasons.append("Strong data science background")
        
        if "Cloud/DevOps" in candidate["categories"] and target_position == "devops":
            reasons.append("Strong DevOps/cloud expertise")
        
        return "; ".join(reasons) if reasons else "Meets basic requirements"

# Run the screener
if __name__ == "__main__":
    import sys
    
    # Get target position from command line or use default
    target_position = "software_engineer"
    if len(sys.argv) > 1:
        target_position = sys.argv[1].lower()
    
    # Validate position
    valid_positions = ["software_engineer", "data_scientist", "devops", "full_stack"]
    if target_position not in valid_positions:
        print(f"⚠️  Unknown position: {target_position}")
        print(f"   Using default: software_engineer")
        print(f"   Valid positions: {', '.join(valid_positions)}")
        target_position = "software_engineer"
    
    screener = RealisticResumeScreener()
    results = screener.run_screening(target_position)
    
    print(f"\n💡 RESEARCH PAPER COMPARISON:")
    print("   Paper reported: 87.73% F1 score for classification")
    print("   Paper reported: 81.35% grade accuracy (±5 points)")
    print("   Paper reported: 11x faster than manual screening")
    
    print(f"\n📋 TO TRY DIFFERENT POSITIONS:")
    print("   python realistic_screener.py software_engineer")
    print("   python realistic_screener.py data_scientist")
    print("   python realistic_screener.py devops")
    print("   python realistic_screener.py full_stack")
    
    # Optional: Wait for user input
    try:
        input("\nPress Enter to exit...")
    except:
        pass