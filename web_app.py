"""
WEB UI for Resume Screening System
Run with: streamlit run web_app.py
"""

import streamlit as st
import pandas as pd
import os
import json
import re
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# Import core screener
# Import core screeners
try:
    from core.screener import RealisticResumeScreener
    from core.llm_screener import LLMScreener
except ImportError:
    # If run from root, this works. If run from inside, might need path adjustment
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from core.screener import RealisticResumeScreener
    # LLMScreener might fail if agents missing dependencies, handle gracefully
    try:
        from core.llm_screener import LLMScreener
    except:
        LLMScreener = None

# Page configuration
st.set_page_config(
    page_title="AI Resume Screener",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #3B82F6;
        margin-top: 1.5rem;
    }
    .highlight-box {
        background-color: #F0F9FF;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #3B82F6;
        margin: 1rem 0;
    }
    .metric-box {
        background-color: #F8FAFC;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .candidate-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
        border-left: 4px solid #3B82F6;
    }
</style>
""", unsafe_allow_html=True)

class ResumeScreenerWebWrapper:
    def __init__(self, mode="rule_based"):
        self.mode = mode
        if mode == "llm" and LLMScreener:
            self.screener = LLMScreener()
        else:
            self.screener = RealisticResumeScreener()
        # Create necessary directories
        os.makedirs("./uploads", exist_ok=True)
        os.makedirs("./results", exist_ok=True)
    
    def parse_resume(self, file_bytes, filename):
        """Parse uploaded resume file"""
        # Save temporarily to parse
        temp_path = os.path.join("./uploads", filename)
        with open(temp_path, "wb") as f:
            f.write(file_bytes)
        
        text = self.screener.parse_resume(temp_path)
        
        # Clean up
        try:
            os.remove(temp_path)
        except:
            pass
            
        return text if text else "Could not read file"
    
    def analyze_resume(self, text, position):
        """Analyze resume content using core screener"""
        if not text:
            return {"error": "No text content"}
        
        # Use the core screener logic
        grade, skills = self.screener.grade_resume(text, position)
        
        # Extract experience
        experience = self.screener.extract_experience(text)
        
        # Determine education level (simple extraction)
        text_lower = text.lower()
        education = "Not specified"
        if "phd" in text_lower or "doctorate" in text_lower:
            education = "PhD"
        elif "master" in text_lower or "ms" in text_lower:
            education = "Master's"
        elif "bachelor" in text_lower or "bs" in text_lower:
            education = "Bachelor's"
            
        # Create summary
        words = text.split()
        summary = " ".join(words[:150]) + "..." if len(words) > 150 else text
        
        return {
            "score": grade,
            "skills": skills,
            "experience_years": experience,
            "education_level": education,
            "summary": summary,
            "word_count": len(words),
            "skills_match": self.screener.calculate_position_match(skills, position)
        }
    
    def run_email_agent_process(self, days=7, position="software_engineer", force_rescan=False):
        """Run the email agent as a subprocess"""
        import subprocess
        try:
            # Command to run
            cmd = ["python", "main.py", "email", "--llm", "--days", str(days), "--position", position]
            if force_rescan:
                cmd.append("--force-rescan")
            
            # Run command
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                check=False
            )
            
            return {
                "success": process.returncode == 0,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "returncode": process.returncode
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/resume.png", width=100)
    st.title("📄 AI Resume Screener")
    st.markdown("---")
    
    # Mode Selection
    mode = st.radio("Screening Mode", ["Rule-Based (Fast)", "LLM Agent (Research)"])
    use_llm = "LLM" in mode
    
    if use_llm and not LLMScreener:
        st.error("LLM Agents not available. Missing dependencies?")
        use_llm = False

    # Position Selection (Global)
    st.subheader("⚙️ Global Settings")
    position = st.selectbox(
        "Select Position Type:",
        ["software_engineer", "data_scientist", "devops", "full_stack"],
        format_func=lambda x: x.replace("_", " ").title()
    )
    
    st.markdown("---")

    wrapper = ResumeScreenerWebWrapper(mode="llm" if use_llm else "rule_based")
    st.markdown("---")

    # Email Agent Section
    st.subheader("📧 Email Agent")
    
    # Date Range Selection
    date_range = st.selectbox(
        "Scan Period",
        ["Last 24 Hours", "Last 3 Days", "Last 1 Week", "Last 1 Month"],
        index=2
    )
    
    days_map = {
        "Last 24 Hours": 1,
        "Last 3 Days": 3,
        "Last 1 Week": 7,
        "Last 1 Month": 30
    }
    
    force_rescan = st.checkbox("Force Rescan (Ignore processed)", value=False)
    
    if st.button("Run Email Agent Now", type="primary"):
        with st.spinner(f"Checking emails from {date_range} for {position.replace('_', ' ').title()}..."):
            result = wrapper.run_email_agent_process(days=days_map[date_range], position=position, force_rescan=force_rescan)
            
            if result.get("success"):
                st.success("Email Agent finished successfully!")
                with st.expander("View Logs"):
                    st.code(result.get("stdout"))
            else:
                st.error("Email Agent failed!")
                if result.get("error"):
                    st.error(result["error"])
                with st.expander("Error Details"):
                    st.code(result.get("stderr"))
                    st.code(result.get("stdout"))
    
    # Display Results (Aggregated)
    import glob
    try:
        results_files = glob.glob(os.path.join("./email_results", "*.json"))
        if results_files:
            all_results = []
            
            # Load all files
            for file in results_files:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if data.get("results"):
                        for r in data["results"]:
                            # Add date from file if not in result
                            if "screening_date" not in r:
                                r["screening_date"] = data.get("screening_date")
                            all_results.append(r)
            
            # Deduplicate by Candidate ID
            unique_results = {}
            for r in all_results:
                # Use email + position as key if candidate_id missing
                key = r.get("candidate_id", f"{r['email_data']['from']}_{r['resume_info']['target_position']}")
                # Updating ensures we get the latest version if duplicates exist
                unique_results[key] = r
            
            final_results = list(unique_results.values())
            
            # Sort by date
            final_results.sort(key=lambda x: x.get("screening_results", {}).get("screened_date", ""), reverse=True)
            
            if final_results:
                st.divider()
                st.markdown(f"### 📊 Email Stats (All Time)")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Total Candidates", len(final_results))
                    st.metric("Accepted", len([r for r in final_results if r["screening_results"]["status"] == "Accepted"]))
                    
                with col_b:
                    st.metric("Rejected", len([r for r in final_results if r["screening_results"]["status"] == "Rejected"]))
                    st.metric("Needs Review", len([r for r in final_results if r["screening_results"]["status"] == "Needs Review"]))
                
                if st.checkbox("Show Recent Email Activity", value=True):
                    for r in final_results[:5]:
                        status_icon = "✅" if r["screening_results"]["status"] == "Accepted" else "❌" if r["screening_results"]["status"] == "Rejected" else "⚠️"
                        st.markdown(f"""
                        **{status_icon} {r['email_data']['sender_name']}**  
                        {r['resume_info']['target_position']} | Score: {r['screening_results']['score']}
                        """)
    except Exception as e:
        st.error(f"Error loading results: {e}")
    
    st.markdown("---")
    
    # File upload
    
    # File upload
    st.subheader("📤 Upload Resumes")
    uploaded_files = st.file_uploader(
        "Choose resume files",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )
    
    # Advanced settings
    with st.expander("Advanced Settings"):
        min_score = st.slider("Minimum Score Threshold", 0, 100, 60)
        top_n = st.slider("Show Top N Candidates", 1, 20, 10)
        show_details = st.checkbox("Show Detailed Analysis", True)
    
    st.markdown("---")
    st.markdown("""
    ### 📊 Based on Research
    - **87.73%** F1 score (paper)
    - **81.35%** grade accuracy (±5)
    - **11× faster** than manual
    """)

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('<h1 class="main-header">🤖 AI Resume Screening System</h1>', unsafe_allow_html=True)
    st.markdown("""
    <div class="highlight-box">
        <h4>🎯 About This System</h4>
        This system implements the research paper <strong>"Application of LLM Agents in Recruitment"</strong>.
        It automates resume screening using intelligent agents to parse, analyze, and rank candidates.
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="metric-box">
        <h3>⚡ Efficiency</h3>
        <h2>11× Faster</h2>
        <p>than manual screening</p>
    </div>
    """, unsafe_allow_html=True)

# Process files
if uploaded_files:
    st.markdown(f"## 📋 Processing {len(uploaded_files)} Resume(s)")
    
    all_results = []
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processing: {uploaded_file.name}")
        
        # Read file
        file_bytes = uploaded_file.read()
        
        # Parse and analyze
        text = wrapper.parse_resume(file_bytes, uploaded_file.name)
        analysis = wrapper.analyze_resume(text, position)
        
        # Add filename and text preview
        analysis["filename"] = uploaded_file.name
        analysis["text_preview"] = text[:500] + "..." if len(text) > 500 else text
        all_results.append(analysis)
        
        # Update progress
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    status_text.text("✅ Processing complete!")
    
    if all_results:
        # Create DataFrame
        df = pd.DataFrame(all_results)
        
        # Sort by score
        df = df.sort_values("score", ascending=False)
        
        # Display metrics
        st.markdown("## 📊 Screening Results")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_score = df["score"].mean()
            st.metric("Average Score", f"{avg_score:.1f}/100")
        
        with col2:
            top_score = df["score"].max()
            st.metric("Top Score", f"{top_score}/100")
        
        with col3:
            qualified = len(df[df["score"] >= min_score])
            st.metric("Qualified", f"{qualified}/{len(df)}")
        
        with col4:
            avg_experience = df["experience_years"].mean()
            st.metric("Avg Experience", f"{avg_experience:.1f} years")
        
        # Visualizations
        st.markdown("## 📈 Analysis Dashboard")
        
        tab1, tab2, tab3 = st.tabs(["Score Distribution", "Skills Analysis", "Top Candidates"])
        
        with tab1:
            # Score distribution chart
            fig = px.histogram(df, x="score", nbins=20, 
                              title="Score Distribution Across Candidates",
                              labels={"score": "Score", "count": "Number of Candidates"})
            fig.update_layout(bargap=0.1)
            st.plotly_chart(fig, width="stretch")
            
            # Score vs Experience
            fig2 = px.scatter(df, x="experience_years", y="score", 
                             size="skills_match", hover_data=["filename"],
                             title="Score vs Experience (bubble size = skills match %)",
                             labels={"experience_years": "Years of Experience", 
                                    "score": "Score", "skills_match": "Skills Match %"})
            st.plotly_chart(fig2, width="stretch")
        
        with tab2:
            # Skills frequency
            all_skills = []
            for skills in df["skills"]:
                all_skills.extend(skills)
            
            if all_skills:
                skills_df = pd.DataFrame({"skill": all_skills})
                skills_count = skills_df["skill"].value_counts().reset_index()
                skills_count.columns = ["skill", "count"]
                
                fig3 = px.bar(skills_count.head(15), x="skill", y="count",
                             title="Most Common Skills Across All Resumes")
                st.plotly_chart(fig3, width="stretch")
            
            # Skills match by candidate
            fig4 = px.bar(df.head(10), x="filename", y="skills_match",
                         title="Skills Match Percentage (Top 10 Candidates)",
                         labels={"filename": "Candidate", "skills_match": "Skills Match %"})
            fig4.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig4, width="stretch")
        
        with tab3:
            # Display top candidates
            st.markdown(f"### 🏆 Top {top_n} Candidates")
            
            top_candidates = df.head(top_n)
            
            for idx, row in top_candidates.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="candidate-card">
                        <h4>{row['filename']} - <span style="color: #3B82F6;">{row['score']}/100</span></h4>
                        <p><strong>Experience:</strong> {row['experience_years']} years | 
                        <strong>Education:</strong> {row['education_level']} | 
                        <strong>Skills Match:</strong> {row['skills_match']}%</p>
                        <p><strong>Top Skills:</strong> {', '.join(row['skills'][:5])}</p>
                        <details>
                            <summary>View Summary</summary>
                            <p>{row['summary']}</p>
                        </details>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show detailed analysis if enabled
                    if show_details:
                        with st.expander("📊 Detailed Analysis"):
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.write("**Score Breakdown:**")
                                st.write(f"- Base score: 50")
                                st.write(f"- Skills bonus: +{row['score'] - 50}")
                                st.write(f"- Experience bonus: +{min(row['experience_years'] * 3, 20)}")
                                
                                # Create gauge chart for score
                                fig_gauge = go.Figure(go.Indicator(
                                    mode="gauge+number",
                                    value=row['score'],
                                    title={'text': "Score"},
                                    domain={'x': [0, 1], 'y': [0, 1]},
                                    gauge={
                                        'axis': {'range': [0, 100]},
                                        'bar': {'color': "#3B82F6"},
                                        'steps': [
                                            {'range': [0, 60], 'color': "lightgray"},
                                            {'range': [60, 80], 'color': "lightblue"},
                                            {'range': [80, 100], 'color': "lightgreen"}
                                        ]
                                    }
                                ))
                                st.plotly_chart(fig_gauge, width="stretch")
                            
                            with col_b:
                                st.write("**Skills Analysis:**")
                                skills_df = pd.DataFrame({
                                    "skill": row['skills'],
                                    "weight": [wrapper.screener.skill_weights.get(skill, 1) 
                                             for skill in row['skills']]
                                })
                                if not skills_df.empty:
                                    fig_skills = px.bar(skills_df.head(8), x="skill", y="weight",
                                                       title="Skill Weights")
                                    st.plotly_chart(fig_skills, width="stretch")
        
        # Download results
        st.markdown("## 📥 Download Results")
        
        # Convert DataFrame to CSV
        csv = df.to_csv(index=False).encode('utf-8')
        
        # Convert to JSON
        json_data = df.to_json(orient='records', indent=2)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📄 Download CSV",
                data=csv,
                file_name=f"resume_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            st.download_button(
                label="📊 Download JSON",
                data=json_data,
                file_name=f"resume_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
else:
    # Check for email results
    import glob
    
    try:
        results_files = glob.glob(os.path.join("./email_results", "*.json"))
        if results_files:
            all_results = []
            
            # Load all files
            for file in results_files:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if data.get("results"):
                        for r in data["results"]:
                            all_results.append(r)
                            
            # Deduplicate
            unique_results = {}
            for r in all_results:
                key = r.get("candidate_id", f"{r['email_data']['from']}_{r['resume_info']['target_position']}")
                unique_results[key] = r
            
            final_results = list(unique_results.values())
            
            if final_results:
                st.markdown(f"## 📧 Email Screening Results (history)")
                
                # Metrics
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Candidates", len(final_results))
                m2.metric("Accepted", len([r for r in final_results if r["screening_results"]["status"] == "Accepted"]))
                m3.metric("Needs Review", len([r for r in final_results if r["screening_results"]["status"] == "Needs Review"]))
                m4.metric("Rejected", len([r for r in final_results if r["screening_results"]["status"] == "Rejected"]))
                
                # Convert to DataFrame
                email_rows = []
                for r in final_results:
                    email_rows.append({
                        "Name": r["email_data"]["sender_name"],
                        "Email": r["email_data"]["from"],
                        "Subject": r["email_data"]["subject"],
                        "Position": r["resume_info"]["target_position"],
                        "Score": r["screening_results"]["score"],
                        "Status": r["screening_results"]["status"],
                        "Exp (Yrs)": r["screening_results"]["experience_years"],
                        "Date": r["screening_results"].get("screened_date", "")[:10]
                    })
                
                df_email = pd.DataFrame(email_rows)
                
                # Show All Candidates first
                st.subheader("📋 All Candidates History")
                st.dataframe(df_email, width="stretch")
                
                st.divider()
                
                # Filter Section
                st.subheader("🔍 Filter Candidates")
                
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    status_filter = st.multiselect(
                        "Filter by Status",
                        ["Accepted", "Rejected", "Needs Review"],
                        default=["Accepted", "Needs Review"]
                    )
                
                # Default filter by selected position
                default_pos_filter = [position]
                if position not in df_email["Position"].unique():
                     default_pos_filter = []
                     
                with col_f2:
                    pos_filter = st.multiselect(
                        "Filter by Position",
                        df_email["Position"].unique(),
                        default=[p for p in default_pos_filter if p in df_email["Position"].unique()]
                    )
                
                # Apply filters
                df_filtered = df_email.copy()
                if status_filter:
                    df_filtered = df_filtered[df_filtered["Status"].isin(status_filter)]
                if pos_filter:
                    df_filtered = df_filtered[df_filtered["Position"].isin(pos_filter)]
                
                st.write(f"Showing {len(df_filtered)} filtered candidates:")
                st.dataframe(df_filtered, width="stretch")
            else:
                st.info("No resumes found in email history.")
        else:
             st.info("No email results found.")

    except Exception as e:
        st.error(f"Error loading email results: {e}")

    # Fallback / Info section
    st.markdown("---")
    st.markdown("## 🎮 Try Manual Upload")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="highlight-box">
            <h4>📤 How to Use</h4>
            <ol>
                <li>Select position type from sidebar</li>
                <li>Upload resume files (PDF, DOCX, TXT)</li>
                <li>Adjust settings as needed</li>
                <li>View automated analysis results</li>
                <li>Download results as CSV/JSON</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="highlight-box">
            <h4>🎯 Based on Research</h4>
            <p>This system implements the framework from:</p>
            <p><strong>"Application of LLM Agents in Recruitment: A Novel Framework for Resume Screening"</strong></p>
            <p>by Chengguang Gan, Qinghao Zhang, Tatsunori Mori</p>
        </div>
        """, unsafe_allow_html=True)