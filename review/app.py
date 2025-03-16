"""
SkillLab Web Review Interface
Streamlit application for human review of flagged documents
"""

import os
import sys
import json
import shutil
from pathlib import Path
import base64
from typing import Dict, List, Any, Tuple, Optional
import sqlite3

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import pdf2image
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from utils.logger import setup_logger
from config import get_config
from api.review import (
    get_review_queue, 
    get_document_details, 
    get_dashboard_stats,
    get_performance_stats, 
    get_review_history, 
    get_error_analysis,
    approve_document, 
    reject_document, 
    save_document_json,
    load_documents_from_filesystem,
    sync_review_data
)

# UI-related imports
from ui.common.factory import UIComponentFactory, UIType
from ui.common.adapter import ReviewAdapter

# Setup logger
logger = setup_logger("review_app")

class ReviewApp:
    """Streamlit application for human review of flagged documents"""
    
    def __init__(self, ui_type: UIType = UIType.WEB):
        """
        Initialize the review app
        
        Args:
            ui_type: Type of UI to use (CLI or WEB)
        """
        config = get_config()
        self.data_dir = os.path.join(project_root, "data")
        self.output_dir = os.path.join(self.data_dir, "output")
        self.input_dir = os.path.join(self.data_dir, "input")
        self.review_dir = os.path.join(project_root, "review", "reviewed")
        self.ui_type = ui_type
        
        # Ensure review directory exists
        os.makedirs(self.review_dir, exist_ok=True)
        
        # Initialize UI components using the adapter
        self.review_adapter = ReviewAdapter(ui_type)
        
        # Initialize session state
        if 'current_document' not in st.session_state:
            st.session_state.current_document = None
        if 'current_pdf' not in st.session_state:
            st.session_state.current_pdf = None
        if 'current_json' not in st.session_state:
            st.session_state.current_json = None
        if 'current_images' not in st.session_state:
            st.session_state.current_images = []
        if 'review_mode' not in st.session_state:
            st.session_state.review_mode = False
        if 'review_queue' not in st.session_state:
            st.session_state.review_queue = []
        if 'issue_filter' not in st.session_state:
            st.session_state.issue_filter = 'All'
        if 'display_images' not in st.session_state:
            st.session_state.display_images = {}
    
    def render_sidebar(self):
        """Render the sidebar navigation and filters"""
        st.sidebar.title("SkillLab Review")
        
        # Navigation
        page = st.sidebar.radio("Navigation", ["Dashboard", "Review Documents", "Performance Analysis"])
        
        # Filters for the review queue (when on review page)
        if page == "Review Documents":
            st.sidebar.header("Filters")
            
            # Get issue types from API via existing documents
            issue_types = set()
            for doc in st.session_state.review_queue:
                for issue in doc.get('issues', []):
                    if 'type' in issue:
                        issue_types.add(issue['type'])
            
            issue_types = ['All'] + sorted(list(issue_types))
            
            # Issue type filter
            selected_issue = st.sidebar.selectbox(
                "Filter by issue type",
                issue_types,
                index=0,
                key="issue_filter"
            )
            
            # Refresh button
            if st.sidebar.button("Refresh Queue"):
                self.load_review_queue(issue_filter=selected_issue)
                st.rerun()
        
        # Return the selected page
        return page
    
    def load_review_queue(self, issue_filter: str = 'All'):
        """
        Load the review queue from the database
        
        Args:
            issue_filter: Filter by issue type (All for no filter)
        """
        # Sync databases first
        sync_review_data()
        
        # Get documents from API
        documents = get_review_queue(issue_filter)
        st.session_state.review_queue = documents
        st.session_state.issue_filter = issue_filter
        
        # Update UI with the new queue data
        self.review_adapter.update_queue(documents)
        
        logger.info(f"Loaded {len(documents)} documents for review (filter: {issue_filter})")
    
    def load_document(self, document_id: str):
        """
        Load a document for review
        
        Args:
            document_id: Document ID to load
        """
        # Use the adapter to load document details
        document = self.review_adapter.load_document(document_id)
        
        if not document:
            st.error(f"Document {document_id} not found")
            return False
        
        st.session_state.current_document = document
        
        # Load PDF file
        pdf_path = os.path.join(self.input_dir, document.get('filename', ''))
        if os.path.exists(pdf_path):
            st.session_state.current_pdf = pdf_path
        else:
            st.session_state.current_pdf = None
            st.warning(f"PDF file not found: {pdf_path}")
        
        # Load JSON data
        if 'json_data' in document:
            st.session_state.current_json = document
        else:
            # Try to load from json_results
            json_path = os.path.join(self.output_dir, "json_results", f"{document_id}_structured.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    st.session_state.current_json = {"json_data": json_data}
            else:
                st.session_state.current_json = None
                st.warning(f"JSON data not found for document: {document_id}")
        
        # Load images
        st.session_state.current_images = []
        st.session_state.display_images = {}
        
        # Check for image paths in various locations
        image_paths = []
        if 'image_paths' in document and document['image_paths']:
            image_paths = document['image_paths']
        elif 'image_path' in document and document['image_path']:
            image_paths = document['image_path']
            
        if image_paths:
            # If image paths are stored in the document
            for path in image_paths:
                if os.path.exists(path):
                    img = Image.open(path)
                    st.session_state.current_images.append(img)
                    st.session_state.display_images[os.path.basename(path)] = img
        elif st.session_state.current_pdf:
            # Convert PDF to images if needed
            try:
                images = pdf2image.convert_from_path(st.session_state.current_pdf, dpi=300)
                st.session_state.current_images = images
                
                # Store in display images
                for i, img in enumerate(images):
                    st.session_state.display_images[f"page_{i+1}.png"] = img
            except Exception as e:
                logger.error(f"Error converting PDF to images: {str(e)}")
        
        # Update navigation with current document
        self.review_adapter.update_document_nav(document_id, st.session_state.review_queue)
        
        st.session_state.review_mode = True
        logger.info(f"Loaded document {document_id} for review")
        return True
    
    def render_dashboard(self):
        """Render the dashboard page using UI components"""
        st.title("SkillLab Dashboard")
        
        # Get dashboard from the adapter
        dashboard = self.review_adapter.get_dashboard()
        
        # Refresh dashboard data
        self.review_adapter.refresh()
        
        # Get statistics from API
        stats = get_dashboard_stats()
        
        # Create columns for key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Documents", stats.get('total_documents', 0))
        
        with col2:
            st.metric("Flagged for Review", stats.get('flagged_documents', 0))
        
        with col3:
            st.metric("Reviewed", stats.get('reviewed_documents', 0))
        
        with col4:
            pending = stats.get('flagged_documents', 0) - stats.get('reviewed_documents', 0)
            st.metric("Pending Review", pending)
        
        # Show pipeline progress
        st.subheader("Pipeline Progress")
        
        pipeline_stats = stats.get('pipeline_stats', {})
        progress_df = pd.DataFrame({
            'Stage': ['OCR', 'JSON Generation', 'Validation', 'Dataset', 'Training'],
            'Completed': [
                pipeline_stats.get('ocr_complete', 0),
                pipeline_stats.get('json_complete', 0),
                pipeline_stats.get('validated', 0),
                pipeline_stats.get('dataset_ready', 0),
                pipeline_stats.get('training_complete', 0)
            ],
            'Total': stats.get('total_documents', 0)
        })
        
        progress_df['Progress'] = (progress_df['Completed'] / progress_df['Total'] * 100).fillna(0).round(1)
        
        # Create progress component
        progress_component = UIComponentFactory.create_component(
            "progress", self.ui_type, "pipeline_progress", "Pipeline Progress"
        )
        
        # Display progress bars
        for i, row in progress_df.iterrows():
            progress_data = {
                "current": row['Completed'],
                "total": row['Total'],
                "message": f"{row['Stage']}: {row['Progress']}%"
            }
            if progress_component:
                progress_component.render(progress_data)
            else:
                # Fallback to standard Streamlit
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.progress(float(row['Progress']) / 100)
                with col2:
                    st.write(f"{row['Stage']}: {row['Progress']}%")
        
        # Show issue breakdown
        st.subheader("Issue Breakdown")
        
        # Create chart component
        chart_component = UIComponentFactory.create_component(
            "chart", self.ui_type, "issue_chart", "Issue Breakdown"
        )
        
        issue_stats = stats.get('issue_stats', {})
        if issue_stats:
            # Create chart data
            chart_data = {
                "type": "pie",
                "labels": list(issue_stats.keys()),
                "values": list(issue_stats.values()),
                "title": "Issues by Type"
            }
            
            if chart_component:
                chart_component.render(chart_data)
            else:
                # Fallback to standard Streamlit
                fig, ax = plt.subplots(figsize=(10, 6))
                labels = list(issue_stats.keys())
                sizes = list(issue_stats.values())
                
                ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
                ax.axis('equal')  # Equal aspect ratio ensures pie is circular
                
                st.pyplot(fig)
        else:
            st.info("No issues reported yet")
        
        # Show documents awaiting review
        st.subheader("Documents Awaiting Review")
        
        # Get documents from API
        queue_docs = get_review_queue('All', limit=5)
        
        if queue_docs:
            # Create table component
            table_component = UIComponentFactory.create_component(
                "table", self.ui_type, "queue_table", "Review Queue"
            )
            
            # Create table data
            headers = ["ID", "Filename", "Issues", "OCR Conf.", "JSON Conf."]
            rows = []
            
            for doc in queue_docs:
                issue_types = ", ".join([issue["type"] for issue in doc.get("issues", [])])
                
                rows.append([
                    doc.get("id", ""),
                    doc.get("filename", ""),
                    issue_types,
                    f"{doc.get('ocr_confidence', 0):.1f}%",
                    f"{doc.get('json_confidence', 0):.1f}%"
                ])
            
            table_data = {
                "headers": headers,
                "rows": rows
            }
            
            if table_component:
                table_component.render(table_data)
            else:
                # Fallback to standard Streamlit
                df = pd.DataFrame(rows, columns=headers)
                st.dataframe(df)
            
            # Button to go to review page
            if st.button("Review Documents"):
                st.session_state.review_queue = queue_docs
                st.session_state.page = "Review Documents"
                st.rerun()
        else:
            st.info("No documents waiting for review")
    
    def render_review_page(self):
        """Render the document review page using UI components"""
        st.title("Review Documents")
        
        # Check if review queue is loaded
        if not st.session_state.review_queue:
            self.load_review_queue(st.session_state.issue_filter)
        
        # Display the queue using UI components
        st.subheader("Review Queue")
        
        if not st.session_state.review_queue:
            st.info("No documents in the review queue")
            return
        
        # Create a table component
        table_component = UIComponentFactory.create_component(
            "table", self.ui_type, "review_queue", "Review Queue"
        )
        
        # Create table data
        headers = ["ID", "Filename", "Issues", "OCR Conf.", "JSON Conf."]
        rows = []
        
        for doc in st.session_state.review_queue:
            issue_types = ", ".join([issue["type"] for issue in doc.get("issues", [])])
            
            rows.append([
                doc.get("id", ""),
                doc.get("filename", ""),
                issue_types,
                f"{doc.get('ocr_confidence', 0):.1f}%",
                f"{doc.get('json_confidence', 0):.1f}%"
            ])
        
        table_data = {
            "headers": headers,
            "rows": rows
        }
        
        if table_component:
            table_component.render(table_data)
        else:
            # Fallback to standard Streamlit
            df = pd.DataFrame(rows, columns=headers)
            st.dataframe(df)
        
        # Select document for review
        document_id = st.selectbox(
            "Select document to review",
            options=[doc['id'] for doc in st.session_state.review_queue],
            format_func=lambda x: f"{x} - {next((doc['filename'] for doc in st.session_state.review_queue if doc['id'] == x), x)}"
        )
        
        # Button to load the selected document
        if st.button("Load Document"):
            self.load_document(document_id)
        
        # Check if in review mode
        if st.session_state.review_mode and st.session_state.current_document:
            self.render_document_review()
    
    def get_document_issues(self):
        """Get issues for the current document"""
        if not st.session_state.current_document:
            return []
        
        issues = st.session_state.current_document.get('issues', [])
        return issues
    
    def render_document_review(self):
        """Render the document review interface"""
        st.header(f"Reviewing: {st.session_state.current_document.get('filename', 'Unknown')}")
        
        # Display issues
        issues = self.get_document_issues()
        
        # Create alert component for issues
        alert_component = UIComponentFactory.create_component(
            "alert", self.ui_type, "issue_alerts", "Document Issues"
        )
        
        if issues:
            st.subheader("Issues")
            for issue in issues:
                if alert_component:
                    alert_component.warning(f"{issue.get('type', 'Unknown issue')}: {issue.get('details', '')}")
                else:
                    # Fallback to standard Streamlit
                    st.warning(f"{issue.get('type', 'Unknown issue')}: {issue.get('details', '')}")
        
        # Create tabs for document view and JSON editor
        tab1, tab2 = st.tabs(["Document View", "JSON Editor"])
        
        with tab1:
            self.render_document_view()
        
        with tab2:
            self.render_json_editor()
        
        # Review actions
        st.subheader("Review Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Approve", type="primary"):
                self.approve_document()
        
        with col2:
            if st.button("Reject", type="secondary"):
                self.reject_document()
        
        with col3:
            if st.button("Save Changes"):
                self.save_document_changes()
    
    def render_document_view(self):
        """Render the document view with resume images"""
        if not st.session_state.current_images:
            st.info("No images available for this document")
            return
        
        # Display images with page selection
        if len(st.session_state.current_images) > 1:
            page_number = st.slider("Page", 1, len(st.session_state.current_images), 1)
            img = st.session_state.current_images[page_number - 1]
        else:
            img = st.session_state.current_images[0]
        
        # Display the image
        st.image(img, caption="Resume Image", use_column_width=True)
    
    def render_json_editor(self):
        """Render the JSON editor for correction using UI components"""
        if not st.session_state.current_json:
            st.info("No JSON data available for this document")
            return
        
        # Extract the main JSON data
        json_data = st.session_state.current_json.get('json_data', {})
        
        # Create form component
        form_component = UIComponentFactory.create_component(
            "form", self.ui_type, "json_editor", "JSON Editor"
        )
        
        # Create form fields
        fields = {
            "name": {
                "type": "text",
                "label": "Name",
                "required": True,
                "default": json_data.get('Name', "")
            },
            "email": {
                "type": "text",
                "label": "Email",
                "required": True,
                "default": json_data.get('Email', "")
            },
            "phone": {
                "type": "text",
                "label": "Phone",
                "required": True,
                "default": json_data.get('Phone', "")
            },
            "position": {
                "type": "text",
                "label": "Current Position",
                "required": False,
                "default": json_data.get('Current_Position', "")
            },
            "skills": {
                "type": "textarea",
                "label": "Skills (comma separated)",
                "required": False,
                "default": ", ".join(json_data.get('Skills', []))
            }
        }
        
        # Add experience entries as fields
        experience_entries = json_data.get('Experience', [])
        for i, exp in enumerate(experience_entries):
            fields[f"company_{i}"] = {
                "type": "text",
                "label": f"Company {i+1}",
                "required": False,
                "default": exp.get('company', '')
            }
            fields[f"title_{i}"] = {
                "type": "text",
                "label": f"Title {i+1}",
                "required": False,
                "default": exp.get('title', '')
            }
            fields[f"years_{i}"] = {
                "type": "text",
                "label": f"Years {i+1}",
                "required": False,
                "default": exp.get('years', '')
            }
        
        form_data = {
            "fields": fields,
            "submit_label": "Update JSON",
            "show_reset": True
        }
        
        if form_component:
            # Render the form
            form_component.render(form_data)
            
            # Check if form is submitted
            if hasattr(form_component, 'is_submitted') and form_component.is_submitted():
                # Get form values
                form_values = form_component.get_values()
                
                # Process form values
                name = form_values.get("name", "")
                email = form_values.get("email", "")
                phone = form_values.get("phone", "")
                position = form_values.get("position", "")
                
                # Parse skills
                skills_str = form_values.get("skills", "")
                skills_list = [s.strip() for s in skills_str.split(',') if s.strip()]
                
                # Process experience entries
                updated_experience = []
                for i in range(len(experience_entries)):
                    company = form_values.get(f"company_{i}", "")
                    title = form_values.get(f"title_{i}", "")
                    years = form_values.get(f"years_{i}", "")
                    
                    if company or title or years:
                        updated_experience.append({
                            'company': company,
                            'title': title,
                            'years': years
                        })
                
                # Update JSON
                updated_json = {
                    'Name': name,
                    'Email': email,
                    'Phone': phone,
                    'Current_Position': position,
                    'Skills': skills_list,
                    'Experience': updated_experience
                }
                
                # Update session state
                if 'json_data' in st.session_state.current_json:
                    st.session_state.current_json['json_data'] = updated_json
                else:
                    st.session_state.current_json = {'json_data': updated_json}
                
                # Create alert component
                alert_component = UIComponentFactory.create_component(
                    "alert", self.ui_type, "json_alert", "JSON Update"
                )
                
                if alert_component:
                    alert_component.success("JSON updated successfully")
                else:
                    st.success("JSON updated successfully")
        else:
            # Fallback to standard Streamlit form
            with st.form(key='json_editor'):
                # Personal information fields
                st.subheader("Personal Information")
                
                # Name field
                name = st.text_input("Name", value=json_data.get('Name') or "")
                
                col1, col2 = st.columns(2)
                with col1:
                    email = st.text_input("Email", value=json_data.get('Email') or "")
                with col2:
                    phone = st.text_input("Phone", value=json_data.get('Phone') or "")
                
                current_position = st.text_input("Current Position", value=json_data.get('Current_Position') or "")
                
                # Skills
                st.subheader("Skills")
                skills_str = ", ".join(json_data.get('Skills', []))
                skills = st.text_area("Skills (comma separated)", value=skills_str)
                
                # Experience entries
                st.subheader("Experience")
                
                experience_entries = json_data.get('Experience', [])
                updated_experience = []
                
                for i, exp in enumerate(experience_entries):
                    st.markdown(f"**Experience Entry {i+1}**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        company = st.text_input(f"Company {i+1}", value=exp.get('company', ''), key=f"company_{i}")
                    with col2:
                        title = st.text_input(f"Title {i+1}", value=exp.get('title', ''), key=f"title_{i}")
                    
                    years = st.text_input(f"Years {i+1}", value=exp.get('years', ''), key=f"years_{i}")
                    
                    # Add to updated experience if not empty
                    if company or title or years:
                        updated_experience.append({
                            'company': company,
                            'title': title,
                            'years': years
                        })
                    
                    st.markdown("---")
                
                # Add new experience entry button
                add_experience = st.checkbox("Add New Experience Entry")
                
                if add_experience:
                    st.markdown("**New Experience Entry**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        new_company = st.text_input("Company", value='', key="new_company")
                    with col2:
                        new_title = st.text_input("Title", value='', key="new_title")
                    
                    new_years = st.text_input("Years", value='', key="new_years")
                    
                    # Add to updated experience if not empty
                    if new_company or new_title or new_years:
                        updated_experience.append({
                            'company': new_company,
                            'title': new_title,
                            'years': new_years
                        })
                
                # Submit button
                submit_button = st.form_submit_button(label='Update JSON')
                
                if submit_button:
                    # Parse skills (split by comma and strip whitespace)
                    skills_list = [s.strip() for s in skills.split(',') if s.strip()]
                    
                    # Update JSON
                    updated_json = {
                        'Name': name,
                        'Email': email,
                        'Phone': phone,
                        'Current_Position': current_position,
                        'Skills': skills_list,
                        'Experience': updated_experience
                    }
                    
                    # Update session state
                    if 'json_data' in st.session_state.current_json:
                        st.session_state.current_json['json_data'] = updated_json
                    else:
                        st.session_state.current_json = {'json_data': updated_json}
                    
                    st.success("JSON updated successfully")
    
    def approve_document(self):
        """Approve the document and save changes"""
        if not st.session_state.current_document or not st.session_state.current_json:
            st.error("No document loaded for review")
            return
        
        document_id = st.session_state.current_document.get('id')
        
        try:
            # Save the current JSON state
            if self.save_document_changes():
                # Approve document through API
                success = approve_document(document_id, changes_made=True)
                
                # Create alert component
                alert_component = UIComponentFactory.create_component(
                    "alert", self.ui_type, "approval_alert", "Document Approval"
                )
                
                if success:
                    if alert_component:
                        alert_component.success(f"Document {document_id} approved successfully")
                    else:
                        st.success(f"Document {document_id} approved successfully")
                    
                    # Reset review mode
                    st.session_state.review_mode = False
                    st.session_state.current_document = None
                    st.session_state.current_pdf = None
                    st.session_state.current_json = None
                    st.session_state.current_images = []
                    
                    # Reload review queue
                    self.load_review_queue(st.session_state.issue_filter)
                    
                    # Rerun to update UI
                    st.rerun()
                else:
                    if alert_component:
                        alert_component.error("Failed to approve document. Please try again.")
                    else:
                        st.error("Failed to approve document. Please try again.")
            else:
                # Create alert component
                alert_component = UIComponentFactory.create_component(
                    "alert", self.ui_type, "save_error", "Save Error"
                )
                
                if alert_component:
                    alert_component.error("Failed to save document changes before approval.")
                else:
                    st.error("Failed to save document changes before approval.")
        
        except Exception as e:
            logger.error(f"Error approving document {document_id}: {str(e)}")
            
            # Create alert component
            alert_component = UIComponentFactory.create_component(
                "alert", self.ui_type, "error_alert", "Error"
            )
            
            if alert_component:
                alert_component.error(f"Error approving document: {str(e)}")
            else:
                st.error(f"Error approving document: {str(e)}")
    
    def reject_document(self):
        """Reject the document with reason"""
        if not st.session_state.current_document:
            st.error("No document loaded for review")
            return
        
        document_id = st.session_state.current_document.get('id')
        
        # Ask for rejection reason - this still uses Streamlit directly
        # since it's part of the interaction flow
        reason = st.text_area("Rejection Reason")
        
        if st.button("Confirm Rejection"):
            try:
                # Reject document through API
                success = reject_document(document_id, reason=reason)
                
                # Create alert component
                alert_component = UIComponentFactory.create_component(
                    "alert", self.ui_type, "rejection_alert", "Document Rejection"
                )
                
                if success:
                    if alert_component:
                        alert_component.success(f"Document {document_id} rejected successfully")
                    else:
                        st.success(f"Document {document_id} rejected successfully")
                    
                    # Reset review mode
                    st.session_state.review_mode = False
                    st.session_state.current_document = None
                    st.session_state.current_pdf = None
                    st.session_state.current_json = None
                    st.session_state.current_images = []
                    
                    # Reload review queue
                    self.load_review_queue(st.session_state.issue_filter)
                    
                    # Rerun to update UI
                    st.rerun()
                else:
                    if alert_component:
                        alert_component.error("Failed to reject document. Please try again.")
                    else:
                        st.error("Failed to reject document. Please try again.")
            
            except Exception as e:
                logger.error(f"Error rejecting document {document_id}: {str(e)}")
                
                # Create alert component
                alert_component = UIComponentFactory.create_component(
                    "alert", self.ui_type, "error_alert", "Error"
                )
                
                if alert_component:
                    alert_component.error(f"Error rejecting document: {str(e)}")
                else:
                    st.error(f"Error rejecting document: {str(e)}")
    
    def save_document_changes(self):
        """Save changes to the document JSON using the adapter"""
        if not st.session_state.current_document or not st.session_state.current_json:
            st.error("No document loaded for review")
            return False
        
        document_id = st.session_state.current_document.get('id')
        
        try:
            # Get the JSON data from session state
            updated_json = st.session_state.current_json.copy()
            
            # Set validation status
            if 'validation' not in updated_json:
                updated_json['validation'] = {}
            
            updated_json['validation']['is_valid'] = True
            updated_json['validation']['reviewed'] = True
            updated_json['resume_id'] = document_id
            
            # Save using adapter
            form_values = {
                "name": updated_json.get('json_data', {}).get('Name', ''),
                "email": updated_json.get('json_data', {}).get('Email', ''),
                "phone": updated_json.get('json_data', {}).get('Phone', ''),
                "position": updated_json.get('json_data', {}).get('Current_Position', ''),
                "skills": ', '.join(updated_json.get('json_data', {}).get('Skills', []))
            }
            
            success = self.review_adapter.save_document(document_id, form_values)
            
            # Create alert component
            alert_component = UIComponentFactory.create_component(
                "alert", self.ui_type, "save_alert", "Save Changes"
            )
            
            if success:
                logger.info(f"Saved changes to document {document_id}")
                
                if alert_component:
                    alert_component.success("Changes saved successfully")
                else:
                    st.success("Changes saved successfully")
                
                return True
            else:
                if alert_component:
                    alert_component.error("Failed to save document changes")
                else:
                    st.error("Failed to save document changes")
                
                return False
        
        except Exception as e:
            logger.error(f"Error saving changes to document {document_id}: {str(e)}")
            
            # Create alert component
            alert_component = UIComponentFactory.create_component(
                "alert", self.ui_type, "error_alert", "Error"
            )
            
            if alert_component:
                alert_component.error(f"Error saving changes: {str(e)}")
            else:
                st.error(f"Error saving changes: {str(e)}")
            
            return False
    
    def render_analysis_page(self):
        """Render the performance analysis page"""
        st.title("Performance Analysis")
        
        # Get performance statistics from API
        stats = get_performance_stats()
        
        # Display key metrics
        st.header("Review Metrics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Reviewed", stats.get('total_reviewed', 0))
        
        with col2:
            st.metric("Approved", stats.get('approved', 0))
        
        with col3:
            st.metric("Rejected", stats.get('rejected', 0))
        
        # Display review history
        st.subheader("Review History")
        
        history = get_review_history()
        if history:
            # Create chart component
            chart_component = UIComponentFactory.create_component(
                "chart", self.ui_type, "history_chart", "Review History"
            )
            
            # Convert to dataframe
            history_df = pd.DataFrame(history)
            
            # Format dates
            if 'timestamp' in history_df.columns:
                history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
                history_df['date'] = history_df['timestamp'].dt.date
            
            # Group by date and status
            if 'date' in history_df.columns and 'status' in history_df.columns:
                daily_stats = history_df.groupby(['date', 'status']).size().unstack(fill_value=0)
                
                # Create chart data
                chart_data = {
                    "type": "bar",
                    "dataframe": daily_stats,
                    "options": {
                        "title": "Review History by Date",
                        "x_label": "Date",
                        "y_label": "Count"
                    }
                }
                
                if chart_component:
                    chart_component.render(chart_data)
                else:
                    # Fallback to standard Streamlit
                    st.bar_chart(daily_stats)
            
            # Show recent reviews
            st.subheader("Recent Reviews")
            
            # Create table component
            table_component = UIComponentFactory.create_component(
                "table", self.ui_type, "review_history", "Recent Reviews"
            )
            
            display_cols = ['document_id', 'status', 'timestamp', 'reason']
            display_df = history_df[display_cols] if all(col in history_df.columns for col in display_cols) else history_df
            
            # Create table data
            headers = list(display_df.columns)
            rows = display_df.head(10).values.tolist()
            
            table_data = {
                "headers": headers,
                "rows": rows
            }
            
            if table_component:
                table_component.render(table_data)
            else:
                # Fallback to standard Streamlit
                st.dataframe(display_df.head(10))
        else:
            st.info("No review history available")
        
        # Display error analysis
        st.header("Error Analysis")
        
        error_stats = get_error_analysis()
        if error_stats and 'issue_counts' in error_stats:
            # Create chart component
            chart_component = UIComponentFactory.create_component(
                "chart", self.ui_type, "error_chart", "Error Analysis"
            )
            
            # Plot issue distribution
            issue_df = pd.DataFrame({
                'Issue': list(error_stats['issue_counts'].keys()),
                'Count': list(error_stats['issue_counts'].values())
            }).sort_values('Count', ascending=False)
            
            # Create chart data
            chart_data = {
                "type": "bar",
                "dataframe": issue_df.set_index('Issue'),
                "options": {
                    "title": "Issues by Type",
                    "x_label": "Issue Type",
                    "y_label": "Count"
                }
            }
            
            if chart_component:
                chart_component.render(chart_data)
            else:
                # Fallback to standard Streamlit
                st.bar_chart(issue_df.set_index('Issue'))
            
            # Show common fields with errors
            if 'field_errors' in error_stats:
                st.subheader("Common Fields with Errors")
                
                # Create table component
                table_component = UIComponentFactory.create_component(
                    "table", self.ui_type, "field_errors", "Field Errors"
                )
                
                field_df = pd.DataFrame({
                    'Field': list(error_stats['field_errors'].keys()),
                    'Error Count': list(error_stats['field_errors'].values())
                }).sort_values('Error Count', ascending=False)
                
                # Create table data
                headers = list(field_df.columns)
                rows = field_df.values.tolist()
                
                table_data = {
                    "headers": headers,
                    "rows": rows
                }
                
                if table_component:
                    table_component.render(table_data)
                else:
                    # Fallback to standard Streamlit
                    st.dataframe(field_df)
        else:
            st.info("No error analysis available")
        
        # Show improvement metrics
        st.header("Pipeline Improvement")
        
        improvement_stats = stats.get('improvement_metrics', {})
        if improvement_stats:
            # Plot improvement over time
            if 'weekly_accuracy' in improvement_stats:
                st.subheader("Weekly Accuracy Trends")
                
                # Create chart component
                chart_component = UIComponentFactory.create_component(
                    "chart", self.ui_type, "accuracy_chart", "Accuracy Trends"
                )
                
                weekly_df = pd.DataFrame(improvement_stats['weekly_accuracy'])
                
                # Create chart data
                chart_data = {
                    "type": "line",
                    "dataframe": weekly_df.set_index('week'),
                    "options": {
                        "title": "Accuracy Trends",
                        "x_label": "Week",
                        "y_label": "Accuracy %"
                    }
                }
                
                if chart_component:
                    chart_component.render(chart_data)
                else:
                    # Fallback to standard Streamlit
                    st.line_chart(weekly_df.set_index('week'))
            
            # Model contribution
            if 'model_contribution' in improvement_stats:
                st.subheader("Model Contribution")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("OCR Accuracy", f"{improvement_stats['model_contribution'].get('ocr_accuracy', 0):.1f}%")
                
                with col2:
                    st.metric("JSON Generation Accuracy", f"{improvement_stats['model_contribution'].get('json_accuracy', 0):.1f}%")
        else:
            st.info("No improvement metrics available")
    
    def run(self):
        """Run the Streamlit app"""
        st.set_page_config(
            page_title="SkillLab Review",
            page_icon="📋",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Render sidebar
        page = self.render_sidebar()
        
        # Render selected page
        if page == "Dashboard":
            self.render_dashboard()
        elif page == "Review Documents":
            self.render_review_page()
        elif page == "Performance Analysis":
            self.render_analysis_page()

def main():
    """Main entry point for the Streamlit app"""
    # Synchronize databases before starting the app
    try:
        # Load documents from filesystem first to ensure all are in the database
        docs_loaded = load_documents_from_filesystem()
        logger.info(f"Loaded {docs_loaded} documents from filesystem.")
        
        # Sync between databases
        docs_synced, issues_synced = sync_review_data()
        logger.info(f"Database sync complete. Synced {docs_synced} documents and {issues_synced} issues.")
    except Exception as e:
        logger.error(f"Error preparing databases: {str(e)}")
    
    # Create and run app with Web UI type
    app = ReviewApp(UIType.WEB)
    app.run()

if __name__ == "__main__":
    main()