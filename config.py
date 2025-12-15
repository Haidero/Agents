import os
from dataclasses import dataclass
from typing import List, Dict, Optional

# Try to import torch, but handle if not installed
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    torch = None

@dataclass
class ModelConfig:
    """Configuration for LLM models"""
    # Local models
    llama2_7b_path: str = "./models/llama2-7b"
    llama2_13b_path: str = "./models/llama2-13b"
    llama2_70b_path: str = "./models/llama2-70b"
    
    # API models (alternative)
    openai_api_key: Optional[str] = None
    gpt_model: str = "gpt-3.5-turbo"
    gpt4_model: str = "gpt-4-turbo-preview"
    
    # Model settings
    use_local: bool = True
    # Fix the device setting - use simple string first
    device: str = "cpu"  # Default to CPU, we'll detect GPU later
    precision: str = "float32"
    
    def __post_init__(self):
        """Detect GPU after the class is created"""
        if HAS_TORCH and torch.cuda.is_available():
            self.device = "cuda"
            self.precision = "float16"
        else:
            self.device = "cpu"
            self.precision = "float32"

@dataclass
class AgentConfig:
    """Configuration for agents"""
    # Sentence classification categories (from paper)
    categories: List[str] = [
        "personal_information",
        "experience",
        "summary",
        "education",
        "qualification_certification",
        "skill",
        "objectives"
    ]
    
    # Privacy protection
    remove_personal_info: bool = True
    sensitive_categories: List[str] = ["personal_information"]
    
    # Grading settings
    max_grade: int = 100
    summary_max_words: int = 100
    
    # Decision making
    top_n_candidates: int = 10
    decision_criteria: Dict = None

@dataclass
class DataConfig:
    """Configuration for data paths"""
    input_dir: str = "./data/resumes"
    processed_dir: str = "./data/processed"
    results_dir: str = "./data/results"
    cache_dir: str = "./data/cache"
    
    # File extensions to process
    supported_extensions: List[str] = [".pdf", ".docx", ".txt", ".doc"]

# Initialize configurations
model_config = ModelConfig()
agent_config = AgentConfig()
data_config = DataConfig()

# Ensure directories exist
for dir_path in [data_config.input_dir, data_config.processed_dir, 
                 data_config.results_dir, data_config.cache_dir]:
    os.makedirs(dir_path, exist_ok=True)

# Print status
print(f"✅ Config loaded. Device: {model_config.device}, Precision: {model_config.precision}")
if model_config.device == "cuda":
    print(f"   GPU detected: {torch.cuda.get_device_name(0)}")
else:
    print("   Using CPU (no GPU detected)")