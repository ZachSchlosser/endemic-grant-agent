#!/usr/bin/env python3
"""
Grant Verifier - Claude Code Hook
Validates grant entries for accuracy before database operations
Prevents inaccurate grant names, non-existent programs, and expired deadlines
"""

import sys
import json
import requests
import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin
import argparse

# Add utils directory to path for logger
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
try:
    from utils.logger import GrantAgentLogger
    LOGGER_AVAILABLE = True
except ImportError:
    LOGGER_AVAILABLE = False

class GrantVerificationResult:
    """Result of grant verification with specific issues found"""
    
    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
        self.suggestions = []
    
    def add_error(self, message: str):
        self.is_valid = False
        self.errors.append(message)
    
    def add_warning(self, message: str):
        self.warnings.append(message)
    
    def add_suggestion(self, message: str):
        self.suggestions.append(message)
    
    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions
        }

class GrantVerifier:
    """Verifies grant accuracy against known patterns and official sources"""
    
    def __init__(self, config_path: str = None):
        """Initialize verifier with centralized configuration"""
        
        # Initialize logging if available
        if LOGGER_AVAILABLE:
            self.logger = GrantAgentLogger().get_logger("grant_verifier")
        else:
            self.logger = None
        
        # Load configuration from JSON
        if not config_path:
            config_path = os.path.join(os.path.dirname(__file__), 'config', 'foundation_seeds.json')
        
        self.config = self._load_config(config_path)
        
        # Extract configuration components
        self.known_funders = self.config.get('foundation_seeds', {})
        self.validation_rules = self.config.get('validation_rules', {})
        self.red_flag_patterns = self.validation_rules.get('red_flag_patterns', [])
        self.deadline_config = self.validation_rules.get('deadline_validation', {})
        
        if self.logger:
            self.logger.info(f"GrantVerifier initialized with {len(self.known_funders)} known funders")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file with fallback"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            if self.logger:
                self.logger.info(f"Loaded configuration from {config_path}")
            
            return config
            
        except FileNotFoundError:
            error_msg = f"Configuration file not found: {config_path}"
            if self.logger:
                self.logger.error(error_msg)
            else:
                print(f"ERROR: {error_msg}")
            
            # Return minimal fallback configuration
            return {
                'foundation_seeds': {},
                'validation_rules': {
                    'required_fields': ['organization_name', 'grant_name'],
                    'red_flag_patterns': [],
                    'deadline_validation': {
                        'supported_formats': ['%Y-%m-%d'],
                        'warning_days_threshold': 7
                    }
                }
            }
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in configuration file: {e}"
            if self.logger:
                self.logger.error(error_msg)
            else:
                print(f"ERROR: {error_msg}")
            
            # Return minimal fallback configuration
            return {
                'foundation_seeds': {},
                'validation_rules': {
                    'required_fields': ['organization_name', 'grant_name'],
                    'red_flag_patterns': [],
                    'deadline_validation': {
                        'supported_formats': ['%Y-%m-%d'],
                        'warning_days_threshold': 7
                    }
                }
            }
        
        except Exception as e:
            error_msg = f"Error loading configuration: {e}"
            if self.logger:
                self.logger.error(error_msg)
            else:
                print(f"ERROR: {error_msg}")
            
            return {
                'foundation_seeds': {},
                'validation_rules': {
                    'required_fields': ['organization_name', 'grant_name'],
                    'red_flag_patterns': [],
                    'deadline_validation': {
                        'supported_formats': ['%Y-%m-%d'],
                        'warning_days_threshold': 7
                    }
                }
            }
    
    def reload_config(self, config_path: str = None) -> bool:
        """Reload configuration from JSON file"""
        if not config_path:
            config_path = os.path.join(os.path.dirname(__file__), 'config', 'foundation_seeds.json')
        
        try:
            old_funder_count = len(self.known_funders)
            self.config = self._load_config(config_path)
            
            # Re-extract configuration components
            self.known_funders = self.config.get('foundation_seeds', {})
            self.validation_rules = self.config.get('validation_rules', {})
            self.red_flag_patterns = self.validation_rules.get('red_flag_patterns', [])
            self.deadline_config = self.validation_rules.get('deadline_validation', {})
            
            if self.logger:
                self.logger.info(f"Configuration reloaded: {old_funder_count} -> {len(self.known_funders)} funders")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to reload configuration: {e}")
            return False
    
    def get_config_summary(self) -> Dict:
        """Get summary of current configuration"""
        return {
            'total_funders': len(self.known_funders),
            'funders': list(self.known_funders.keys()),
            'red_flag_patterns_count': len(self.red_flag_patterns),
            'required_fields': self.validation_rules.get('required_fields', []),
            'deadline_formats_supported': len(self.deadline_config.get('supported_formats', [])),
            'config_loaded': bool(self.config)
        }
    
    def verify_grant_entry(self, grant_data: Dict) -> GrantVerificationResult:
        """Main verification method for grant entries"""
        result = GrantVerificationResult()
        
        if self.logger:
            self.logger.debug("Starting grant verification")
        
        # Handle None or invalid input
        if grant_data is None:
            result.add_error("Grant data cannot be None")
            return result
        
        if not isinstance(grant_data, dict):
            result.add_error("Grant data must be a dictionary")
            return result
        
        # 1. Verify required fields are present
        self._verify_required_fields(grant_data, result)
        if not result.is_valid:
            return result
        
        # Extract grant information
        org_name = grant_data.get("organization_name", "")
        grant_name = grant_data.get("grant_name", "")
        grant_url = grant_data.get("grant_link", "")
        deadline = grant_data.get("deadline", "")
        
        # 2. Verify organization exists and is known
        self._verify_organization(org_name, result)
        
        # 3. Verify grant name against known programs
        self._verify_grant_name(org_name, grant_name, result)
        
        # 4. Verify grant URL is valid and accessible
        if grant_url:
            self._verify_grant_url(org_name, grant_url, result)
        
        # 5. Check for red flag patterns
        self._check_red_flags(grant_name, result)
        
        # 6. Verify deadline is not in the past
        if deadline:
            self._verify_deadline(deadline, result)
        
        # 7. Additional field validations
        self._verify_optional_fields(grant_data, result)
        
        if self.logger:
            self.logger.debug(f"Grant verification completed: {result.is_valid}")
        
        return result
    
    def _verify_required_fields(self, grant_data: Dict, result: GrantVerificationResult):
        """Verify required fields are present and non-empty"""
        required_fields = self.validation_rules.get('required_fields', ['organization_name', 'grant_name'])
        
        missing_fields = []
        for field in required_fields:
            if not grant_data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            result.add_error(f"Missing required fields: {', '.join(missing_fields)}")
    
    def _verify_optional_fields(self, grant_data: Dict, result: GrantVerificationResult):
        """Verify optional fields meet validation rules"""
        # Check description length if present
        description = grant_data.get("description", "")
        if description:
            min_length = self.validation_rules.get('minimum_description_length', 0)
            max_length = self.validation_rules.get('maximum_description_length', 10000)
            
            if len(description) < min_length:
                result.add_warning(f"Description is too short ({len(description)} chars, minimum {min_length})")
            elif len(description) > max_length:
                result.add_warning(f"Description is too long ({len(description)} chars, maximum {max_length})")
    
    def _verify_organization(self, org_name: str, result: GrantVerificationResult):
        """Verify organization name against known funders"""
        if org_name not in self.known_funders:
            result.add_warning(f"Organization '{org_name}' not in verified funder database")
            result.add_suggestion(f"Consider using one of: {list(self.known_funders.keys())}")
        
    def _verify_grant_name(self, org_name: str, grant_name: str, result: GrantVerificationResult):
        """Verify grant name against known programs for the organization"""
        if org_name in self.known_funders:
            known_programs = self.known_funders[org_name]["known_programs"]
            
            # Exact match
            if grant_name in known_programs:
                return
            
            # Partial match
            partial_matches = [p for p in known_programs if grant_name.lower() in p.lower() or p.lower() in grant_name.lower()]
            if partial_matches:
                result.add_warning(f"Grant name '{grant_name}' may be imprecise")
                result.add_suggestion(f"Consider exact name: {partial_matches[0]}")
                return
            
            # No match found
            result.add_error(f"Grant '{grant_name}' not found in {org_name}'s known programs")
            result.add_suggestion(f"Known {org_name} programs: {', '.join(known_programs)}")
    
    def _verify_grant_url(self, org_name: str, grant_url: str, result: GrantVerificationResult):
        """Verify grant URL is from correct domain and accessible"""
        try:
            parsed_url = urlparse(grant_url)
            domain = parsed_url.netloc.lower().replace("www.", "")
            
            # Check domain matches known funder domains
            if org_name in self.known_funders:
                expected_domains = self.known_funders[org_name]["base_urls"]
                if not any(domain.endswith(expected) for expected in expected_domains):
                    result.add_error(f"URL domain '{domain}' doesn't match {org_name} expected domains: {expected_domains}")
            
            # Check URL is accessible (with timeout)
            response = requests.head(grant_url, timeout=10, allow_redirects=True)
            if response.status_code >= 400:
                result.add_error(f"Grant URL returns {response.status_code} error")
            elif response.status_code >= 300:
                result.add_warning(f"Grant URL redirects (status: {response.status_code})")
            
        except requests.RequestException as e:
            result.add_error(f"Cannot access grant URL: {str(e)}")
        except Exception as e:
            result.add_warning(f"URL validation error: {str(e)}")
    
    def _check_red_flags(self, grant_name: str, result: GrantVerificationResult):
        """Check for patterns that indicate made-up grant names"""
        grant_lower = grant_name.lower()
        for pattern in self.red_flag_patterns:
            if re.search(pattern, grant_lower):
                result.add_error(f"Grant name matches red flag pattern: '{pattern}'")
                result.add_suggestion("Use exact program names from official sources only")
    
    def _verify_deadline(self, deadline: str, result: GrantVerificationResult):
        """Verify deadline is not in the past using configured date formats"""
        try:
            # Get supported date formats from configuration
            supported_formats = self.deadline_config.get('supported_formats', ['%Y-%m-%d'])
            warning_threshold = self.deadline_config.get('warning_days_threshold', 7)
            
            # Parse various date formats
            for date_format in supported_formats:
                try:
                    deadline_date = datetime.strptime(deadline, date_format)
                    break
                except ValueError:
                    continue
            else:
                result.add_warning(f"Cannot parse deadline format: {deadline}")
                result.add_suggestion(f"Supported formats: {', '.join(supported_formats)}")
                return
            
            if deadline_date < datetime.now():
                result.add_error(f"Deadline {deadline} is in the past")
            elif deadline_date < datetime.now() + timedelta(days=warning_threshold):
                result.add_warning(f"Deadline {deadline} is very soon (less than {warning_threshold} days)")
                
        except Exception as e:
            result.add_warning(f"Deadline validation error: {str(e)}")

