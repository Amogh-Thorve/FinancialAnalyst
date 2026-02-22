"""
Financial Metrics Validator
Validates AI-extracted metrics against calculated values from raw data
"""

import re
from typing import Dict, Any, Optional, Tuple


class MetricsValidator:
    """Validates financial metrics by comparing AI estimates with calculated values"""
    
    def __init__(self, pdf_text: str):
        self.pdf_text = pdf_text.lower()
        self.validation_results = {}
    
    def extract_number(self, pattern: str, context_window: int = 200) -> Optional[float]:
        """Extract a number near a specific keyword/pattern"""
        try:
            # Find all occurrences of the pattern
            matches = list(re.finditer(pattern, self.pdf_text, re.IGNORECASE))
            
            for match in matches:
                start = max(0, match.start() - context_window)
                end = min(len(self.pdf_text), match.end() + context_window)
                context = self.pdf_text[start:end]
                
                # Look for numbers near the pattern
                # Match patterns like: 123.45, $123.45, (123.45), 123,456.78
                number_patterns = [
                    r'[\$\(]?\s*([\d,]+\.?\d*)\s*[%\)]?',  # Handle $, (, ), %
                ]
                
                for num_pattern in number_patterns:
                    # Use finditer to check for currency symbols in the full match
                    iterator = re.finditer(num_pattern, context)
                    for match in iterator:
                        full_match = match.group(0)
                        num_str = match.group(1).replace(',', '')
                        
                        try:
                            val = float(num_str)
                            
                            # Heuristic: Ignore likely years (e.g. 2023, 2024) if they don't have a currency symbol
                            # Check if integer and within reasonable year range
                            if 1990 <= val <= 2030 and val.is_integer():
                                if '$' not in full_match and '£' not in full_match and '€' not in full_match:
                                    # Skip this number, it's likely a year
                                    continue
                                    
                            return val
                        except ValueError:
                            continue
            
            return None
        except Exception as e:
            print(f"Error extracting number for pattern '{pattern}': {e}")
            return None
    
    def calculate_eps(self) -> Tuple[Optional[float], str]:
        """Calculate EPS = Net Income / Shares Outstanding"""
        # Try to find net income
        net_income_patterns = [
            r'net\s+income',
            r'net\s+profit',
            r'profit\s+for\s+the\s+year',
            r'earnings\s+attributable'
        ]
        
        net_income = None
        for pattern in net_income_patterns:
            net_income = self.extract_number(pattern)
            if net_income:
                break
        
        # Try to find shares outstanding
        shares_patterns = [
            r'shares\s+outstanding',
            r'weighted\s+average\s+shares',
            r'number\s+of\s+shares',
            r'common\s+shares'
        ]
        
        shares = None
        for pattern in shares_patterns:
            shares = self.extract_number(pattern)
            if shares:
                break
        
        if net_income and shares and shares > 0:
            # Handle millions/billions
            # Usually net income is in millions and shares too
            calculated_eps = net_income / shares
            
            # If result is very small, might need to adjust units
            if calculated_eps < 0.01:
                calculated_eps = (net_income * 1000) / shares  # Try different scale
            
            return calculated_eps, f"Calculated: ${calculated_eps:.2f} (Net Income: {net_income}, Shares: {shares})"
        
        return None, "Could not find Net Income or Shares Outstanding"
    
    def calculate_roe(self) -> Tuple[Optional[float], str]:
        """Calculate ROE = (Net Income / Shareholders' Equity) × 100"""
        # Net income
        net_income = self.extract_number(r'net\s+income')
        
        # Shareholders' equity
        equity_patterns = [
            r'shareholders?\s*\'?\s*equity',
            r'total\s+equity',
            r'stockholders?\s*\'?\s*equity'
        ]
        
        equity = None
        for pattern in equity_patterns:
            equity = self.extract_number(pattern)
            if equity:
                break
        
        if net_income and equity and equity > 0:
            roe = (net_income / equity) * 100
            return roe, f"Calculated: {roe:.1f}% (Net Income: {net_income}, Equity: {equity})"
        
        return None, "Could not find Net Income or Equity"
    
    def calculate_debt_equity_ratio(self) -> Tuple[Optional[float], str]:
        """Calculate D/E = Total Debt / Total Equity"""
        # Total debt
        debt_patterns = [
            r'total\s+debt',
            r'total\s+liabilities',
            r'borrowings',
            r'long[- ]term\s+debt'
        ]
        
        debt = None
        for pattern in debt_patterns:
            debt = self.extract_number(pattern)
            if debt:
                break
        
        # Equity
        equity_patterns = [
            r'shareholders?\s*\'?\s*equity',
            r'total\s+equity'
        ]
        
        equity = None
        for pattern in equity_patterns:
            equity = self.extract_number(pattern)
            if equity:
                break
        
        if debt and equity and equity > 0:
            de_ratio = debt / equity
            return de_ratio, f"Calculated: {de_ratio:.2f} (Debt: {debt}, Equity: {equity})"
        
        return None, "Could not find Total Debt or Equity"
    
    def calculate_profit_margin(self) -> Tuple[Optional[float], str]:
        """Calculate Profit Margin = (Net Income / Revenue) × 100"""
        net_income = self.extract_number(r'net\s+income')
        
        revenue_patterns = [
            r'total\s+revenue',
            r'net\s+revenue',
            r'sales',
            r'turnover'
        ]
        
        revenue = None
        for pattern in revenue_patterns:
            revenue = self.extract_number(pattern)
            if revenue:
                break
        
        if net_income and revenue and revenue > 0:
            margin = (net_income / revenue) * 100
            return margin, f"Calculated: {margin:.1f}% (Net Income: {net_income}, Revenue: {revenue})"
        
        return None, "Could not find Net Income or Revenue"
    
    def calculate_market_cap(self) -> Tuple[Optional[float], str]:
        """Verify Market Cap = Shares Outstanding * Stock Price (approx)"""
        shares = self.extract_number(r'shares\s+outstanding')
        price = self.extract_number(r'stock\s+price|market\s+price')
        if shares and price:
            cap = shares * price
            return cap, f"Calculated: ${cap:,.2f} (Shares: {shares}, Price: {price})"
        return None, "Price or Shares not found"

    def calculate_pe_ratio(self) -> Tuple[Optional[float], str]:
        """Calculate P/E = Price / EPS"""
        price = self.extract_number(r'stock\s+price|market\s+price')
        eps, _ = self.calculate_eps()
        if price and eps and eps > 0:
            pe = price / eps
            return pe, f"Calculated: {pe:.2f} (Price: {price}, EPS: {eps:.2f})"
        return None, "Price or EPS not found"
    
    def validate_metric(self, metric_name: str, ai_value: Any, calculated_value: Optional[float], 
                       threshold: float = 0.1) -> Dict[str, Any]:
        """
        Compare AI value with calculated value
        
        Args:
            metric_name: Name of the metric
            ai_value: Value extracted by AI
            calculated_value: Mathematically calculated value
            threshold: Acceptable difference ratio (0.1 = 10% difference)
        
        Returns:
            Validation result with confidence score
        """
        result = {
            "metric": metric_name,
            "ai_value": ai_value,
            "calculated_value": calculated_value,
            "confidence": "UNKNOWN",
            "status": "UNKNOWN",
            "message": ""
        }
        
        if calculated_value is None:
            result["confidence"] = "MEDIUM"
            result["status"] = "UNCHECKED"
            result["message"] = "Could not calculate - insufficient data in PDF"
            return result
        
        try:
            # Parse AI value with suffix handling
            if isinstance(ai_value, (int, float)):
                ai_numeric = float(ai_value)
            else:
                s = str(ai_value).upper().replace('%', '').replace('$', '').replace(',', '').strip()
                multiplier = 1.0
                if s.endswith('T'):
                    multiplier = 1e12
                    s = s[:-1]
                elif s.endswith('B'):
                    multiplier = 1e9
                    s = s[:-1]
                elif s.endswith('M') or s.endswith('MM'):
                    multiplier = 1e6
                    s = s.replace('MM', '').replace('M', '')
                elif s.endswith('K'):
                    multiplier = 1e3
                    s = s[:-1]
                
                ai_numeric = float(s) * multiplier
            
            # Smart Scale Adjustment
            # If off by exactly 1000x, 1M x, etc., adjust calculate_value or ai_value contextually
            # But simpler: check if difference is huge, try scaling logic
            
            # Simple Comparison
            diff = abs(ai_numeric - calculated_value)
            diff_ratio = diff / max(abs(calculated_value), 0.01)  # Avoid division by zero
            
            # Logic to detecting unit mismatches (e.g. AI says 150B, Calc says 150)
            if diff_ratio > 10.0:
                # Try scaling calculated value to match context
                if abs(ai_numeric / 1e9 - calculated_value) < max(calculated_value, 0.1) * threshold:
                    diff_ratio = abs(ai_numeric / 1e9 - calculated_value) / calculated_value
                elif abs(ai_numeric - calculated_value / 1e9) < max(calculated_value / 1e9, 0.1) * threshold:
                     diff_ratio = abs(ai_numeric - calculated_value / 1e9) / (calculated_value / 1e9)

            if diff_ratio <= threshold:
                result["confidence"] = "HIGH"
                result["status"] = "VERIFIED"
                result["message"] = f"✓ Values match (difference: {diff_ratio*100:.1f}%)"
            elif diff_ratio <= threshold * 3:
                result["confidence"] = "MEDIUM"
                result["status"] = "CLOSE"
                result["message"] = f"⚠ Close but not exact (difference: {diff_ratio*100:.1f}%)"
            else:
                result["confidence"] = "LOW"
                result["status"] = "MISMATCH"
                result["message"] = f"✗ Significant difference (AI: {ai_numeric:.2e}, Calc: {calculated_value:.2e})"
        
        except (ValueError, TypeError) as e:
            result["confidence"] = "LOW"
            result["status"] = "ERROR"
            result["message"] = f"Error comparing values: {str(e)}"
        
        return result
    
    def validate_all_metrics(self, ai_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate all metrics in the AI-extracted data
        
        Args:
            ai_metrics: Dictionary of metrics extracted by AI
        
        Returns:
            Validation report with confidence scores
        """
        validation_report = {
            "overall_confidence": "HIGH",
            "validations": {},
            "summary": {
                "verified": 0,
                "close": 0,
                "mismatch": 0,
                "unchecked": 0
            }
        }
        
        # Validate EPS
        if 'eps' in ai_metrics:
            calc_eps, eps_msg = self.calculate_eps()
            eps_validation = self.validate_metric('EPS', ai_metrics['eps'], calc_eps, threshold=0.15)
            eps_validation['calculation_details'] = eps_msg
            validation_report['validations']['eps'] = eps_validation
        
        # Validate ROE
        if 'roe' in ai_metrics:
            calc_roe, roe_msg = self.calculate_roe()
            roe_validation = self.validate_metric('ROE', ai_metrics['roe'], calc_roe, threshold=0.1)
            roe_validation['calculation_details'] = roe_msg
            validation_report['validations']['roe'] = roe_validation
        
        # Validate Debt/Equity
        if 'debt_equity' in ai_metrics:
            calc_de, de_msg = self.calculate_debt_equity_ratio()
            de_validation = self.validate_metric('Debt/Equity', ai_metrics['debt_equity'], calc_de, threshold=0.15)
            de_validation['calculation_details'] = de_msg
            validation_report['validations']['debt_equity'] = de_validation
        
        # Validate Profit Margin
        if 'profit_margin' in ai_metrics:
            calc_margin, margin_msg = self.calculate_profit_margin()
            margin_validation = self.validate_metric('Profit Margin', ai_metrics['profit_margin'], calc_margin, threshold=0.1)
            margin_validation['calculation_details'] = margin_msg
            validation_report['validations']['profit_margin'] = margin_validation
        
        # Validate Market Cap
        if 'market_cap' in ai_metrics:
            calc_mc, mc_msg = self.calculate_market_cap()
            mc_validation = self.validate_metric('Market Cap', ai_metrics['market_cap'], calc_mc, threshold=0.2)
            mc_validation['calculation_details'] = mc_msg
            validation_report['validations']['market_cap'] = mc_validation

        # Validate PE Ratio
        if 'pe_ratio' in ai_metrics:
            calc_pe, pe_msg = self.calculate_pe_ratio()
            pe_validation = self.validate_metric('P/E Ratio', ai_metrics['pe_ratio'], calc_pe, threshold=0.2)
            pe_validation['calculation_details'] = pe_msg
            validation_report['validations']['pe_ratio'] = pe_validation
        
        # Calculate summary
        for validation in validation_report['validations'].values():
            status = validation['status']
            if status == 'VERIFIED':
                validation_report['summary']['verified'] += 1
            elif status == 'CLOSE':
                validation_report['summary']['close'] += 1
            elif status == 'MISMATCH':
                validation_report['summary']['mismatch'] += 1
            else:
                validation_report['summary']['unchecked'] += 1
        
        # Determine overall confidence
        total_checked = validation_report['summary']['verified'] + validation_report['summary']['close'] + validation_report['summary']['mismatch']
        
        if total_checked > 0:
            verified_ratio = validation_report['summary']['verified'] / total_checked
            mismatch_ratio = validation_report['summary']['mismatch'] / total_checked
            
            if verified_ratio >= 0.7 and mismatch_ratio == 0:
                validation_report['overall_confidence'] = 'HIGH'
            elif verified_ratio >= 0.5 or mismatch_ratio <= 0.3:
                validation_report['overall_confidence'] = 'MEDIUM'
            else:
                validation_report['overall_confidence'] = 'LOW'
        else:
            validation_report['overall_confidence'] = 'MEDIUM'  # No validation possible
        
        return validation_report
