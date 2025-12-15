import json
import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score
from typing import Dict, List, Tuple

class Evaluator:
    """Evaluate the system performance (as per paper metrics)"""
    
    @staticmethod
    def calculate_f1(predictions: List[str], truths: List[str]) -> Dict:
        """Calculate F1 score for classification"""
        unique_labels = list(set(predictions + truths))
        
        precision = precision_score(truths, predictions, average='weighted', zero_division=0)
        recall = recall_score(truths, predictions, average='weighted', zero_division=0)
        f1 = f1_score(truths, predictions, average='weighted', zero_division=0)
        
        return {
            "f1_score": f1,
            "precision": precision,
            "recall": recall,
            "unique_labels": unique_labels
        }
    
    @staticmethod
    def calculate_grade_accuracy(predicted_grades: List[int], true_grades: List[int], tolerance: int = 5) -> Dict:
        """Calculate grade accuracy with tolerance (as per paper)"""
        if len(predicted_grades) != len(true_grades):
            raise ValueError("Grade lists must have same length")
        
        correct = 0
        differences = []
        
        for pred, true in zip(predicted_grades, true_grades):
            diff = abs(pred - true)
            differences.append(diff)
            if diff <= tolerance:
                correct += 1
        
        accuracy = correct / len(predicted_grades)
        
        return {
            "accuracy": accuracy,
            "correct_count": correct,
            "total_count": len(predicted_grades),
            "mean_difference": np.mean(differences),
            "std_difference": np.std(differences)
        }
    
    @staticmethod
    def compare_with_manual(manual_results: Dict, auto_results: Dict) -> Dict:
        """Compare automated results with manual screening"""
        # Compare top candidates overlap
        manual_top = manual_results.get("top_candidates", [])[:10]
        auto_top = auto_results.get("top_candidates", [])[:10]
        
        manual_ids = [c["id"] for c in manual_top]
        auto_ids = [c["id"] for c in auto_top]
        
        overlap = set(manual_ids) & set(auto_ids)
        
        return {
            "manual_count": len(manual_top),
            "auto_count": len(auto_top),
            "overlap_count": len(overlap),
            "overlap_percentage": len(overlap) / len(manual_top) if manual_top else 0,
            "overlap_candidates": list(overlap)
        }
    
    @staticmethod
    def evaluate_time_savings(manual_time_hours: float, auto_time_hours: float) -> Dict:
        """Calculate time savings (as per paper)"""
        speedup = manual_time_hours / auto_time_hours if auto_time_hours > 0 else 0
        time_saved = manual_time_hours - auto_time_hours
        
        return {
            "manual_time_hours": manual_time_hours,
            "auto_time_hours": auto_time_hours,
            "speedup_factor": speedup,
            "time_saved_hours": time_saved,
            "time_saved_percentage": (time_saved / manual_time_hours) * 100 if manual_time_hours > 0 else 0
        }