def validate_grant_from_json(json_file: str) -> GrantVerificationResult:
    """Validate grant from JSON file"""
    try:
        with open(json_file, 'r') as f:
            grant_data = json.load(f)
        
        verifier = GrantVerifier()
        return verifier.verify_grant_entry(grant_data)
        
    except Exception as e:
        result = GrantVerificationResult()
        result.add_error(f"Error reading grant file: {str(e)}")
        return result

def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(description="Verify grant entry accuracy")
    parser.add_argument("--grant-file", help="JSON file containing grant data")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--quiet", action="store_true", help="Suppress output except errors")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--show-config", action="store_true", help="Show configuration summary")
    
    args = parser.parse_args()
    
    # Initialize verifier with specified config
    verifier = GrantVerifier(config_path=args.config)
    
    # Show configuration if requested
    if args.show_config:
        if not args.quiet:
            print("GRANT VERIFIER CONFIGURATION:")
            print("="*50)
            
            config_summary = verifier.get_config_summary()
            for key, value in config_summary.items():
                if isinstance(value, list) and len(value) > 5:
                    print(f"  {key}: {len(value)} items ({value[:3]}...)")
                else:
                    print(f"  {key}: {value}")
            
            print()
        
        if not args.grant_file:
            return
    
    # Validate grant file if provided
    if not args.grant_file:
        print("ERROR: --grant-file is required unless using --show-config only")
        sys.exit(1)
    
    result = validate_grant_from_json(args.grant_file)
    
    if not args.quiet:
        print("GRANT VERIFIER RESULTS:")
        print("="*50)
        
        if result.errors:
            print("❌ ERRORS:")
            for error in result.errors:
                print(f"  • {error}")
        
        if result.warnings:
            print("⚠️  WARNINGS:")
            for warning in result.warnings:
                print(f"  • {warning}")
        
        if result.suggestions:
            print("💡 SUGGESTIONS:")
            for suggestion in result.suggestions:
                print(f"  • {suggestion}")
        
        print(f"\n✅ Valid: {result.is_valid}")
    
    # Exit with error code if validation failed
    if not result.is_valid or (args.strict and result.warnings):
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()