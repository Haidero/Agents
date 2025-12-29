import torch
from transformers import pipeline, BitsAndBytesConfig
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
        
        try:
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
            self.use_mock = False
        except Exception as e:
            print(f"[WARN] Could not load local model: {e}")
            print("[INFO] Switching to MOCK/RULE-BASED grading mode")
            self.model = None
            self.tokenizer = None
            self.pipeline = None
            self.generate = self._generate_mock
            self.use_mock = True
    
    def _create_hr_prompt(self, resume_text: str, target_position: str) -> str:
        """Create prompt for HR agent (role-playing as per paper)"""
        return f"""You are an experienced HR professional. Evaluate this resume for the position of "{target_position}".

RESUME CONTENT:
{resume_text}

INSTRUCTIONS:
1. Analyze the candidate's relevance to "{target_position}".
2. Evaluate specific skills, experience quality, and formatting.
3. Provide a final score out of 100.

OUTPUT FORMAT:
Return ONLY a strictly valid JSON object. Do not include markdown formatting or backticks.
{{
    "grade": <int 0-100>,
    "summary": "<concise summary max 50 words>",
    "relevance_score": <int 0-100>,
    "skills_score": <int 0-100>,
    "experience_score": <int 0-100>,
    "formatting_score": <int 0-100>
}}
"""
    
    def _generate_gpt(self, prompt: str) -> str:
        """Generate using GPT API"""
        import openai
        
        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a helpful HR assistant that outputs only JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=400
        )
        
        return response.choices[0].message.content
    
    def _generate_local(self, prompt: str) -> str:
        """Generate using local model"""
        output = self.pipeline(
            prompt,
            max_new_tokens=400,
            temperature=0.2,
            do_sample=True,
            early_stopping=True
        )[0]['generated_text']
        
        # Extract only the new generated part
        return output[len(prompt):].strip()

    def _generate_mock(self, prompt: str) -> str:
        """Generate mock response (Random but realistic)"""
        import random
        base_grade = random.randint(60, 95)
        
        # Simple summary based on grade
        if base_grade > 85:
            summary = "Excellent candidate with strong relevant experience."
        elif base_grade > 75:
            summary = "Good candidate with solid foundation."
        else:
            summary = "Decent candidate but lacks specific depth."
            
        return json.dumps({
            "grade": base_grade,
            "summary": summary,
            "relevance_score": base_grade - random.randint(0, 5),
            "skills_score": base_grade + random.randint(-5, 5),
            "experience_score": base_grade - random.randint(0, 10),
            "formatting_score": random.randint(80, 100)
        })
    
    def _parse_response(self, response: str) -> Dict:
        """Parse grade and summary from model response"""
        try:
            # Clean response if it contains markdown code blocks
            clean_response = response.strip()
            if "```json" in clean_response:
                clean_response = clean_response.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_response:
                clean_response = clean_response.split("```")[1].split("```")[0].strip()
                
            data = json.loads(clean_response)
            return data
        except Exception as e:
            print(f"Error parsing JSON response: {e}. Raw response: {response}")
            # Fallback
            return {
                "grade": 0,
                "summary": "Error parsing agent response",
                "relevance_score": 0,
                "skills_score": 0, 
                "experience_score": 0,
                "formatting_score": 0
            }
    
    def grade_and_summarize(self, resume_text: str, target_position: str = "software_engineer") -> Dict:
        """Grade and summarize a single resume"""
        prompt = self._create_hr_prompt(resume_text, target_position)
        response = self.generate(prompt)
        parsed_data = self._parse_response(response)
        
        return {
            "grade": parsed_data.get("grade", 0),
            "summary": parsed_data.get("summary", ""),
            "details": {
                "relevance": parsed_data.get("relevance_score", 0),
                "skills": parsed_data.get("skills_score", 0),
                "experience": parsed_data.get("experience_score", 0),
                "formatting": parsed_data.get("formatting_score", 0)
            },
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