import torch
from transformers import pipeline
import re
from typing import Dict, List, Tuple, Optional
import json
from tqdm import tqdm

class HRGraderAgent:
    """Agent for grading and summarizing resumes (as per paper)"""
    
    def __init__(self, config, model_path=None, use_gpt=False):
        self.config = config
        self.use_gpt = use_gpt
        self.max_grade = config.max_grade
        self.summary_max_words = config.summary_max_words
        
        if use_gpt and self.config.openai_api_key:
            self._setup_openai()
        else:
            self._setup_local_model(model_path)
    
    def _setup_openai(self):
        """Setup for OpenAI GPT models"""
        import openai
        openai.api_key = self.config.openai_api_key
        
        if self.config.gpt_model.startswith("gpt-4"):
            self.model_name = self.config.gpt4_model
        else:
            self.model_name = self.config.gpt_model
        
        self.generate = self._generate_gpt
    
    def _setup_local_model(self, model_path=None):
        """Setup for local LLaMA2 model"""
        if model_path is None:
            model_path = self.config.llama2_13b_path
        
        # Use 4-bit quantization
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16
        )
        
        from transformers import AutoTokenizer, AutoModelForCausalLM
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.float16
        )
        
        self.pipeline = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=200,
            temperature=0.3,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        self.generate = self._generate_local
    
    def _create_hr_prompt(self, resume_text: str) -> str:
        """Create prompt for HR agent (role-playing as per paper)"""
        return f"""You are an experienced HR professional with 10+ years of experience in IT recruitment at top tech companies.

Please evaluate this resume for a software engineering position:

{resume_text}

Instructions:
1. Assign a grade from 0 to {self.max_grade} based on relevance, experience, skills, and qualifications.
2. Write a concise summary (max {self.summary_max_words} words) highlighting key strengths.

Format your response exactly as:
Grade: [number]/100
Summary: [your summary here]

Begin your evaluation:"""
    
    def _generate_gpt(self, prompt: str) -> str:
        """Generate using GPT API"""
        import openai
        
        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are an expert HR professional."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        return response.choices[0].message.content
    
    def _generate_local(self, prompt: str) -> str:
        """Generate using local model"""
        output = self.pipeline(
            prompt,
            max_new_tokens=300,
            temperature=0.3,
            do_sample=True,
            early_stopping=True
        )[0]['generated_text']
        
        # Extract only the new generated part
        return output[len(prompt):].strip()
    
    def _parse_response(self, response: str) -> Tuple[Optional[int], Optional[str]]:
        """Parse grade and summary from model response"""
        grade = None
        summary = None
        
        # Extract grade using regex
        grade_match = re.search(r'Grade:\s*(\d+)\s*/\s*100', response, re.IGNORECASE)
        if grade_match:
            try:
                grade = int(grade_match.group(1))
                if grade < 0 or grade > 100:
                    grade = None
            except:
                grade = None
        
        # Extract summary
        summary_match = re.search(r'Summary:\s*(.+?)(?:\n\n|\Z)', response, re.IGNORECASE | re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
        
        return grade, summary
    
    def grade_and_summarize(self, resume_text: str) -> Dict:
        """Grade and summarize a single resume"""
        prompt = self._create_hr_prompt(resume_text)
        response = self.generate(prompt)
        grade, summary = self._parse_response(response)
        
        return {
            "grade": grade,
            "summary": summary,
            "full_response": response,
            "word_count": len(resume_text.split())
        }
    
    def process_classified_resume(self, classified_data: Dict) -> Dict:
        """Process a classified resume"""
        filtered_text = classified_data.get("filtered_text", "")
        
        result = self.grade_and_summarize(filtered_text)
        
        return {
            **classified_data,
            "grading_result": result
        }
    
    def batch_grade(self, classified_dir: str) -> List[Dict]:
        """Grade all classified resumes in a directory"""
        import glob
        
        results = []
        json_files = glob.glob(f"{classified_dir}/*_classified.json")
        
        for json_file in tqdm(json_files, desc="Grading resumes"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    classified_data = json.load(f)
                
                result = self.process_classified_resume(classified_data)
                
                # Save result
                output_file = json_file.replace("_classified.json", "_graded.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                results.append(result)
                
            except Exception as e:
                print(f"Error grading {json_file}: {e}")
        
        return results