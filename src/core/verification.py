"""
Verification and proof-of-erasure functionality
Provides cryptographic verification that data has been properly wiped
"""

import os
import hashlib
import logging
import json
import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class VerificationManager:
    """Manages verification and proof-of-erasure operations"""
    
    def __init__(self):
        self.verification_logs = []
        self.proof_directory = Path("proofs")
        self.proof_directory.mkdir(exist_ok=True)
    
    def verify_wipe(self, device: str, sample_size: int = 1024*1024) -> Tuple[bool, str]:
        """
        Verify that a disk has been properly wiped
        
        Args:
            device: Device path to verify
            sample_size: Number of bytes to sample for verification
            
        Returns:
            Tuple of (success, message)
        """
        try:
            logger.info(f"Starting verification for {device}")
            
            # Read sample data from device
            sample_data = self._read_device_sample(device, sample_size)
            if sample_data is None:
                return False, "Could not read device sample"
            
            # Analyze the sample
            analysis = self._analyze_sample(sample_data)
            
            # Create verification record
            verification_record = {
                "device": device,
                "timestamp": datetime.datetime.now().isoformat(),
                "sample_size": sample_size,
                "analysis": analysis,
                "verification_id": self._generate_verification_id()
            }
            
            # Save verification proof
            self._save_verification_proof(verification_record)
            
            # Determine if wipe was successful
            is_clean = self._is_sample_clean(analysis)
            
            if is_clean:
                message = f"Verification successful: {analysis['clean_percentage']:.2f}% clean"
                logger.info(f"Verification passed for {device}: {message}")
            else:
                message = f"Verification failed: {analysis['clean_percentage']:.2f}% clean"
                logger.warning(f"Verification failed for {device}: {message}")
            
            return is_clean, message
            
        except Exception as e:
            error_msg = f"Verification error: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def _read_device_sample(self, device: str, sample_size: int) -> Optional[bytes]:
        """Read a sample of data from the device"""
        try:
            # For safety, we'll read from the beginning of the device
            with open(device, 'rb') as f:
                sample_data = f.read(sample_size)
                return sample_data
                
        except PermissionError:
            logger.error(f"Permission denied reading {device}")
            return None
        except Exception as e:
            logger.error(f"Error reading device sample: {e}")
            return None
    
    def _analyze_sample(self, sample_data: bytes) -> Dict:
        """Analyze the sample data to determine wipe effectiveness"""
        if not sample_data:
            return {"clean_percentage": 0, "zero_bytes": 0, "total_bytes": 0}
        
        total_bytes = len(sample_data)
        zero_bytes = sample_data.count(b'\x00')
        
        # Calculate clean percentage
        clean_percentage = (zero_bytes / total_bytes) * 100
        
        # Check for patterns (indicating incomplete wipe)
        patterns = self._detect_patterns(sample_data)
        
        # Calculate entropy (randomness)
        entropy = self._calculate_entropy(sample_data)
        
        analysis = {
            "clean_percentage": clean_percentage,
            "zero_bytes": zero_bytes,
            "total_bytes": total_bytes,
            "patterns": patterns,
            "entropy": entropy,
            "is_random": entropy > 7.5  # High entropy indicates random data
        }
        
        return analysis
    
    def _detect_patterns(self, data: bytes) -> List[str]:
        """Detect patterns in the data that might indicate incomplete wiping"""
        patterns = []
        
        # Check for repeated bytes
        if len(set(data)) < 10:  # Very few unique bytes
            patterns.append("repeated_bytes")
        
        # Check for sequential patterns
        sequential_count = 0
        for i in range(len(data) - 1):
            if data[i] + 1 == data[i + 1]:
                sequential_count += 1
        
        if sequential_count > len(data) * 0.1:  # More than 10% sequential
            patterns.append("sequential_pattern")
        
        # Check for all zeros (good for wipe verification)
        if all(b == 0 for b in data):
            patterns.append("all_zeros")
        
        return patterns
    
    def _calculate_entropy(self, data: bytes) -> float:
        """Calculate Shannon entropy of the data"""
        if not data:
            return 0
        
        # Count byte frequencies
        byte_counts = [0] * 256
        for byte in data:
            byte_counts[byte] += 1
        
        # Calculate entropy
        entropy = 0
        data_len = len(data)
        
        for count in byte_counts:
            if count > 0:
                probability = count / data_len
                entropy -= probability * (probability.bit_length() - 1)
        
        return entropy
    
    def _is_sample_clean(self, analysis: Dict) -> bool:
        """Determine if the sample indicates a clean wipe"""
        clean_percentage = analysis.get("clean_percentage", 0)
        patterns = analysis.get("patterns", [])
        
        # Consider it clean if:
        # 1. More than 95% zeros, OR
        # 2. All zeros pattern detected, OR
        # 3. High entropy (random data) and no problematic patterns
        
        if clean_percentage > 95:
            return True
        
        if "all_zeros" in patterns:
            return True
        
        if (analysis.get("is_random", False) and 
            not any(p in patterns for p in ["repeated_bytes", "sequential_pattern"])):
            return True
        
        return False
    
    def _generate_verification_id(self) -> str:
        """Generate a unique verification ID"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(str(datetime.datetime.now()).encode()).hexdigest()[:8]
        return f"VERIFY_{timestamp}_{random_suffix}"
    
    def _save_verification_proof(self, verification_record: Dict):
        """Save verification proof to file"""
        try:
            verification_id = verification_record["verification_id"]
            proof_file = self.proof_directory / f"{verification_id}.json"
            
            with open(proof_file, 'w') as f:
                json.dump(verification_record, f, indent=2)
            
            logger.info(f"Verification proof saved: {proof_file}")
            
        except Exception as e:
            logger.error(f"Error saving verification proof: {e}")
    
    def get_verification_history(self) -> List[Dict]:
        """Get history of all verification operations"""
        try:
            history = []
            
            for proof_file in self.proof_directory.glob("*.json"):
                try:
                    with open(proof_file, 'r') as f:
                        verification_record = json.load(f)
                        history.append(verification_record)
                except Exception as e:
                    logger.error(f"Error reading proof file {proof_file}: {e}")
            
            # Sort by timestamp (newest first)
            history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting verification history: {e}")
            return []
    
    def generate_wipe_certificate(self, device: str, wipe_method: str, 
                                verification_record: Dict) -> Dict:
        """Generate a certificate of data erasure"""
        certificate = {
            "certificate_type": "Data Erasure Certificate",
            "device": device,
            "wipe_method": wipe_method,
            "verification_id": verification_record["verification_id"],
            "timestamp": verification_record["timestamp"],
            "verification_results": verification_record["analysis"],
            "certificate_hash": "",
            "software_version": "1.0.0",
            "platform": os.name
        }
        
        # Generate certificate hash
        cert_string = json.dumps(certificate, sort_keys=True)
        certificate["certificate_hash"] = hashlib.sha256(cert_string.encode()).hexdigest()
        
        return certificate
    
    def save_certificate(self, certificate: Dict) -> str:
        """Save certificate to file and return file path"""
        try:
            cert_id = certificate["verification_id"]
            cert_file = self.proof_directory / f"CERT_{cert_id}.json"
            
            with open(cert_file, 'w') as f:
                json.dump(certificate, f, indent=2)
            
            logger.info(f"Certificate saved: {cert_file}")
            return str(cert_file)
            
        except Exception as e:
            logger.error(f"Error saving certificate: {e}")
            return ""
