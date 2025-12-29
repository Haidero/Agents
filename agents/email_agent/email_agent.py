"""
Email Agent for Resume Screening
Checks email, downloads resumes, processes them, and sends responses
"""

import os
import json
import re
import time
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime, timedelta
import base64
import pandas as pd
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EmailAgent:
    """Email agent that checks, downloads, and processes resumes"""
    
    def __init__(self, config_file: str = "email_config.json", screener: Optional[Any] = None, target_position: str = None):
        """
        Initialize email agent with configuration
        
        Args:
            config_file: Path to email configuration file
            screener: Optional Screener instance
            target_position: Optional override for target position
        """
        self.config = self.load_config(config_file)
        
        # Override position if provided
        if target_position:
            self.config["screening"]["target_position"] = target_position
            
        self.processed_emails_file = "processed_emails.json"
        self.processed_emails_file = "processed_emails.json"
        self.processed_emails = self.load_processed_emails()
        
        # Create directories
        # Save directly to main resumes folder so they appear in UI/Scan
        self.attachments_dir = "./resumes" 
        self.results_dir = "./email_results"
        os.makedirs(self.attachments_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Initialize resume processor
        if screener:
            self.screener = screener
            logger.info(f"[INFO] Using injected screener: {type(screener).__name__}")
        else:
            try:
                from core.screener import RealisticResumeScreener
                self.screener = RealisticResumeScreener()
                logger.info("[INFO] Using default RealisticResumeScreener")
            except ImportError:
                import sys
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from core.screener import RealisticResumeScreener
                self.screener = RealisticResumeScreener()
        
        logger.info("[INFO] Email Agent Initialized")
    
    def load_config(self, config_file: str) -> Dict:
        """Load email configuration from JSON file"""
        default_config = {
            "email": {
                "imap_server": "imap.gmail.com",
                "imap_port": 993,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "your_email@gmail.com",
                "password": "your_app_password",  # Use App Password for Gmail
                "folder": "INBOX"
            },
            "screening": {
                "target_position": "software_engineer",
                "minimum_score": 70,
                "check_interval_minutes": 5,
                "automatic_response": True
            },
            "response_templates": {
                "accepted": """
                Dear {candidate_name},
                
                Thank you for your interest in the {position} position at our company.
                
                We have reviewed your resume and are impressed with your qualifications.
                Your application has been shortlisted for the next stage.
                
                We will contact you within 3-5 business days to schedule an interview.
                
                Best regards,
                Recruitment Team
                AI Resume Screening System
                """,
                "rejected": """
                Dear {candidate_name},
                
                Thank you for your interest in the {position} position at our company.
                
                After careful review, we have decided to proceed with other candidates
                whose qualifications more closely match our current needs.
                
                We appreciate your interest and encourage you to apply for future openings.
                
                Best regards,
                Recruitment Team
                AI Resume Screening System
                """,
                "needs_review": """
                Dear {candidate_name},
                
                Thank you for applying for the {position} position.
                
                We have received your application and it is currently under review.
                Our team will get back to you within 5-7 business days.
                
                Best regards,
                Recruitment Team
                AI Resume Screening System
                """
            }
        }
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                # Merge with default config
                default_config.update(user_config)
                logger.info(f"[OK] Loaded config from {config_file}")
        else:
            # Create sample config file
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"[INFO] Created sample config file: {config_file}")
            logger.info("[WARN] Please edit the config file with your email credentials")
        
        return default_config
    
    def load_processed_emails(self) -> List[str]:
        """Load list of already processed email IDs"""
        if os.path.exists(self.processed_emails_file):
            with open(self.processed_emails_file, 'r') as f:
                return json.load(f).get("processed_emails", [])
        return []
    
    def save_processed_email(self, email_id: str):
        """Save processed email ID to avoid duplicates"""
        self.processed_emails.append(email_id)
        data = {
            "processed_emails": self.processed_emails[-1000:],  # Keep last 1000
            "last_updated": datetime.now().isoformat()
        }
        with open(self.processed_emails_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def connect_to_email(self) -> Optional[imaplib.IMAP4_SSL]:
        """Connect to email server"""
        try:
            mail = imaplib.IMAP4_SSL(
                self.config["email"]["imap_server"],
                self.config["email"]["imap_port"]
            )
            mail.login(
                self.config["email"]["username"],
                self.config["email"]["password"]
            )
            mail.select(self.config["email"]["folder"])
            logger.info("[OK] Connected to email server")
            return mail
        except Exception as e:
            logger.error(f"[ERROR] Failed to connect to email: {e}")
            return None
    
    def get_imap_date(self, days_back: int) -> str:
        """Get date string for IMAP search (DD-Mon-YYYY) ensuring English months"""
        date = datetime.now() - timedelta(days=days_back)
        months = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
        }
        return f"{date.day}-{months[date.month]}-{date.year}"

    def check_for_new_resumes(self, days_back: int = 7, ignore_processed: bool = False) -> List[Dict]:
        """
        Check email for new resumes
        Returns list of dictionaries with email info and attachments
        """
        mail = self.connect_to_email()
        if not mail:
            return []
        
        new_resumes = []
        
        try:
            # Search for emails with attachments
            # Search criteria: Emails from last N days
            date_string = self.get_imap_date(days_back)
            
            # Using SINCE to get all emails from that date, not just UNSEEN
            # This allows finding resumes even if emails were read
            search_criteria = f'(SINCE "{date_string}")'
            
            logger.info(f"[INFO] Searching emails since {date_string}")
            status, messages = mail.search(None, search_criteria)
            
            if status != 'OK':
                logger.warning("No new emails found")
                return []
            
            email_ids = messages[0].split()
            logger.info(f"[INFO] Found {len(email_ids)} emails in range")
            
            for email_id in email_ids[-50:]:  # Process last 50 emails (newest first usually)
                email_id_str = email_id.decode()
                
                # Skip if already processed, unless forced
                if not ignore_processed and email_id_str in self.processed_emails:
                    continue
                
                # Fetch the email
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                
                if status != 'OK':
                    continue
                
                # Parse email
                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)
                
                # Extract email details
                subject = self.decode_email_header(email_message['Subject'])
                from_email = self.extract_email_address(email_message['From'])
                sender_name = self.extract_sender_name(email_message['From'])
                
                logger.info(f"[INFO] Processing email: {subject} from {from_email}")
                
                # Check for attachments
                attachments = []
                body = ""
                
                if email_message.is_multipart():
                    for part in email_message.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        
                        # Get email body
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            body = part.get_payload(decode=True).decode(errors='ignore')
                        
                        # Get attachments
                        if "attachment" in content_disposition:
                            filename = part.get_filename()
                            if filename:
                                filename = self.decode_email_header(filename)
                                if self.is_resume_file(filename):
                                    # Save attachment
                                    filepath = self.save_attachment(
                                        part.get_payload(decode=True),
                                        filename,
                                        from_email
                                    )
                                    if filepath:
                                        attachments.append({
                                            "filename": filename,
                                            "filepath": filepath,
                                            "content_type": content_type
                                        })
                else:
                    # Not multipart, just plain text
                    body = email_message.get_payload(decode=True).decode(errors='ignore')
                
                # Extract candidate info from email body
                candidate_info = self.extract_candidate_info(body, from_email, sender_name)
                
                if attachments or "resume" in body.lower() or "cv" in body.lower():
                    new_resumes.append({
                        "email_id": email_id_str,
                        "subject": subject,
                        "from_email": from_email,
                        "sender_name": sender_name,
                        "body": body,
                        "attachments": attachments,
                        "candidate_info": candidate_info,
                        "received_date": datetime.now().isoformat()
                    })
                    
                    # Mark as processed
                    self.save_processed_email(email_id_str)
            
            mail.close()
            mail.logout()
            
            logger.info(f"[OK] Found {len(new_resumes)} emails with resumes")
            return new_resumes
            
        except Exception as e:
            logger.error(f"[ERROR] Error checking email: {e}")
            try:
                mail.close()
                mail.logout()
            except:
                pass
            return []
    
    def decode_email_header(self, header):
        """Decode email header"""
        if header is None:
            return ""
        decoded_parts = decode_header(header)
        decoded_str = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    decoded_str += part.decode(encoding)
                else:
                    decoded_str += part.decode()
            else:
                decoded_str += str(part)
        return decoded_str
    
    def extract_email_address(self, from_header):
        """Extract email address from From header"""
        if not from_header:
            return "unknown@email.com"
        
        # Try to find email pattern
        email_match = re.search(r'<(.+?)>', from_header)
        if email_match:
            return email_match.group(1)
        
        # Try to find email without brackets
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_header)
        if email_match:
            return email_match.group(0)
        
        return from_header
    
    def extract_sender_name(self, from_header):
        """Extract sender name from From header"""
        if not from_header:
            return "Unknown Sender"
        
        # Remove email part
        name = re.sub(r'<.*?>', '', from_header).strip()
        name = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', name).strip()
        
        if name and len(name) > 1:
            # Clean up quotes and extra spaces
            name = name.strip('"\' ')
            return name
        
        # If no name found, use part before @ in email
        email = self.extract_email_address(from_header)
        if '@' in email:
            return email.split('@')[0].replace('.', ' ').title()
        
        return "Unknown Sender"
    
    def is_resume_file(self, filename: str) -> bool:
        """Check if file is a resume (PDF, DOCX, TXT)"""
        if not filename:
            return False
        extensions = ['.pdf', '.docx', '.doc', '.txt', '.rtf']
        filename_lower = filename.lower()
        return any(filename_lower.endswith(ext) for ext in extensions)
    
    def save_attachment(self, file_data: bytes, filename: str, email_address: str) -> Optional[str]:
        """Save email attachment to disk"""
        try:
            # Clean filename
            safe_filename = re.sub(r'[^\w\.-]', '_', filename)
            
            # Add timestamp and email identifier
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            email_hash = abs(hash(email_address)) % 10000
            unique_filename = f"{timestamp}_{email_hash:04d}_{safe_filename}"
            
            filepath = os.path.join(self.attachments_dir, unique_filename)
            
            with open(filepath, 'wb') as f:
                f.write(file_data)
            
            logger.info(f"[INFO] Saved attachment: {unique_filename}")
            return filepath
            
        except Exception as e:
            logger.error(f"[ERROR] Error saving attachment {filename}: {e}")
            return None
    
    def extract_candidate_info(self, email_body: str, email_address: str, sender_name: str) -> Dict:
        """Extract candidate information from email body"""
        info = {
            "name": sender_name,
            "email": email_address,
            "phone": "",
            "position_applied": "",
            "cover_letter": email_body[:1000]  # First 1000 chars
        }
        
        # Try to extract phone number
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b',
            r'\b\d{10}\b'
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, email_body)
            if match:
                info["phone"] = match.group(0)
                break
        
        # Try to extract position applied for
        position_patterns = [
            r'applying for\s+(.+)position',
            r'position\s+of\s+(.+)',
            r'job\s+(.+)application',
            r'role\s+of\s+(.+)'
        ]
        
        for pattern in position_patterns:
            match = re.search(pattern, email_body.lower())
            if match:
                info["position_applied"] = match.group(1).strip().title()
                break
        
        # If no position found, try to infer from subject/common roles
        if not info["position_applied"]:
            common_roles = ["software engineer", "developer", "data scientist", 
                           "devops", "manager", "analyst", "designer"]
            for role in common_roles:
                if role in email_body.lower():
                    info["position_applied"] = role.title()
                    break
        
        return info
    
    def process_resumes(self, email_resumes: List[Dict]) -> List[Dict]:
        """Process downloaded resumes through screening system"""
        results = []
        
        for email_data in email_resumes:
            candidate_id = f"{email_data['from_email']}_{datetime.now().strftime('%Y%m%d')}"
            
            # Check if there are attachments
            if not email_data["attachments"]:
                logger.warning(f"[WARN] Email from {email_data['from_email']} has no attachments. Skipping.")
                continue

            # Process each attachment
            for attachment in email_data["attachments"]:
                try:
                    # Read the file
                    filepath = attachment["filepath"]
                    
                    # Parse resume text
                    text = self.read_resume_file(filepath)
                    
                    if not text:
                        continue
                    
                    # Determine position to screen for
                    target_position = self.config["screening"]["target_position"]
                    if email_data["candidate_info"]["position_applied"]:
                        # Map common position names to our position types
                        position_lower = email_data["candidate_info"]["position_applied"].lower()
                        if any(word in position_lower for word in ["software", "developer", "engineer"]):
                            target_position = "software_engineer"
                        elif any(word in position_lower for word in ["data", "scientist", "analyst", "machine"]):
                            target_position = "data_scientist"
                        elif "devops" in position_lower:
                            target_position = "devops"
                        elif "full" in position_lower:
                            target_position = "full_stack"
                    
                    # Grade the resume
                    grade, skills = self.screener.grade_resume(text, target_position)
                    
                    # Extract experience
                    years_exp = self.screener.extract_experience(text)
                    
                    # Calculate position match
                    position_match = self.screener.calculate_position_match(skills, target_position)
                    
                    # Determine status
                    min_score = self.config["screening"]["minimum_score"]
                    if grade >= min_score + 10:
                        status = "Accepted"
                        response_template = "accepted"
                    elif grade >= min_score:
                        status = "Needs Review"
                        response_template = "needs_review"
                    else:
                        status = "Rejected"
                        response_template = "rejected"
                    
                    # Create result
                    result = {
                        "candidate_id": candidate_id,
                        "email_data": {
                            "from": email_data["from_email"],
                            "subject": email_data["subject"],
                            "sender_name": email_data["sender_name"]
                        },
                        "resume_info": {
                            "filename": attachment["filename"],
                            "filepath": filepath,
                            "target_position": target_position
                        },
                        "screening_results": {
                            "score": grade,
                            "status": status,
                            "skills": skills[:10],
                            "experience_years": years_exp,
                            "position_match": position_match,
                            "screened_date": datetime.now().isoformat()
                        },
                        "response_info": {
                            "template": response_template,
                            "sent": False,
                            "scheduled": False
                        }
                    }
                    
                    results.append(result)
                    logger.info(f"[INFO] Screened: {email_data['sender_name']} - Score: {grade}/100 - Status: {status}")
                    
                except Exception as e:
                    logger.error(f"[ERROR] Error processing resume {attachment['filename']}: {e}")
        
        return results
    
    def read_resume_file(self, filepath: str) -> str:
        """Read resume file based on extension"""
        try:
            if filepath.endswith('.pdf'):
                import pdfplumber
                with pdfplumber.open(filepath) as pdf:
                    text = "\n".join([page.extract_text() or "" for page in pdf.pages])
            elif filepath.endswith('.docx'):
                from docx import Document
                doc = Document(filepath)
                text = "\n".join([para.text for para in doc.paragraphs])
            elif filepath.endswith('.txt'):
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            else:
                logger.warning(f"[WARN] Unsupported file type: {filepath}")
                return ""
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"[ERROR] Error reading file {filepath}: {e}")
            return ""
    
    def send_email_response(self, result: Dict) -> bool:
        """Send email response to candidate"""
        try:
            # Get response template
            template_key = result["response_info"]["template"]
            template = self.config["response_templates"][template_key]
            
            # Prepare email
            msg = MIMEMultipart()
            msg['From'] = self.config["email"]["username"]
            msg['To'] = result["email_data"]["from"]
            msg['Subject'] = f"Application Update: {result['email_data']['subject']}"
            
            # Format message
            candidate_name = result["email_data"]["sender_name"]
            position = result["resume_info"]["target_position"].replace("_", " ").title()
            
            message = template.format(
                candidate_name=candidate_name,
                position=position,
                score=result["screening_results"]["score"]
            )
            
            msg.attach(MIMEText(message, 'plain'))
            
            # Connect to SMTP server
            with smtplib.SMTP(
                self.config["email"]["smtp_server"],
                self.config["email"]["smtp_port"]
            ) as server:
                server.starttls()
                server.login(
                    self.config["email"]["username"],
                    self.config["email"]["password"]
                )
                server.send_message(msg)
            
            logger.info(f"[INFO] Sent response to: {result['email_data']['from']}")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Error sending email to {result['email_data']['from']}: {e}")
            return False
    
    def save_results(self, results: List[Dict]):
        """Save screening results to file"""
        if not results:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed JSON
        json_file = os.path.join(self.results_dir, f"email_results_{timestamp}.json")
        with open(json_file, 'w') as f:
            json.dump({
                "screening_date": datetime.now().isoformat(),
                "total_candidates": len(results),
                "results": results
            }, f, indent=2)
        
        # Save CSV summary
        csv_data = []
        for result in results:
            csv_data.append({
                "Candidate ID": result["candidate_id"],
                "Name": result["email_data"]["sender_name"],
                "Email": result["email_data"]["from"],
                "Position": result["resume_info"]["target_position"],
                "Score": result["screening_results"]["score"],
                "Status": result["screening_results"]["status"],
                "Experience": result["screening_results"]["experience_years"],
                "Skills Match": result["screening_results"]["position_match"],
                "Response Sent": result["response_info"]["sent"],
                "Date": result["screening_results"]["screened_date"]
            })
        
        if csv_data:
            df = pd.DataFrame(csv_data)
            csv_file = os.path.join(self.results_dir, f"email_summary_{timestamp}.csv")
            df.to_csv(csv_file, index=False)
        
        logger.info(f"[INFO] Saved results: {json_file}")
    
    def run_once(self, send_responses: bool = True, days_back: int = 7, ignore_processed: bool = False) -> Dict:
        """
        Run one complete cycle:
        1. Check email for new resumes
        2. Download and process them
        3. Send responses (optional)
        
        Returns summary of the run
        """
        logger.info(f"[INFO] Starting email screening cycle (looking back {days_back} days, re-scanning: {ignore_processed})")
        
        # Step 1: Check for new resumes
        new_resumes = self.check_for_new_resumes(days_back=days_back, ignore_processed=ignore_processed)
        
        if not new_resumes:
            logger.info("[INFO] No new resumes found")
            return {"status": "no_new_resumes"}
        
        # Step 2: Process resumes
        results = self.process_resumes(new_resumes)
        
        if not results:
            logger.info("[INFO] No valid resumes processed")
            return {"status": "no_valid_resumes"}
        
        # Step 3: Send responses if enabled
        responses_sent = 0
        if send_responses and self.config["screening"]["automatic_response"]:
            for result in results:
                if self.send_email_response(result):
                    result["response_info"]["sent"] = True
                    responses_sent += 1
        
        # Step 4: Save results
        self.save_results(results)
        
        # Generate summary
        summary = {
            "status": "completed",
            "total_emails": len(new_resumes),
            "total_resumes": len(results),
            "responses_sent": responses_sent,
            "accepted": len([r for r in results if r["screening_results"]["status"] == "Accepted"]),
            "needs_review": len([r for r in results if r["screening_results"]["status"] == "Needs Review"]),
            "rejected": len([r for r in results if r["screening_results"]["status"] == "Rejected"]),
            "average_score": sum(r["screening_results"]["score"] for r in results) / len(results),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"""
        [OK] Screening Cycle Complete:
           • Emails processed: {summary['total_emails']}
           • Resumes screened: {summary['total_resumes']}
           • Accepted: {summary['accepted']}
           • Needs Review: {summary['needs_review']}
           • Rejected: {summary['rejected']}
           • Average Score: {summary['average_score']:.1f}/100
           • Responses Sent: {summary['responses_sent']}
        """)
        
        return summary
    
    def run_continuously(self, interval_minutes: int = None):
        """
        Run email screening continuously at specified intervals
        
        Args:
            interval_minutes: Minutes between checks (uses config if None)
        """
        if interval_minutes is None:
            interval_minutes = self.config["screening"]["check_interval_minutes"]
        
        logger.info(f"[INFO] Starting continuous email screening (interval: {interval_minutes} minutes)")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                summary = self.run_once()
                
                # Log summary
                if summary["status"] == "completed":
                    logger.info(f"[INFO] Next check in {interval_minutes} minutes...")
                
                # Wait for next check
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            logger.info("[INFO] Stopped by user")
        except Exception as e:
            logger.error(f"[ERROR] Error in continuous run: {e}")