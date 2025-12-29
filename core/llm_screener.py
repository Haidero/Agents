import os
import json
from typing import List, Dict, Any, Optional
from tqdm import tqdm
import logging
import time

# Import configuration
from config import model_config, agent_config, data_config

# Import Agents
try:
    from agents.parser_agent import ResumeParserAgent
    from agents.classifier_agent import SentenceClassifierAgent
    from agents.grader_agent import HRGraderAgent
    from agents.decision_agent import DecisionMakerAgent
except ImportError:
    # Handle case where agents might be in different path structure during dev
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from agents.parser_agent import ResumeParserAgent
    from agents.classifier_agent import SentenceClassifierAgent
    from agents.grader_agent import HRGraderAgent
    from agents.decision_agent import DecisionMakerAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedConfig:
    """Helper to combine configs for agents that expect a single config object"""
    def __init__(self, model_conf, agent_conf, data_conf):
        # Merge all attributes
        for conf in [model_conf, agent_conf, data_conf]:
            for key, value in conf.__dict__.items():
                setattr(self, key, value)

class LLMScreener:
    """
    Orchestrator for the Agents-based Resume Screening System.
    Implements the pipeline: Parse -> Classify -> Grade -> Decide.
    """
    
    def __init__(self, use_gpu: bool = None):
        """
        Initialize the screener and all agents.
        
        Args:
            use_gpu: Whether to use GPU for local models. If None, detects auto.
        """
        # Create unified config for agents
        self.config = UnifiedConfig(model_config, agent_config, data_config)
        
        # Override device if specified
        if use_gpu is not None:
            self.config.device = "cuda" if use_gpu else "cpu"
            
        logger.info(f"🚀 Initializing LLM Screener (Device: {self.config.device})")
        
        # Initialize Agents
        self.parser = ResumeParserAgent(self.config)
        
        # Initialize LLM Agents (Lazy load or immediate?)
        # For now immediate, but we handle the 'mock' or 'api' fallback in a standardized way
        # Note: Agents currently implementation might try to load local models immediately.
        # We might need to ensure they fallback gracefully if model path doesn't exist.
        
        self.classifier = SentenceClassifierAgent(self.config)
        
        # Determine if we use GPT or Local for Grader/Decision
        use_gpt = bool(self.config.openai_api_key)
        self.grader = HRGraderAgent(self.config, use_gpt=use_gpt)
        self.decision_maker = DecisionMakerAgent(self.config)
        
    def process_resume(self, file_path: str, target_position: str = "software_engineer") -> Dict:
        """
        Process a single resume through the full pipeline.
        
        Args:
            file_path: Path to resume file
            target_position: Target job position
            
        Returns:
            Dictionary containing results from all stages
        """
        logger.info(f"📄 Processing resume: {file_path}")
        start_time = time.time()
        
        try:
            # Stage 1: Parsing
            logger.info("  1️⃣ Parsing...")
            parsed_data = self.parser.parse_resume(file_path)
            
            # Stage 2: Classification & Filtering (Privacy)
            logger.info("  2️⃣ Classifying & Filtering...")
            # Convert ResumeData object to dict for classifier compatibility
            resume_dict = {
                "sentences": parsed_data.sentences,
                "metadata": parsed_data.metadata
            }
            classification_result = self.classifier.process_resume(resume_dict)
            
            # Stage 3: Grading & Summarization
            # Stage 3: Grading & Summarization
            logger.info("  3️⃣ Grading & Summarizing...")
            filtered_text = classification_result["filtered_text"]
            
            # Pass target position to grader for context-aware grading
            grading_result = self.grader.grade_and_summarize(filtered_text, target_position)
            
            # Stage 4: Calculate additional metrics (Skill match, experience)
            # This logic was in the rule-based screener, let's reuse/re-implement some of it
            # or rely on the LLM's summary. 
            # For compatibility with EmailAgent, we should provide these fields.
            
            # Simple keyword matching for skills (fallback/hybrid)
            # TODO: Improve this with SkillExtractionAgent?
            skills_found = self._extract_skills_rule_based(filtered_text)
            years_exp = self._extract_experience_rule_based(filtered_text)
            position_match = self._calculate_match(skills_found, target_position)
            
            processing_time = time.time() - start_time
            
            return {
                "filename": os.path.basename(file_path),
                "filepath": file_path,
                "target_position": target_position,
                "parsed_data": {
                    "word_count": parsed_data.metadata["word_count"]
                },
                "classification_result": {
                    "stats": classification_result["category_statistics"]
                },
                "grading_result": grading_result,
                "derived_metrics": {
                    "skills": skills_found,
                    "years_experience": years_exp,
                    "position_match": position_match
                },
                # Flattened fields for easy access by EmailAgent/UI
                "score": grading_result["grade"] or 0,
                "summary": grading_result["summary"] or "",
                "details": grading_result.get("details", {}),
                "skills": skills_found,
                "years_experience": years_exp,
                "position_match": position_match,
                "processing_time": processing_time 
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing {file_path}: {str(e)}")
            return {"error": str(e), "filename": os.path.basename(file_path)}

    def batch_process(self, folder_path: str, target_position: str = "software_engineer") -> List[Dict]:
        """Process all resumes in a folder"""
        results = []
        if not os.path.exists(folder_path):
            logger.error(f"Folder not found: {folder_path}")
            return []
            
        files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                if f.lower().endswith(('.pdf', '.docx', '.txt', '.doc'))]
        
        logger.info(f"📂 Batch processing {len(files)} resumes from {folder_path}")
        
        for file_path in tqdm(files, desc="Screening Resumes"):
            result = self.process_resume(file_path, target_position)
            if "error" not in result:
                results.append(result)
        
        return results

    def make_hiring_decision(self, results: List[Dict], top_n: int = 10) -> Dict:
        """Call DecisionAgent to select candidates"""
        logger.info("  4️⃣ Making Hiring Decision...")
        
        # Reformulate results for DecisionAgent compatibility
        # DecisionAgent expects list of dicts with "grading_result" key
        
        decision = self.decision_maker.make_decision(results)
        return decision

    # --- Helper methods (Rule-based fallbacks for speed/reliability) ---

    def _extract_skills_rule_based(self, text: str) -> List[str]:
        """Extract skills using regex (reused from original screener)"""
        # Common tech skills
        common_skills = [
            "python", "java", "javascript", "aws", "docker", "kubernetes", "sql", 
            "react", "node.js", "tensorflow", "pytorch", "machine learning", "ai", 
            "cloud", "devops", "azure", "gcp", "linux", "git", "c++", "c#", "go", "rust"
        ]
        text_lower = text.lower()
        found = []
        import re
        for skill in common_skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
                found.append(skill)
        return found

    def _extract_experience_rule_based(self, text: str) -> float:
        """Extract experience years using regex"""
        import re
        text_lower = text.lower()
        # Look for "X years experience"
        match = re.search(r'(\d+)\s*years?\s*(?:of)?\s*experience', text_lower)
        if match:
            return float(match.group(1))
        return 0.0

    def _calculate_match(self, skills: List[str], position: str) -> int:
        """Simple skill match percentage"""
        # Define some basic requirements
        requirements = {
            "software_engineer": ["python", "java", "javascript", "sql"],
            "data_scientist": ["python", "machine learning", "sql", "tensorflow"],
            "devops": ["aws", "docker", "linux", "kubernetes"],
            "full_stack": ["javascript", "react", "node.js", "html"]
        }
        reqs = requirements.get(position.lower(), [])
        if not reqs:
            return 0
        
        matches = [s for s in skills if s in reqs]
        return int((len(matches) / len(reqs)) * 100)

    # --- Compatibility Methods for EmailScreener ---
    
    def grade_resume(self, text: str, target_position: str) -> tuple:
        """
        Compatibility wrapper for EmailAgent which calls screener.grade_resume(text, pos)
        Returns (grade, skills)
        """
        # The EmailAgent passes raw text.
        # But LLMScreener pipeline expects a file path usually.
        # We can bypass parser/classifier if we just have text, or wrap it.
        
        # Grading stage
        grading_result = self.grader.grade_and_summarize(text, target_position)
        grade = grading_result.get("grade", 0) or 0
        
        # Skill extraction
        skills = self._extract_skills_rule_based(text)
        
        return grade, skills

    def extract_experience(self, text: str) -> float:
        """Compatibility wrapper"""
        return self._extract_experience_rule_based(text)

    def calculate_position_match(self, skills: List[str], target_position: str) -> int:
        """Compatibility wrapper"""
        return self._calculate_match(skills, target_position)
