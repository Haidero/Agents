import json
import heapq
from typing import List, Dict, Any, Optional
from datetime import datetime

class DecisionMakerAgent:
    """Agent for making final hiring decisions (as per paper)"""
    
    def __init__(self, config):
        self.config = config
        self.top_n = config.top_n_candidates
        self.decision_criteria = config.decision_criteria or {}
        
    def _create_decision_prompt(self, candidates: List[Dict], criteria: Dict = None) -> str:
        """Create prompt for decision making"""
        
        candidates_info = ""
        for i, candidate in enumerate(candidates):
            candidates_info += f"\nCandidate {i+1} (ID: {candidate.get('id', i)}):\n"
            candidates_info += f"Grade: {candidate.get('grade', 'N/A')}/100\n"
            candidates_info += f"Summary: {candidate.get('summary', 'No summary')}\n"
        
        criteria_text = ""
        if criteria:
            criteria_text = "\nAdditional Requirements:\n"
            for key, value in criteria.items():
                criteria_text += f"- {key}: {value}\n"
        
        return f"""You are the CEO of a technology company. Your task is to select the best candidate(s) for the open position.

You have reviewed {len(candidates)} top candidates. Here is their information:
{candidates_info}
{criteria_text}

Based on the grades and summaries, please:
1. Select the top candidate(s) (specify how many if needed)
2. Provide the ID(s) of your selection
3. Explain your reasoning for each selection

Format your response as:
Selection: [Candidate ID(s)]
Reasoning: [Your detailed reasoning]

Begin your decision:"""
    
    def select_top_candidates(self, graded_resumes: List[Dict], n: Optional[int] = None) -> List[Dict]:
        """Select top N candidates by grade"""
        if n is None:
            n = self.top_n
        
        # Filter resumes with valid grades
        valid_resumes = [
            r for r in graded_resumes 
            if r.get("grading_result", {}).get("grade") is not None
        ]
        
        # Sort by grade (descending)
        sorted_resumes = sorted(
            valid_resumes,
            key=lambda x: x["grading_result"]["grade"],
            reverse=True
        )
        
        return sorted_resumes[:n]
    
    def make_decision(self, candidates: List[Dict], criteria: Dict = None) -> Dict:
        """Make a decision using LLM (or simple ranking)"""
        
        # Simple method: just return top N
        if not self.config.get("use_llm_for_decision", True):
            selected = candidates[:1] if len(candidates) > 0 else []
            return {
                "method": "simple_ranking",
                "selected_candidates": [
                    {
                        "id": i,
                        "grade": c["grading_result"]["grade"],
                        "summary": c["grading_result"]["summary"]
                    }
                    for i, c in enumerate(selected)
                ],
                "reasoning": f"Selected top candidate by grade: {selected[0]['grading_result']['grade']}/100"
            }
        
        # LLM-based decision
        if self.config.use_gpt:
            return self._make_gpt_decision(candidates, criteria)
        else:
            return self._make_local_decision(candidates, criteria)
    
    def _make_gpt_decision(self, candidates: List[Dict], criteria: Dict = None) -> Dict:
        """Make decision using GPT"""
        try:
            import openai
            
            prompt = self._create_decision_prompt(candidates, criteria)
            
            response = openai.ChatCompletion.create(
                model=self.config.gpt_model,
                messages=[
                    {"role": "system", "content": "You are a decisive CEO making hiring decisions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )
            
            decision_text = response.choices[0].message.content
            
            # Parse response
            return self._parse_decision_response(decision_text, candidates)
            
        except Exception as e:
            print(f"Error in GPT decision: {e}")
            return self._make_local_decision(candidates, criteria)
    
    def _make_local_decision(self, candidates: List[Dict], criteria: Dict = None) -> Dict:
        """Make decision using local model (simplified)"""
        if len(candidates) == 0:
            return {"error": "No candidates to evaluate"}
        
        # Simple heuristic: highest grade + has keywords
        selected = candidates[0]
        
        reasoning = f"Selected candidate with highest grade ({selected['grading_result']['grade']}/100). "
        
        if criteria and 'keywords' in criteria:
            keywords = criteria['keywords']
            summary = selected['grading_result']['summary'].lower()
            matched = [k for k in keywords if k.lower() in summary]
            if matched:
                reasoning += f"Keywords matched: {', '.join(matched)}."
        
        return {
            "method": "local_heuristic",
            "selected_candidate": {
                "id": 0,
                "grade": selected["grading_result"]["grade"],
                "summary": selected["grading_result"]["summary"]
            },
            "reasoning": reasoning
        }
    
    def _parse_decision_response(self, response: str, candidates: List[Dict]) -> Dict:
        """Parse decision response from LLM"""
        import re
        
        # Extract selection IDs
        id_match = re.search(r'Selection:\s*\[?(.+?)\]?', response, re.IGNORECASE)
        selected_ids = []
        
        if id_match:
            ids_text = id_match.group(1)
            # Parse IDs (could be "1, 3, 5" or "1-3")
            for part in ids_text.split(','):
                part = part.strip()
                if '-' in part:
                    try:
                        start, end = map(int, part.split('-'))
                        selected_ids.extend(range(start, end + 1))
                    except:
                        pass
                else:
                    try:
                        selected_ids.append(int(part))
                    except:
                        pass
        
        # Extract reasoning
        reasoning_match = re.search(r'Reasoning:\s*(.+?)(?:\n\n|\Z)', response, re.IGNORECASE | re.DOTALL)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided."
        
        # Get selected candidates
        selected_candidates = []
        for idx in selected_ids:
            if 0 <= idx - 1 < len(candidates):
                candidate = candidates[idx - 1]  # Convert to 0-index
                selected_candidates.append({
                    "id": idx,
                    "grade": candidate["grading_result"]["grade"],
                    "summary": candidate["grading_result"]["summary"]
                })
        
        return {
            "method": "llm_decision",
            "selected_candidates": selected_candidates,
            "reasoning": reasoning,
            "full_response": response
        }
    
    def generate_report(self, all_resumes: List[Dict], selected: Dict) -> Dict:
        """Generate a comprehensive report"""
        
        stats = {
            "total_resumes": len(all_resumes),
            "valid_grades": len([r for r in all_resumes if r.get("grading_result", {}).get("grade")]),
            "average_grade": 0,
            "top_grade": 0,
            "processing_time": datetime.now().isoformat()
        }
        
        # Calculate statistics
        grades = [r["grading_result"]["grade"] for r in all_resumes 
                 if r.get("grading_result", {}).get("grade")]
        
        if grades:
            stats["average_grade"] = sum(grades) / len(grades)
            stats["top_grade"] = max(grades)
        
        return {
            "summary": {
                "decision_method": selected.get("method", "unknown"),
                "num_selected": len(selected.get("selected_candidates", [])),
                "selection_ids": [c["id"] for c in selected.get("selected_candidates", [])]
            },
            "statistics": stats,
            "selection_details": selected,
            "candidate_ranking": [
                {
                    "rank": i + 1,
                    "id": i,
                    "grade": r["grading_result"]["grade"],
                    "summary_preview": r["grading_result"]["summary"][:100] + "..."
                }
                for i, r in enumerate(all_resumes[:10])  # Top 10
            ]
        }