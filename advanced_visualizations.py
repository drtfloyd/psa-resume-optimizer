"""
Advanced Visualization Module for PSA Resume Optimizer
Interactive charts, radar plots, and enhanced dashboard components
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

class AdvancedVisualizer:
    def __init__(self):
        self.theme = "plotly_white"
        
    def create_skill_radar_chart(self, domain_scores: Dict[str, float], critical_domains: List[str]) -> go.Figure:
        """Create an interactive radar chart for skill domains"""
        
        domains = list(domain_scores.keys())
        scores = list(domain_scores.values())
        
        # Create colors: red for critical, blue for others
        colors = ['#e74c3c' if domain in critical_domains else '#3498db' for domain in domains]
        
        fig = go.Figure()
        
        # Add radar trace
        fig.add_trace(go.Scatterpolar(
            r=scores,
            theta=domains,
            fill='toself',
            name='Current Skills',
            line=dict(color='#2980b9', width=2),
            fillcolor='rgba(41, 128, 185, 0.1)',
            marker=dict(size=8, color=colors)
        ))
        
        # Add target score line (80%)
        target_scores = [80] * len(domains)
        fig.add_trace(go.Scatterpolar(
            r=target_scores,
            theta=domains,
            mode='lines',
            name='Target (80%)',
            line=dict(color='#27ae60', width=2, dash='dash'),
            showlegend=True
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    tickfont=dict(size=10)
                ),
                angularaxis=dict(
                    tickfont=dict(size=11),
                    rotation=90,
                    direction='clockwise'
                )
            ),
            title={
                'text': "🎯 Skill Domain Analysis",
                'x': 0.5,
                'font': {'size': 18}
            },
            template=self.theme,
            height=500,
            showlegend=True
        )
        
        return fig

    def create_keyword_heatmap(self, domain_gaps: Dict[str, List[str]], domain_scores: Dict[str, float]) -> go.Figure:
        """Create a heatmap showing keyword gaps by domain"""
        
        if not domain_gaps:
            return self._create_empty_chart("No keyword gaps to display")
        
        # Prepare data for heatmap
        domains = list(domain_gaps.keys())[:5]  # Top 5 domains
        max_gaps = 5  # Show top 5 gaps per domain
        
        heatmap_data = []
        hover_text = []
        
        for domain in domains:
            gaps = domain_gaps[domain][:max_gaps]
            domain_row = []
            hover_row = []
            
            for i in range(max_gaps):
                if i < len(gaps):
                    gap_priority = max(0, 100 - domain_scores.get(domain, 0))
                    domain_row.append(gap_priority)
                    hover_row.append(f"Domain: {domain}<br>Missing: {gaps[i]}<br>Priority: {gap_priority:.0f}")
                else:
                    domain_row.append(0)
                    hover_row.append("")
            
            heatmap_data.append(domain_row)
            hover_text.append(hover_row)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data,
            x=[f"Gap {i+1}" for i in range(max_gaps)],
            y=domains,
            colorscale='RdYlBu_r',
            showscale=True,
            colorbar=dict(title="Gap Priority"),
            hovertemplate='%{text}<extra></extra>',
            text=hover_text
        ))
        
        fig.update_layout(
            title={
                'text': "🔥 Keyword Gap Priority Matrix",
                'x': 0.5,
                'font': {'size': 18}
            },
            xaxis_title="Missing Keywords (Ranked by Priority)",
            yaxis_title="Skill Domains",
            template=self.theme,
            height=400
        )
        
        return fig

    def create_progress_timeline(self, analysis_history: List[Dict]) -> go.Figure:
        """Create an interactive timeline of progress"""
        
        if len(analysis_history) < 2:
            return self._create_empty_chart("Need at least 2 analyses for timeline")
        
        df = pd.DataFrame(analysis_history)
        df['analysis_number'] = range(1, len(df) + 1)
        
        fig = go.Figure()
        
        # Overall score trend
        fig.add_trace(go.Scatter(
            x=df['analysis_number'],
            y=df['overall_score'],
            mode='lines+markers',
            name='Overall Score',
            line=dict(color='#3498db', width=3),
            marker=dict(size=10)
        ))
        
        # Trust score trend
        if 'trust_score' in df.columns:
            fig.add_trace(go.Scatter(
                x=df['analysis_number'],
                y=df['trust_score'],
                mode='lines+markers',
                name='Trust Score',
                line=dict(color='#2ecc71', width=2)
            ))
        
        # Visibility score trend
        if 'visibility_score' in df.columns:
            fig.add_trace(go.Scatter(
                x=df['analysis_number'],
                y=df['visibility_score'],
                mode='lines+markers',
                name='Visibility Score',
                line=dict(color='#e74c3c', width=2)
            ))
        
        fig.update_layout(
            title={
                'text': "📈 Your PSA Progress Over Time",
                'x': 0.5,
                'font': {'size': 18}
            },
            xaxis_title="Analysis Session",
            yaxis_title="Score (%)",
            yaxis=dict(range=[0, 100]),
            template=self.theme,
            height=400
        )
        
        return fig

    def create_optimization_dashboard(self, results: Dict) -> go.Figure:
        """Create a comprehensive dashboard view"""
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Overall Score', 'Domain Performance', 'Gap Analysis', 'Progress Indicator'
            ),
            specs=[
                [{"type": "indicator"}, {"type": "bar"}],
                [{"type": "pie"}, {"type": "scatter"}]
            ]
        )
        
        # Overall score indicator
        overall_score = results.get('overall_score', 0)
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=overall_score,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Overall Match %"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "gray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 80
                    }
                }
            ),
            row=1, col=1
        )
        
        # Domain performance
        domain_scores = results.get('domain_scores', {})
        if domain_scores:
            domains = list(domain_scores.keys())[:6]
            scores = [domain_scores[d] for d in domains]
            
            fig.add_trace(
                go.Bar(
                    x=domains,
                    y=scores,
                    name='Domain Scores',
                    marker_color=scores,
                    marker_colorscale='RdYlGn',
                    showlegend=False
                ),
                row=1, col=2
            )
        
        # Gap analysis pie
        domain_gaps = results.get('domain_gaps', {})
        if domain_gaps:
            gap_counts = [len(gaps) for gaps in domain_gaps.values()]
            fig.add_trace(
                go.Pie(
                    labels=list(domain_gaps.keys()),
                    values=gap_counts,
                    name="Gaps by Domain",
                    showlegend=False
                ),
                row=2, col=1
            )
        
        fig.update_layout(
            title={
                'text': "📊 PSA Analysis Dashboard",
                'x': 0.5,
                'font': {'size': 20}
            },
            template=self.theme,
            height=600,
            showlegend=False
        )
        
        return fig

    def _create_empty_chart(self, message: str) -> go.Figure:
        """Create an empty chart with a message"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            template=self.theme,
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False),
            height=300
        )
        return fig

# Global instance
visualizer = AdvancedVisualizer()