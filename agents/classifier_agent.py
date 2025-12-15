import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM,
    pipeline,
    BitsAndBytesConfig
)
from typing import List, Dict, Any, Tuple
import re
import json
from tqdm import tqdm

class SentenceClassifierAgent:
    """Agent for classifying resume sentences (based on paper's instruction format)"""
    
    def __init__(self, config, model_path=None):
        self.config = config
        self.categories = config.categories
        self.sensitive_categories = config.sensitive_categories
        
        # Load model and tokenizer
        try:
            self.model, self.tokenizer = self._load_model(model_path)
            self.pipeline = self._create_pipeline()
            self.use_mock = False
        except Exception as e:
            print(f"[WARN] Could not load local model: {e}")
            print("[INFO] Switching to MOCK/RULE-BASED classification mode")
            self.model = None
            self.tokenizer = None
            self.pipeline = None
            self.use_mock = True
        
        # Create instruction template (CRITICAL - from paper)
        self.instruction_template = """Classify this resume sentence into one of the following categories:
{}

Sentence: "{}"

Answer:"""
    
    def _load_model(self, model_path=None):
        """Load LLaMA2 model with quantization"""
        if model_path is None:
            model_path = self.config.llama2_7b_path
        
        # Quantization config for memory efficiency
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True
        )
        
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        tokenizer.pad_token = tokenizer.eos_token
        
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.float16
        )
        
        return model, tokenizer
    
    def _create_pipeline(self):
        """Create text generation pipeline"""
        return pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=10,
            temperature=0.1,
            do_sample=False,
            pad_token_id=self.tokenizer.eos_token_id
        )
    
    def _format_instruction(self, sentence: str) -> str:
        """Format sentence with instruction (as per paper)"""
        categories_str = "\n".join([f"- {cat}" for cat in self.categories])
        return self.instruction_template.format(categories_str, sentence)
    
    def classify_sentence(self, sentence: str) -> Tuple[str, str]:
        """Classify a single sentence"""
        # Mock/Rule-based Fallback
        if self.use_mock:
            lower_sentence = sentence.lower()
            if "skill" in lower_sentence or "expert" in lower_sentence or "proficient" in lower_sentence:
                return "skill", "skill"
            elif "experience" in lower_sentence or "year" in lower_sentence or "worked" in lower_sentence:
                return "experience", "experience"
            elif "university" in lower_sentence or "degree" in lower_sentence or "bachelor" in lower_sentence:
                return "education", "education"
            elif "email" in lower_sentence or "phone" in lower_sentence or "@" in lower_sentence:
                return "personal_information", "personal_information"
            else:
                return "summary", "summary"

        prompt = self._format_instruction(sentence)
        
        try:
            output = self.pipeline(prompt)[0]['generated_text']
            
            # Extract the classification (text after "Answer:")
            answer_part = output.split("Answer:")[-1].strip()
            
            # Find which category is in the answer
            for category in self.categories:
                if category.lower() in answer_part.lower():
                    return category, answer_part
            
            # Default to "unknown" if no match
            return "unknown", answer_part
            
        except Exception as e:
            print(f"Error classifying sentence: {e}")
            return "error", ""
    
    def process_resume(self, resume_data: Dict) -> Dict:
        """Process a resume: classify all sentences and remove personal info"""
        sentences = resume_data.get("sentences", [])
        
        classified_sentences = []
        filtered_sentences = []
        
        for sentence in tqdm(sentences, desc="Classifying sentences"):
            category, full_answer = self.classify_sentence(sentence)
            
            classified_sentences.append({
                "sentence": sentence,
                "category": category,
                "model_output": full_answer
            })
            
            # Filter out sensitive categories if enabled
            if self.config.remove_personal_info:
                if category not in self.sensitive_categories:
                    filtered_sentences.append(sentence)
            else:
                filtered_sentences.append(sentence)
        
        # Statistics
        category_counts = {}
        for item in classified_sentences:
            cat = item["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return {
            "original_resume": resume_data,
            "classified_sentences": classified_sentences,
            "filtered_text": " ".join(filtered_sentences),
            "category_statistics": category_counts,
            "total_sentences": len(sentences),
            "filtered_sentences": len(filtered_sentences)
        }
    
    def batch_classify(self, processed_dir: str) -> List[Dict]:
        """Classify all resumes in a directory"""
        import glob
        
        results = []
        json_files = glob.glob(f"{processed_dir}/*.json")
        
        for json_file in tqdm(json_files, desc="Processing resumes"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    resume_data = json.load(f)
                
                result = self.process_resume(resume_data)
                
                # Save result
                output_file = json_file.replace(".json", "_classified.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                results.append(result)
                
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
        
        return results