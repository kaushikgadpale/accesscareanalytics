import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
from config import THEME_CONFIG
from modules.airtable.kpi import calculate_performance_score, get_kpi_data

def create_leader_performance_dashboard(kpi_df, scores_df, weights=None):
    """
    Create the leader performance dashboard
    
    Args:
        kpi_df: DataFrame containing KPI data
        scores_df: DataFrame containing performance scores
        weights: Dictionary of weights for different metrics
        
    Returns:
        None (displays visualizations in Streamlit)
    """
    if kpi_df.empty:
        st.warning("No KPI data available. Please check your Airtable connection.")
        
        # Generate sample data for demonstration purposes
        if st.button("Generate Sample Data for Demo"):
            kpi_df = generate_sample_kpi_data()
            scores_df = calculate_performance_score(kpi_df, weights)
            st.success("Sample data generated for demonstration!")
        else:
            return
    
    # Set default weights if not provided
    if weights is None:
        weights = {
            'EargymPromotion': 1,
            'Crossbooking': 1,
            'BOTDandEODFilled': 1,
            'PhotosVideosTestimonials': 1,
            'XraysAndDentalNotesUploaded': 1
        }
    
    # Add dashboard explanation
    st.markdown("""
    <div style="background-color: var(--color-card); padding: 15px; border-radius: var(--border-radius); margin-bottom: 20px; box-shadow: var(--box-shadow);">
        <h4 style="margin-top: 0; color: var(--color-text);">👥 Onsite Leader Performance Dashboard</h4>
        <p style="color: var(--color-text-secondary);">This dashboard helps evaluate onsite leader performance based on KPIs collected from each event. 
        Use it to track performance metrics, identify top performers, and spot areas for improvement.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Refactor Minimum Requirements section to use Streamlit markdown for the list
    st.markdown("##### Minimum Requirements:")
    st.markdown("""
    - **Eargym Promotion:** 100% of all audio exams (min. 1)
    - **Crossbooking:** Minimum 2 per event
    - **Photos/Videos/Testimonials:** Minimum 3 per event
    - **Forms:** BOTD, EOD and Team Feedback must be completed
    - **Documentation:** All Patient History Forms and Dental Notes must be completed
    """)
    
    # Display the leaderboard
    st.subheader("Onsite Leader Performance Leaderboard")
    
    # Create two columns for explanation and weight adjustment
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("""
        <div style="background-color: var(--color-info-bg); padding: 15px; border-radius: var(--border-radius); margin-bottom: 15px;">
            The performance score is calculated based on these KPIs:
            <ul>
                <li><strong>Eargym Promotion</strong>: Number of Eargym promotions</li>
                <li><strong>Crossbooking</strong>: Number of cross-bookings achieved</li>
                <li><strong>BOTD/EOD Forms</strong>: Whether Beginning/End of Day forms are completed</li>
                <li><strong>Photos/Videos</strong>: Number of photos/videos/testimonials posted</li>
                <li><strong>Documentation</strong>: Whether all Xrays and Dental Notes are properly uploaded</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### Adjust KPI Weights")
        st.markdown("Set the relative importance of each KPI:")
        
        # Create sliders for weight adjustment
        new_weights = {}
        new_weights['EargymPromotion'] = st.slider("Eargym Promotion Weight", 0.0, 5.0, float(weights['EargymPromotion']), 0.5)
        new_weights['Crossbooking'] = st.slider("Crossbooking Weight", 0.0, 5.0, float(weights['Crossbooking']), 0.5)
        new_weights['BOTDandEODFilled'] = st.slider("BOTD/EOD Forms Weight", 0.0, 5.0, float(weights['BOTDandEODFilled']), 0.5)
        new_weights['PhotosVideosTestimonials'] = st.slider("Photos/Videos Weight", 0.0, 5.0, float(weights['PhotosVideosTestimonials']), 0.5)
        new_weights['XraysAndDentalNotesUploaded'] = st.slider("Documentation Weight", 0.0, 5.0, float(weights['XraysAndDentalNotesUploaded']), 0.5)
        
        # Check if weights have changed
        if new_weights != weights:
            st.session_state['kpi_weights'] = new_weights
            st.button("Recalculate Scores")
    
    # Display the leaderboard in a nice table
    if not scores_df.empty:
        # Enhanced leaderboard display
        st.markdown("#### Current Performance Ranking")
        
        # Format scores DataFrame for display
        display_df = scores_df.copy()
        display_df = display_df.sort_values('PerformanceScore', ascending=False).reset_index()
        
        # Format columns
        display_df['PerformanceScore'] = display_df['PerformanceScore'].round(1)
        display_df['EventCount'] = display_df['EventCount'].astype(int)
        
        # Create a styled table with colored performance scores
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=['<b>Rank</b>', '<b>Leader</b>', '<b>Performance<br>Score</b>', '<b>Events<br>Count</b>'],
                fill_color='#f8f9fa',  # Light gray background
                align='left',
                font=dict(color='#212529', size=14)  # Dark text
            ),
            cells=dict(
                values=[
                    display_df['Rank'].astype(int),
                    display_df['Leader'],
                    display_df['PerformanceScore'].apply(lambda x: f"{x:.1f}"),
                    display_df['EventCount']
                ],
                fill_color=[
                    'white',  # White background for rank
                    'white',  # White background for leader
                    display_df['PerformanceScore'].apply(  # Gradient colors for score
                        lambda x: f'rgba(94, 140, 106, {min(x/100, 0.5)})' if x >= 70 else  # Light green for high scores
                        (f'rgba(255, 193, 7, {min(x/100, 0.3)})' if x >= 50 else  # Light yellow for medium scores
                         f'rgba(220, 53, 69, {min(x/100, 0.2)})') # Very light red for low scores
                    ),
                    'white'  # White background for event count
                ],
                align='left',
                font=dict(color='#212529', size=14),  # Dark text for all cells
                height=35  # Slightly taller rows
            )
        )])
        
        # Update layout
        fig.update_layout(
            margin=dict(l=0, r=0, b=0, t=0),
            height=45 * (len(display_df) + 1)  # Adjust height based on number of rows
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add ranking stars for top performers
        top_performers = display_df.head(3)
        
        if len(top_performers) > 0:
            st.markdown("#### 🏆 Top Performers")
            
            cols = st.columns(min(3, len(top_performers)))
            for i, (_, leader) in enumerate(top_performers.iterrows()):
                with cols[i]:
                    medal = "🥇" if i == 0 else ("🥈" if i == 1 else "🥉")
                    st.markdown(f"""
                    <div style="text-align: center; background-color: var(--color-card); padding: 15px; border-radius: var(--border-radius); box-shadow: var(--box-shadow);">
                        <div style="font-size: 2rem;">{medal}</div>
                        <div style="font-weight: 500; color: var(--color-text); margin-top: 10px;">{leader['Leader']}</div>
                        <div style="font-size: 1.5rem; color: var(--color-accent); margin-top: 5px;">{leader['PerformanceScore']:.1f}</div>
                        <div style="color: var(--color-text-secondary); font-size: 0.8rem;">Based on {leader['EventCount']} events</div>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Create performance metrics visualizations
    st.subheader("Performance Metrics")
    
    # Create tabs for different visualizations
    tab1, tab2, tab3 = st.tabs(["Performance Breakdown", "Trend Analysis", "Site Performance"])
    
    with tab1:
        if not scores_df.empty:
            # Replace radar chart with horizontal bar chart for better clarity
            st.markdown("#### Leader Performance Comparison")
            st.markdown("This chart shows how each leader performs across different KPIs:")
            
            # Prepare data for horizontal bar chart
            radar_data = scores_df.copy()
            
            # Calculate normalized metrics (0-10 scale for better visualization)
            metric_cols = ['NormalizedEargymPromotion', 'NormalizedCrossbooking', 'BOTDandEODFilled', 
                         'NormalizedPhotosVideosTestimonials', 'XraysAndDentalNotesUploaded']
            
            # Transform data for bar chart
            bar_data = []
            for leader in radar_data.index:
                for i, col in enumerate(metric_cols):
                    metric_name = ['Eargym Promotion', 'Crossbooking', 'BOTD/EOD Forms', 
                                 'Photos/Videos', 'Documentation'][i]
                    # Scale to 0-10 for better visualization
                    val = float(radar_data.loc[leader, col]) * 10
                    bar_data.append({
                        'Leader': leader,
                        'Metric': metric_name,
                        'Score': val
                    })
            
            bar_df = pd.DataFrame(bar_data)
            
            # Create horizontal bar chart using Plotly Express
            fig = px.bar(
                bar_df, 
                y='Metric',
                x='Score',
                color='Leader',
                barmode='group',
                orientation='h',
                title='KPI Performance by Leader',
                labels={'Score': 'Performance (0-10 scale)', 'Metric': 'KPI Category'},
                template='plotly_white',
                height=500,
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            
            # Update layout for better readability
            fig.update_layout(
                xaxis=dict(title='Performance Score (0-10)', range=[0, 10]),
                yaxis=dict(title=''),
                legend=dict(title='Leader', orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5),
                margin=dict(l=20, r=20, t=60, b=80)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Stacked bar chart showing contribution of each KPI to overall score
            st.markdown("#### Score Composition by KPI")
            st.markdown("This chart shows how each KPI contributes to the overall performance score:")
            
            # Prepare data for stacked bar chart
            stack_data = []
            
            for leader in scores_df.index:
                # Calculate the weighted contribution of each KPI
                weights_sum = sum(weights.values())
                eargym_contrib = scores_df.loc[leader, 'NormalizedEargymPromotion'] * weights['EargymPromotion'] / weights_sum * 100
                crossbook_contrib = scores_df.loc[leader, 'NormalizedCrossbooking'] * weights['Crossbooking'] / weights_sum * 100
                forms_contrib = scores_df.loc[leader, 'BOTDandEODFilled'] * weights['BOTDandEODFilled'] / weights_sum * 100
                photos_contrib = scores_df.loc[leader, 'NormalizedPhotosVideosTestimonials'] * weights['PhotosVideosTestimonials'] / weights_sum * 100
                docs_contrib = scores_df.loc[leader, 'XraysAndDentalNotesUploaded'] * weights['XraysAndDentalNotesUploaded'] / weights_sum * 100
                
                # Add to stacked data
                stack_data.append({
                    'Leader': leader,
                    'KPI': 'Eargym Promotion',
                    'Contribution': eargym_contrib
                })
                stack_data.append({
                    'Leader': leader,
                    'KPI': 'Crossbooking',
                    'Contribution': crossbook_contrib
                })
                stack_data.append({
                    'Leader': leader,
                    'KPI': 'BOTD/EOD Forms',
                    'Contribution': forms_contrib
                })
                stack_data.append({
                    'Leader': leader,
                    'KPI': 'Photos/Videos',
                    'Contribution': photos_contrib
                })
                stack_data.append({
                    'Leader': leader,
                    'KPI': 'Documentation',
                    'Contribution': docs_contrib
                })
            
            stack_df = pd.DataFrame(stack_data)
            
            # Create stacked bar chart
            fig = px.bar(
                stack_df,
                x='Leader',
                y='Contribution',
                color='KPI',
                title='Performance Score Breakdown by KPI',
                color_discrete_sequence=px.colors.qualitative.Pastel,
                template='plotly_white'
            )
            
            fig.update_layout(
                xaxis_title='Leader',
                yaxis_title='Score Contribution',
                legend_title='KPI Category',
                height=450,
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add KPI compliance breakdown section
            if 'EargymMinMet' in scores_df.columns:
                st.markdown("#### KPI-Specific Compliance")
                st.markdown("This shows how well each leader meets the minimum requirements for each KPI category:")
                
                compliance_data = []
                for leader in scores_df.index:
                    # For each KPI, get the average compliance percentage (0-100)
                    compliance_data.append({
                        'Leader': leader,
                        'KPI': 'Eargym Promotion',
                        'Compliance': scores_df.loc[leader, 'EargymMinMet'] * 100
                    })
                    compliance_data.append({
                        'Leader': leader,
                        'KPI': 'Crossbooking',
                        'Compliance': scores_df.loc[leader, 'CrossbookingMinMet'] * 100
                    })
                    compliance_data.append({
                        'Leader': leader,
                        'KPI': 'BOTD/EOD Forms',
                        'Compliance': scores_df.loc[leader, 'BOTDandEODFilled'] * 100
                    })
                    compliance_data.append({
                        'Leader': leader,
                        'KPI': 'Photos/Videos',
                        'Compliance': scores_df.loc[leader, 'PhotosMinMet'] * 100
                    })
                    compliance_data.append({
                        'Leader': leader,
                        'KPI': 'Documentation',
                        'Compliance': scores_df.loc[leader, 'XraysAndDentalNotesUploaded'] * 100
                    })
                
                compliance_df = pd.DataFrame(compliance_data)
                
                # Create heatmap of compliance
                heatmap_df = compliance_df.pivot(index='KPI', columns='Leader', values='Compliance')
                
                # Fill NaN with 0 for leaders who might be missing some KPI data entirely
                heatmap_df = heatmap_df.fillna(0.0)
                
                fig = px.imshow(
                    heatmap_df,
                    text_auto=True, # Let Plotly handle text display for zeros and non-zeros
                    labels=dict(x="Leader", y="KPI", color="Compliance %"),
                    color_continuous_scale='RdYlGn',
                    range_color=[0, 100],
                    title='KPI Compliance by Leader (%)'
                )
                
                # Update layout
                fig.update_layout(
                    xaxis_title='Leader',
                    yaxis_title='KPI Category',
                    height=350,
                    margin=dict(l=50, r=50, t=80, b=50)
                )
                
                # Improve text visibility on the heatmap
                fig.update_traces(
                    texttemplate='%{z:.1f}%', # Use %{z:.1f}% to display the heatmap value
                    textfont=dict(color='black', size=12, family='Arial')
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Add explanation
                st.markdown("""
                <div style="background-color: var(--color-info-bg); padding: 15px; border-radius: var(--border-radius); margin-bottom: 15px;">
                    <p style="margin-bottom: 0;">
                    <strong>KPI Compliance</strong> shows how often each leader meets the minimum requirements for each category:
                    </p>
                    <ul>
                        <li>100% means the leader always meets or exceeds the minimum requirement</li>
                        <li>Partial percentages mean the leader partially meets the requirement (e.g., 1 out of 2 required crossbookings = 50%)</li>
                        <li>0% means the leader never meets the minimum requirement</li>
                    </ul>
                    <p style="margin-bottom: 0;">
                    Leaders should aim for 100% compliance across all categories.
                    </p>
                </div>
                """, unsafe_allow_html=True)
    
    with tab2:
        # Time series analysis
        st.markdown("#### Performance Trends Over Time")
        st.markdown("Track how leader performance has changed over time:")
        
        if 'Date' in kpi_df.columns and not kpi_df.empty:
            # Group by leader and date to get scores over time
            kpi_df_sorted = kpi_df.sort_values('Date')
            
            # Calculate a simple running score for each event
            # Using a 0-10 scale for each metric
            kpi_df_sorted['EventScore'] = (
                (kpi_df_sorted['EargymPromotion'] / kpi_df_sorted['EargymPromotion'].max() if kpi_df_sorted['EargymPromotion'].max() > 0 else 0) * weights['EargymPromotion'] +
                (kpi_df_sorted['Crossbooking'] / kpi_df_sorted['Crossbooking'].max() if kpi_df_sorted['Crossbooking'].max() > 0 else 0) * weights['Crossbooking'] +
                kpi_df_sorted['BOTDandEODFilled'] * weights['BOTDandEODFilled'] +
                (kpi_df_sorted['PhotosVideosTestimonials'] / kpi_df_sorted['PhotosVideosTestimonials'].max() if kpi_df_sorted['PhotosVideosTestimonials'].max() > 0 else 0) * weights['PhotosVideosTestimonials'] +
                kpi_df_sorted['XraysAndDentalNotesUploaded'] * weights['XraysAndDentalNotesUploaded']
            )
            
            # Normalize to 0-100 scale
            weight_sum = sum(weights.values())
            kpi_df_sorted['EventScore'] = kpi_df_sorted['EventScore'] * 100 / weight_sum
            
            # Create time series plot
            fig = px.line(
                kpi_df_sorted,
                x='Date',
                y='EventScore',
                color='Leader',
                markers=True,
                title='Leader Performance Trend',
                template='plotly_white'
            )
            
            fig.update_layout(
                xaxis_title='Date',
                yaxis_title='Performance Score',
                legend_title='Leader',
                height=450,
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show the most improved leader
            if len(kpi_df_sorted['Leader'].unique()) > 1:
                # Calculate the average score for the first half and second half of events for each leader
                leaders = kpi_df_sorted['Leader'].unique()
                improvements = []
                
                for leader in leaders:
                    leader_data = kpi_df_sorted[kpi_df_sorted['Leader'] == leader]
                    if len(leader_data) >= 2:  # Need at least 2 events to measure improvement
                        midpoint = len(leader_data) // 2
                        first_half_avg = leader_data.iloc[:midpoint]['EventScore'].mean()
                        second_half_avg = leader_data.iloc[midpoint:]['EventScore'].mean()
                        improvement = second_half_avg - first_half_avg
                        improvements.append((leader, improvement))
                
                if improvements:
                    most_improved = max(improvements, key=lambda x: x[1])
                    if most_improved[1] > 0:
                        st.markdown(f"""
                        <div style="background-color: var(--color-info-bg); padding: 15px; border-radius: var(--border-radius); margin-top: 15px;">
                            <h4 style="margin-top: 0; color: var(--color-text);">🚀 Most Improved: {most_improved[0]}</h4>
                            <p style="color: var(--color-text-secondary);">
                                {most_improved[0]} has shown the greatest improvement over time, with a score increase of {most_improved[1]:.1f} points!
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
    
    with tab3:
        # Site performance analysis
        st.markdown("#### Performance by Site")
        st.markdown("""
        <div style="background-color: var(--color-info-bg); padding: 15px; border-radius: var(--border-radius); margin-bottom: 15px;">
            <p style="margin-bottom: 8px;">This analysis shows how each leader performs at different sites:</p>
            <ul style="margin-bottom: 0;">
                <li><strong>Heatmap</strong>: The color intensity shows performance level (red-yellow-green)</li>
                <li><strong>Numbers</strong>: Performance scores (0-100) at each site</li>
                <li><strong>Best Leaders</strong>: The top-performing leader for each site</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if 'Site' in kpi_df.columns and not kpi_df.empty:
            # Calculate average performance by site and leader
            site_performance = kpi_df.groupby(['Site', 'Leader']).agg({
                'EargymPromotion': 'mean',
                'Crossbooking': 'mean',
                'BOTDandEODFilled': 'mean',
                'PhotosVideosTestimonials': 'mean',
                'XraysAndDentalNotesUploaded': 'mean',
                'id': 'count'
            }).reset_index().rename(columns={'id': 'EventCount'})
            
            # Calculate a performance score for each site/leader combination
            # Using the same formula as the main performance score
            max_eargym = max(1.0, kpi_df['EargymPromotion'].max())  # Ensure non-zero divisor
            max_crossbooking = max(1.0, kpi_df['Crossbooking'].max())  # Ensure non-zero divisor
            max_photos = max(1.0, kpi_df['PhotosVideosTestimonials'].max())  # Ensure non-zero divisor
            
            site_performance['NormalizedEargymPromotion'] = site_performance['EargymPromotion'] / max_eargym
            site_performance['NormalizedCrossbooking'] = site_performance['Crossbooking'] / max_crossbooking
            site_performance['NormalizedPhotosVideosTestimonials'] = site_performance['PhotosVideosTestimonials'] / max_photos
            
            # Create weighted score - Make sure weights are valid
            weight_sum = sum(weights.values())
            if weight_sum > 0:  # Avoid division by zero
                site_performance['SiteScore'] = (
                    site_performance['NormalizedEargymPromotion'] * weights['EargymPromotion'] +
                    site_performance['NormalizedCrossbooking'] * weights['Crossbooking'] +
                    site_performance['BOTDandEODFilled'] * weights['BOTDandEODFilled'] +
                    site_performance['NormalizedPhotosVideosTestimonials'] * weights['PhotosVideosTestimonials'] +
                    site_performance['XraysAndDentalNotesUploaded'] * weights['XraysAndDentalNotesUploaded']
                ) * 100 / weight_sum
            else:
                # Fallback if weights sum to zero
                site_performance['SiteScore'] = 50  # Set a default mid-range score if weights are invalid
            
            # Create a heatmap of leader performance by site
            pivot_df = site_performance.pivot_table(
                index='Leader',
                columns='Site',
                values='SiteScore',
                aggfunc='mean'
            ).fillna(0) # Fill NaN with 0, for sites a leader hasn't worked at
            
            # Create heatmap with improved styling
            fig = px.imshow(
                pivot_df,
                text_auto=True, # Let Plotly handle text display for zeros and non-zeros
                aspect='auto',
                color_continuous_scale='RdYlGn',
                title='Leader Performance by Site',
                color_continuous_midpoint=50,
                labels={'color': 'Score'},
                width=800
            )
            
            fig.update_layout(
                xaxis_title='Site',
                yaxis_title='Leader',
                coloraxis_colorbar=dict(
                    title='Score',
                    tickvals=[0, 25, 50, 75, 100],
                    ticktext=['0', '25', '50', '75', '100'],
                    lenmode='fraction',
                    len=0.75
                ),
                height=300 + 30 * len(pivot_df),
                margin=dict(l=50, r=50, t=80, b=50),
                font=dict(size=13)
            )
            
            # Improve text visibility on the heatmap
            fig.update_traces(
                texttemplate='%{z:.1f}', # Use %{z:.1f} to display the heatmap value
                textfont=dict(color='black', size=12, family='Arial'),
                showscale=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add interpretation tips
            if len(pivot_df) > 0 and len(pivot_df.columns) > 0:
                best_site_overall = pivot_df.mean().idxmax()
                best_leader_overall = pivot_df.mean(axis=1).idxmax()
                
                # Calculate site-leader pairs with highest scores
                flat_scores = []
                for leader in pivot_df.index:
                    for site in pivot_df.columns:
                        score = pivot_df.loc[leader, site]
                        if score > 0:  # Only include non-zero scores
                            flat_scores.append((leader, site, score))
                
                # Sort by score descending
                flat_scores.sort(key=lambda x: x[2], reverse=True)
                
                # Get top 3 pairs
                top_pairs = flat_scores[:3] if len(flat_scores) >= 3 else flat_scores
                
                st.markdown("#### Key Insights")
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: var(--border-radius); margin: 15px 0;">
                    <p><strong>Overall Best Performing Site:</strong> {best_site_overall if best_site_overall else 'N/A'}</p>
                    <p><strong>Overall Best Performing Leader:</strong> {best_leader_overall if best_leader_overall else 'N/A'}</p>
                    <p><strong>Top Performing Site-Leader Combinations:</strong></p>
                    <ol>
                """, unsafe_allow_html=True)
                
                for i, (leader, site, score) in enumerate(top_pairs):
                    st.markdown(f"""
                    <li><strong>{leader}</strong> at <strong>{site}</strong>: {score:.1f} points</li>
                    """, unsafe_allow_html=True)
                
                st.markdown("""
                    </ol>
                </div>
                """, unsafe_allow_html=True)
                
                # Add recommendations based on data
                st.markdown(f"""
                <div style="background-color: var(--color-info-bg); padding: 15px; border-radius: var(--border-radius); margin: 15px 0;">
                    <h5 style="margin-top: 0;">Recommendations:</h5>
                    <ul>
                        <li>Consider scheduling <strong>{best_leader_overall}</strong> for high-priority sites when possible</li>
                        <li>Analyze what makes the top-performing combinations successful</li>
                        <li>Use the best practices from high-scoring leader-site combinations to improve others</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            
            # Show best leader for each site
            site_best_leaders = site_performance.sort_values('SiteScore', ascending=False).groupby('Site').first().reset_index()
            
            st.markdown("#### Best Leader by Site")
            st.markdown("These leaders have the highest performance scores at each site:")
            
            # Create a nice looking table
            col1, col2 = st.columns(2)
            with col1:
                if len(site_best_leaders) > 0:
                    for i, row in site_best_leaders.iloc[:len(site_best_leaders)//2 + len(site_best_leaders)%2].iterrows():
                        st.markdown(f"""
                        <div style="background-color: var(--color-card); padding: 12px; border-radius: var(--border-radius); margin-bottom: 10px; box-shadow: var(--box-shadow);">
                            <div style="color: var(--color-text-secondary); font-size: 0.9rem;"><strong>Site:</strong> {row['Site']}</div>
                            <div style="font-weight: 500; font-size: 1.1rem; color: var(--color-text); display: flex; align-items: center; margin-top: 4px;">
                                <span style="margin-right: 8px;">👑</span> {row['Leader']}
                            </div>
                            <div style="color: var(--color-accent); font-size: 1rem; margin-top: 4px;">Score: {row['SiteScore']:.1f}</div>
                            <div style="color: var(--color-text-secondary); font-size: 0.8rem; margin-top: 4px;">Based on {int(row['EventCount'])} events</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            with col2:
                if len(site_best_leaders) > 0:
                    for i, row in site_best_leaders.iloc[len(site_best_leaders)//2 + len(site_best_leaders)%2:].iterrows():
                        st.markdown(f"""
                        <div style="background-color: var(--color-card); padding: 12px; border-radius: var(--border-radius); margin-bottom: 10px; box-shadow: var(--box-shadow);">
                            <div style="color: var(--color-text-secondary); font-size: 0.9rem;"><strong>Site:</strong> {row['Site']}</div>
                            <div style="font-weight: 500; font-size: 1.1rem; color: var(--color-text); display: flex; align-items: center; margin-top: 4px;">
                                <span style="margin-right: 8px;">👑</span> {row['Leader']}
                            </div>
                            <div style="color: var(--color-accent); font-size: 1rem; margin-top: 4px;">Score: {row['SiteScore']:.1f}</div>
                            <div style="color: var(--color-text-secondary); font-size: 0.8rem; margin-top: 4px;">Based on {int(row['EventCount'])} events</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
            # Add an analysis of opportunities for improvement
            st.markdown("#### Opportunities for Improvement")
            
            # Create a dataframe to identify underperforming leader-site combinations
            if len(pivot_df) > 1 and len(pivot_df.columns) > 1:  # Only show if we have multiple leaders and sites
                improvement_opportunities = []
                
                for leader in pivot_df.index:
                    # Get this leader's average score
                    leader_avg = pivot_df.loc[leader].mean()
                    
                    for site in pivot_df.columns:
                        # Get this site's average score across all leaders
                        site_avg = pivot_df[site].mean()
                        
                        # Get this specific leader-site score
                        leader_site_score = pivot_df.loc[leader, site]
                        
                        # If this leader-site combo is significantly below both the leader's average and the site's average
                        if leader_site_score < min(leader_avg * 0.8, site_avg * 0.8) and leader_site_score > 0:
                            improvement_opportunities.append({
                                'Leader': leader,
                                'Site': site,
                                'Score': leader_site_score,
                                'Leader Avg': leader_avg,
                                'Site Avg': site_avg,
                                'Gap': min(leader_avg - leader_site_score, site_avg - leader_site_score)
                            })
                
                if improvement_opportunities:
                    # Sort by gap (largest first)
                    improvement_opportunities = sorted(improvement_opportunities, key=lambda x: x['Gap'], reverse=True)
                    
                    for i, opp in enumerate(improvement_opportunities[:3]):  # Show top 3 opportunities
                        st.markdown(f"""
                        <div style="background-color: #fff3cd; padding: 12px; border-radius: var(--border-radius); margin-bottom: 10px;">
                            <div style="font-weight: 500;">Leader <strong>{opp['Leader']}</strong> at <strong>{opp['Site']}</strong></div>
                            <div>Current score: {opp['Score']:.1f} (Leader's average: {opp['Leader Avg']:.1f}, Site average: {opp['Site Avg']:.1f})</div>
                            <div style="margin-top: 8px;">This combination is performing below both the leader's average and the site's average. Consider additional training or resources.</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No significant performance gaps identified between leaders and sites.")
        else:
            st.warning("Site information not available in the data. Make sure your KPI data includes site information.")
        
        # Add site-specific filtering option
        if 'Site' in kpi_df.columns and not kpi_df.empty:
            st.markdown("#### Analyze a Specific Site")
            selected_site = st.selectbox("Select a site to analyze in detail:", options=['All Sites'] + list(kpi_df['Site'].unique()))
            
            if selected_site != 'All Sites':
                # Filter data for the selected site
                site_filtered_df = kpi_df[kpi_df['Site'] == selected_site]
                
                # Calculate leader scores for this site only
                site_leader_scores = calculate_performance_score(site_filtered_df, weights=weights)
                
                if not site_leader_scores.empty:
                    st.markdown(f"##### Performance at {selected_site}")
                    
                    # Format the data for display
                    site_display_df = site_leader_scores.copy()
                    site_display_df = site_display_df.sort_values('PerformanceScore', ascending=False).reset_index()
                    
                    # Format columns
                    site_display_df['PerformanceScore'] = site_display_df['PerformanceScore'].round(1)
                    site_display_df['EventCount'] = site_display_df['EventCount'].astype(int)
                    
                    # Create a clean table
                    cols = st.columns(len(site_display_df))
                    for i, (_, leader) in enumerate(site_display_df.iterrows()):
                        with cols[i]:
                            st.markdown(f"""
                            <div style="text-align: center; background-color: var(--color-card); padding: 15px; border-radius: var(--border-radius); box-shadow: var(--box-shadow);">
                                <div style="font-weight: 500; color: var(--color-text); margin-top: 10px;">{leader['Leader']}</div>
                                <div style="font-size: 1.5rem; color: var(--color-accent); margin-top: 5px;">{leader['PerformanceScore']:.1f}</div>
                                <div style="color: var(--color-text-secondary); font-size: 0.8rem;">Based on {leader['EventCount']} events</div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info(f"No performance data available for {selected_site}.")
            else:
                st.info("Select a specific site from the dropdown to see detailed performance metrics.")
        
        # Add site comparison tool
        if 'Site' in kpi_df.columns and len(kpi_df['Site'].unique()) > 1:
            st.markdown("#### Compare Sites")
            selected_sites = st.multiselect("Select sites to compare:", options=kpi_df['Site'].unique(), 
                                           default=list(kpi_df['Site'].unique())[:2] if len(kpi_df['Site'].unique()) >= 2 else [])
            
            if len(selected_sites) >= 2:
                # Filter data for selected sites
                sites_filtered_df = kpi_df[kpi_df['Site'].isin(selected_sites)]
                
                # Group by site and calculate metrics
                site_metrics = sites_filtered_df.groupby('Site').agg({
                    'EargymPromotion': 'mean',
                    'Crossbooking': 'mean', 
                    'BOTDandEODFilled': 'mean',
                    'PhotosVideosTestimonials': 'mean',
                    'XraysAndDentalNotesUploaded': 'mean',
                    'id': 'count'
                }).reset_index()
                
                # Create a bar chart to compare sites
                fig = px.bar(
                    site_metrics,
                    x='Site',
                    y=['EargymPromotion', 'Crossbooking', 'BOTDandEODFilled', 'PhotosVideosTestimonials', 'XraysAndDentalNotesUploaded'],
                    title='Site Comparison by KPI Category',
                    labels={
                        'value': 'Average Score',
                        'variable': 'KPI Category',
                        'Site': 'Site'
                    },
                    barmode='group',
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                
                # Update layout
                fig.update_layout(
                    xaxis_title='Site',
                    yaxis_title='Average Score',
                    legend_title='KPI Category',
                    height=450,
                    margin=dict(l=50, r=50, t=80, b=50)
                )
                
                # Rename legend items to be more readable
                fig.for_each_trace(lambda t: t.update(name=t.name.replace('EargymPromotion', 'Eargym Promo')
                                                     .replace('Crossbooking', 'Cross-booking')
                                                     .replace('BOTDandEODFilled', 'BOTD/EOD Forms')
                                                     .replace('PhotosVideosTestimonials', 'Media Posted')
                                                     .replace('XraysAndDentalNotesUploaded', 'Documentation')))
                
                st.plotly_chart(fig, use_container_width=True)
            elif len(selected_sites) == 1:
                st.info("Please select at least one more site to compare.")
            else:
                st.info("Please select sites to compare.")
    
    # Raw data and export
    with st.expander("View Raw Data"):
        st.dataframe(kpi_df, use_container_width=True)
        
        # Add button to download data as CSV
        csv = kpi_df.to_csv(index=False)
        st.download_button(
            label="Download Data as CSV",
            data=csv,
            file_name="leader_performance_data.csv",
            mime="text/csv"
        )

def generate_sample_kpi_data():
    """Generate sample KPI data for demonstration purposes"""
    from datetime import datetime, timedelta
    
    # Create sample leaders and sites
    leaders = ['John Smith', 'Maria Garcia', 'James Johnson', 'Sarah Williams']
    sites = ['Downtown Clinic', 'Eastside Center', 'Westview Hospital', 'Northside Medical']
    
    # Start date for events
    start_date = datetime(2025, 1, 1)
    
    # Create 50 sample events
    records = []
    for i in range(50):
        leader = np.random.choice(leaders)
        site = np.random.choice(sites)
        event_date = start_date + timedelta(days=i // 2)  # Spread events over time
        
        # Generate KPI metrics with some variability
        eargym = max(0, np.random.poisson(3))  # Average 3 Eargym promotions
        crossbook = max(0, np.random.poisson(3))  # Average 3 crossbookings
        botd_eod = 1 if np.random.random() > 0.2 else 0  # 80% chance of completing forms
        photos = max(0, np.random.poisson(4))  # Average 4 photos/videos
        docs = 1 if np.random.random() > 0.15 else 0  # 85% chance of completing docs
        
        records.append({
            'id': f'sample{i}',
            'Leader': leader,
            'Site': site,
            'Date': event_date,
            'EargymPromotion': eargym,
            'Crossbooking': crossbook,
            'BOTDandEODFilled': botd_eod,
            'PhotosVideosTestimonials': photos,
            'XraysAndDentalNotesUploaded': docs
        })
    
    return pd.DataFrame(records) 