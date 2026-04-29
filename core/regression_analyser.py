import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import curve_fit
from scipy.stats import t as t_dist
from enum import Enum
from dataclasses import dataclass
from typing import Tuple, List

class RegressionType(Enum):
    LINEAR = "Linear"
    POLYNOMIAL = "Polynomial"
    EXPONENTIAL = "Exponential"
    LOGARITHMIC = "Logarithmic"

class ErrorBarType(Enum):
    NONE = "None"
    STANDARD_DEVIATION = "Standard Deviation"
    STANDARD_ERROR = "Standard Error"

@dataclass
class RegressionMetrics:
    r_squared: float
    rmse: float
    equation_str: str
    
@dataclass
class RegressionResult:
    x_line: np.ndarray
    y_line: np.ndarray
    y_pred_all: np.ndarray
    metrics: RegressionMetrics
    residuals: np.ndarray

class RegressionAnalyser:
    """Handles mathematcal modeling and statistics for dataset regression"""
    
    @staticmethod
    def clean_data(df: pd.DataFrame, x_col: str, y_col: str, reg_type: RegressionType) -> Tuple[np.ndarray, np.ndarray]:
        """Validates and extracts numeric vectors used for analysis"""
        if not pd.api.types.is_numeric_dtype(df[x_col]) or not pd.api.types.is_numeric_dtype(df[y_col]):
            raise TypeError(f"Columns {x_col} and {y_col} must be numeric")
        
        mask = np.isfinite(df[x_col]) & np.isfinite(df[y_col])
        if reg_type == RegressionType.LOGARITHMIC:
            mask &= (df[x_col] > 0)
        
        return df.loc[mask, x_col].values, df.loc[mask, y_col].values
    
    @staticmethod
    def compute_fit(x_data: np.ndarray, y_data: np.ndarray, reg_type: RegressionType, degree: int = 2) -> RegressionResult:
        """Computes a regression fit based on regression type"""
        if len(x_data) < 2:
            raise ValueError("Insufficient data points for regression analysis. A minimum of 2 points is required.")

        x_line = np.linspace(x_data.min(), x_data.max(), 100)
        num_format = ".4g"
        
        if reg_type == RegressionType.POLYNOMIAL:
            try:
                coeffs = np.polyfit(x_data, y_data, degree)
            except Exception as e:
                raise ValueError(f"Polynomial fit failed: {str(e)}")
                
            poly_func = np.poly1d(coeffs)
            y_pred_all = poly_func(x_data)
            y_line = poly_func(x_line)
            
            terms = []
            for i, coefficient in enumerate(coeffs):
                power = degree - i
                abs_coeff = abs(coefficient)
                sign = "-" if coefficient < 0 else ("+" if i > 0 else "")
                
                formatted_coeff = f"{abs_coeff:{num_format}}"
                if power == 0:
                    term = f"{sign} {formatted_coeff}".strip()
                elif power == 1:
                    term = f"{sign} {formatted_coeff}x".strip()
                else:
                    term = f"{sign} {formatted_coeff}x^{power}".strip()
                terms.append(term)
                
            equation_str = " ".join(terms)
        
        elif reg_type == RegressionType.EXPONENTIAL:
            def exp_func(x, a, b):
                return a * np.exp(b * x)
            
            try:
                slope, intercept, _, _, _ = stats.linregress(x_data, np.log(np.abs(y_data) + 1e-10))
                p0 = (np.exp(intercept), slope)
            except Exception:
                p0 = (1.0, 1e-6)

            try:
                popt, _ = curve_fit(exp_func, x_data, y_data, p0=p0, maxfev=10000)
            except RuntimeError as e:
                raise ValueError(f"Exponential fit failed to converge: {str(e)}")

            y_pred_all = exp_func(x_data, *popt)
            y_line = exp_func(x_line, *popt)
            op = "+" if popt[1] >= 0 else "-"
            equation_str = f"{popt[0]:{num_format}} * exp({op}{abs(popt[1]):{num_format}} * x)"
        
        elif reg_type == RegressionType.LOGARITHMIC:
            def log_func(x, a, b):
                return a + b * np.log(x)
                
            try:
                popt, _ = curve_fit(log_func, x_data, y_data, maxfev=10000)
            except RuntimeError as e:
                raise ValueError(f"Logarithmic fit failed to converge: {str(e)}")
                
            y_pred_all = log_func(x_data, *popt)
            y_line = log_func(x_line, *popt)
            op = "+" if popt[1] >= 0 else "-"
            equation_str = f"{popt[0]:{num_format}} {op} {abs(popt[1]):{num_format}} * ln(x)"
        else:
            slope, intercept, _, _, _ = stats.linregress(x_data, y_data)
            y_pred_all = slope * x_data + intercept
            y_line = slope * x_line + intercept
            op = "+" if intercept >= 0 else "-"
            equation_str = f"{slope:{num_format}}x {op} {abs(intercept):{num_format}}"
        
        residuals = y_data - y_pred_all
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y_data - np.mean(y_data))**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        rmse = np.sqrt(np.mean(residuals**2))
        
        metrics = RegressionMetrics(r_squared=r_squared, rmse=rmse, equation_str=equation_str)
        return RegressionResult(x_line, y_line, y_pred_all, metrics, residuals)
    
    @staticmethod
    def compute_confidence_interval(x_data: np.ndarray, residuals: np.ndarray, x_line: np.ndarray, confidence_level: float) -> np.ndarray:
        n = len(x_data)
        if n <= 2:
            return np.zeros_like(x_line)
        
        residual_std = np.sqrt(np.sum(residuals**2) / (n - 2))
        x_mean = np.mean(x_data)
        sum_sq_diff = np.sum((x_data - x_mean)**2)
        
        if sum_sq_diff == 0:
            return np.zeros_like(x_line)
        
        se_line = residual_std * np.sqrt(1/n + (x_line - x_mean)**2 / sum_sq_diff)
        t_val = t_dist.ppf((1 + confidence_level) / 2, n - 2)
        return t_val * se_line