import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib
# Use a non-GUI backend for headless environments (e.g., servers, CI, Windows without GUI libs)
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from jinja2 import Template
import os
import datetime

class DataInsightGenerator:
    def __init__(self, df):
        self.df = df.replace([np.inf, -np.inf], np.nan)
        self.report_html = ""
        self.numeric_cols = self.df.select_dtypes(include=np.number).columns.tolist()
        self.categorical_cols = self.df.select_dtypes(exclude=np.number).columns.tolist()
        
    def _get_base64_plot(self):
        """Convert matplotlib plot to base64 encoded image"""
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
        buffer.seek(0)
        img_str = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
        return img_str
    
    def _generate_column_stats(self):
        """Generate statistics for each column"""
        stats_data = []
        
        for col in self.df.columns:
            col_data = {
                'name': col,
                'dtype': str(self.df[col].dtype),
                'missing': self.df[col].isna().sum(),
                'missing_pct': round(self.df[col].isna().mean() * 100, 2),
                'unique': self.df[col].nunique()
            }
            
            if col in self.numeric_cols:
                col_stats = self.df[col].describe(percentiles=[.25, .5, .75])
                col_data.update({
                    'type': 'Numeric',
                    'min': round(col_stats['min'], 4),
                    'max': round(col_stats['max'], 4),
                    'mean': round(col_stats['mean'], 4),
                    'median': round(col_stats['50%'], 4),
                    'std': round(col_stats['std'], 4) if 'std' in col_stats else np.nan,
                    'q1': round(col_stats['25%'], 4),
                    'q3': round(col_stats['75%'], 4),
                })
            else:
                top_values = self.df[col].value_counts().head(5)
                col_data.update({
                    'type': 'Categorical',
                    'top_values': [{'value': k, 'count': v, 'pct': round(v/len(self.df)*100, 2)} 
                                  for k, v in top_values.items()]
                })
                
            stats_data.append(col_data)
            
        return stats_data
    
    def _generate_correlation_analysis(self):
        """Generate correlation matrices and plots"""
        results = {
            'numeric_matrix': {},
            'categorical_matrix': {},
            'numeric_img': None,
            'categorical_img': None
        }
        
        # Numeric correlations
        if len(self.numeric_cols) > 1:
            corr_matrix = self.df[self.numeric_cols].corr()
            plt.figure(figsize=(12, 8))
            sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f")
            plt.title('Numeric Correlation Matrix')
            results['numeric_img'] = self._get_base64_plot()
            results['numeric_matrix'] = corr_matrix.to_dict()
        
        # Cramer's V for categorical associations (no SciPy dependency)
        if len(self.categorical_cols) > 1:
            cramers_matrix = pd.DataFrame(
                index=self.categorical_cols, 
                columns=self.categorical_cols,
                dtype=float
            )
            
            for col1 in self.categorical_cols:
                for col2 in self.categorical_cols:
                    if col1 == col2:
                        cramers_matrix.loc[col1, col2] = 1.0
                    else:
                        confusion_matrix = pd.crosstab(self.df[col1], self.df[col2])
                        observed = confusion_matrix.values.astype(float)
                        # Guard against empty or degenerate tables
                        if observed.size == 0:
                            cramers_matrix.loc[col1, col2] = np.nan
                            continue
                        row_sums = observed.sum(axis=1, keepdims=True)
                        col_sums = observed.sum(axis=0, keepdims=True)
                        total = observed.sum()
                        # Expected frequencies
                        expected = (row_sums @ col_sums) / max(total, 1.0)
                        # Avoid division by zero by masking zeros in expected
                        with np.errstate(divide='ignore', invalid='ignore'):
                            chi2 = np.nansum(((observed - expected) ** 2) / np.where(expected > 0, expected, np.nan))
                        n = total if total > 0 else 1.0
                        r, k = observed.shape
                        denom = max(min(k - 1, r - 1), 1)
                        phi2 = chi2 / n
                        cramers_v = float(np.sqrt(max(phi2 / denom, 0.0)))
                        cramers_matrix.loc[col1, col2] = cramers_v
            
            plt.figure(figsize=(12, 8))
            sns.heatmap(cramers_matrix, annot=True, cmap='Blues', fmt=".2f")
            plt.title('Categorical Association (Cramer\'s V)')
            results['categorical_img'] = self._get_base64_plot()
            results['categorical_matrix'] = cramers_matrix.to_dict()
            
        return results
    
    def _generate_distribution_plots(self):
        """Generate distribution plots for all columns"""
        dist_plots = {}
        
        # Numeric distributions
        for col in self.numeric_cols:
            plt.figure(figsize=(10, 4))
            plt.subplot(1, 2, 1)
            sns.histplot(self.df[col], kde=True)
            plt.title(f'{col} Distribution')
            
            plt.subplot(1, 2, 2)
            sns.boxplot(x=self.df[col])
            plt.title(f'{col} Boxplot')
            
            dist_plots[col] = self._get_base64_plot()
        
        # Categorical distributions
        for col in self.categorical_cols:
            plt.figure(figsize=(10, 6))
            # Show top 10 categories to avoid overcrowding
            top_categories = self.df[col].value_counts().iloc[:10].index
            sns.countplot(y=col, data=self.df, order=top_categories)
            plt.title(f'{col} Value Counts')
            dist_plots[col] = self._get_base64_plot()
            
        return dist_plots
    
    def _generate_relationship_plots(self):
        """Generate relationship visualization options"""
        relationships = {}
        
        # Numeric vs Numeric
        if len(self.numeric_cols) >= 2:
            # Sample to avoid too many points in pairplot
            sample_df = self.df.sample(min(500, len(self.df)))
            plt.figure(figsize=(10, 8))
            sns.pairplot(sample_df[self.numeric_cols[:5]])
            relationships['pairplot'] = self._get_base64_plot()
            
            plt.figure(figsize=(10, 6))
            sns.scatterplot(
                x=self.numeric_cols[0], 
                y=self.numeric_cols[1], 
                data=sample_df
            )
            plt.title(f'{self.numeric_cols[0]} vs {self.numeric_cols[1]}')
            relationships['scatterplot'] = self._get_base64_plot()
        
        # Categorical vs Numeric
        if self.categorical_cols and self.numeric_cols:
            cat_col = self.categorical_cols[0]
            num_col = self.numeric_cols[0]
            
            plt.figure(figsize=(12, 6))
            plt.subplot(1, 2, 1)
            sns.boxplot(x=cat_col, y=num_col, data=self.df)
            plt.title(f'{num_col} by {cat_col}')
            plt.xticks(rotation=45)
            
            plt.subplot(1, 2, 2)
            sns.barplot(x=cat_col, y=num_col, data=self.df, errorbar=None)
            plt.title(f'{num_col} by {cat_col}')
            plt.xticks(rotation=45)
            
            relationships['cat_num'] = self._get_base64_plot()
        
        return relationships
    
    def generate_report(self, title="Dataset Analysis Report", template_path="report_template.html"):
        """Generate complete HTML report"""
        # Prepare data
        column_stats = self._generate_column_stats()
        correlations = self._generate_correlation_analysis()
        distributions = self._generate_distribution_plots()
        relationships = self._generate_relationship_plots()
        
        # Load template
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                template_str = f.read()
        else:
            raise FileNotFoundError(f"Template file not found at {template_path}")
        
        template = Template(template_str)
        
    
        # Render template with the new 'now' variable
        self.report_html = template.render(
            title=title,
           
            dataset_head=self.df.head(10).to_html(classes='table table-striped table-sm'),
            shape=self.df.shape,
            column_stats=column_stats,
            numeric_cols=self.numeric_cols,
            categorical_cols=self.categorical_cols,
            correlations=correlations,
            distributions=distributions,
            relationships=relationships
        )
        return self.report_html
    
    def save_report(self, filename="data_insight_report.html"):
        """Save report to HTML file"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.report_html)