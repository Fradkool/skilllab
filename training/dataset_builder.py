"""
Dataset Builder module for SkillLab
Prepares dataset for training Donut model
"""

import os
import json
import glob
import shutil
from typing import Dict, List, Any, Tuple, Optional
from PIL import Image

from utils.logger import setup_logger

logger = setup_logger("dataset_builder")

class DonutDatasetBuilder:
    """Prepares dataset for training Donut model from validated JSONs and images"""
    
    def __init__(
        self, 
        validated_json_dir: str = "data/output/validated_json",
        donut_dataset_dir: str = "data/donut_dataset",
        train_val_split: float = 0.8,
        task_name: str = "resume_extraction"
    ):
        """
        Initialize Donut Dataset Builder
        
        Args:
            validated_json_dir: Directory with validated JSONs
            donut_dataset_dir: Directory to save Donut dataset
            train_val_split: Train/validation split ratio (0.0-1.0)
            task_name: Task name for Donut training
        """
        logger.info(f"Initializing Donut Dataset Builder (Split: {train_val_split})")
        self.validated_json_dir = validated_json_dir
        self.donut_dataset_dir = donut_dataset_dir
        self.train_val_split = train_val_split
        self.task_name = task_name
        
        # Create dataset directories
        self.train_dir = os.path.join(donut_dataset_dir, "train")
        self.val_dir = os.path.join(donut_dataset_dir, "validation")
        
        os.makedirs(self.train_dir, exist_ok=True)
        os.makedirs(self.val_dir, exist_ok=True)
        
        # Templates for JSON-to-docstring conversion for Donut
        self.task_prompt = f"<s_docvqa><s_{task_name}>"
        self.response_template = "<s_answer>{{ANSWER}}</s_answer>"
    
    def _format_json_for_donut(self, json_data: Dict[str, Any]) -> str:
        """
        Format JSON data for Donut training (convert to string representation)
        
        Args:
            json_data: JSON data to format
            
        Returns:
            Formatted string for Donut
        """
        # Convert experience entries to better format for Donut
        if json_data.get("Experience"):
            for exp in json_data["Experience"]:
                exp_str = []
                for key, value in exp.items():
                    if value:
                        exp_str.append(f"{key}: {value}")
                exp["donut_str"] = ", ".join(exp_str)
        
        # Build a formatted string that Donut can learn
        lines = []
        
        # Add name, email, phone, position if available
        for field in ["Name", "Email", "Phone", "Current_Position"]:
            if json_data.get(field):
                lines.append(f"{field}: {json_data[field]}")
        
        # Add skills if available
        if json_data.get("Skills") and len(json_data["Skills"]) > 0:
            skills_str = ", ".join(json_data["Skills"])
            lines.append(f"Skills: {skills_str}")
        
        # Add experience if available
        if json_data.get("Experience") and len(json_data["Experience"]) > 0:
            lines.append("Experience:")
            for exp in json_data["Experience"]:
                if exp.get("donut_str"):
                    lines.append(f"  - {exp['donut_str']}")
                else:
                    company = exp.get("company", "")
                    title = exp.get("title", "")
                    years = exp.get("years", "")
                    lines.append(f"  - {company}, {title}, {years}")
        
        # Join all lines
        return "\n".join(lines)
    
    def _prepare_sample(self, validated_file: str) -> Optional[Tuple[str, str, List[str]]]:
        """
        Prepare a sample for Donut dataset
        
        Args:
            validated_file: Path to validated JSON file
            
        Returns:
            Tuple of (sample ID, formatted JSON string, list of image paths)
            or None if invalid
        """
        try:
            # Load validated JSON
            with open(validated_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Skip if not valid
            if not data.get("validation", {}).get("is_valid", False):
                logger.warning(f"Skipping invalid sample: {validated_file}")
                return None
            
            # Get JSON data and image paths
            json_data = data.get("json_data", {})
            image_paths = data.get("image_paths", [])
            
            if not json_data or not image_paths:
                logger.warning(f"Missing JSON data or images: {validated_file}")
                return None
            
            # Generate sample ID from file name
            sample_id = os.path.splitext(os.path.basename(validated_file))[0].replace("_validated", "")
            
            # Format JSON for Donut
            formatted_json = self._format_json_for_donut(json_data)
            
            return sample_id, formatted_json, image_paths
        
        except Exception as e:
            logger.error(f"Error preparing sample {validated_file}: {str(e)}")
            return None
    
    def _copy_and_prepare_images(self, sample_id: str, image_paths: List[str], output_dir: str) -> List[str]:
        """
        Copy and prepare images for Donut dataset
        
        Args:
            sample_id: Sample ID
            image_paths: List of image paths
            output_dir: Output directory
            
        Returns:
            List of new image paths
        """
        new_paths = []
        
        for i, img_path in enumerate(image_paths):
            if not os.path.exists(img_path):
                logger.warning(f"Image not found: {img_path}")
                continue
            
            # For multi-page, use index; for single page use only ID
            new_filename = f"{sample_id}_{i}.jpg" if len(image_paths) > 1 else f"{sample_id}.jpg"
            new_path = os.path.join(output_dir, new_filename)
            
            # Convert to JPEG and save
            try:
                img = Image.open(img_path)
                rgb_img = img.convert('RGB')
                rgb_img.save(new_path, format='JPEG', quality=95)
                new_paths.append(new_path)
            except Exception as e:
                logger.error(f"Error processing image {img_path}: {str(e)}")
        
        return new_paths
    
    def _save_metadata(self, sample_id: str, image_path: str, json_str: str, output_dir: str) -> str:
        """
        Save metadata for Donut dataset
        
        Args:
            sample_id: Sample ID
            image_path: Image path
            json_str: Formatted JSON string
            output_dir: Output directory
            
        Returns:
            Path to metadata file
        """
        # Create metadata file
        metadata_path = os.path.join(output_dir, f"{sample_id}.json")
        
        # Format the answer using the template
        answer_str = self.response_template.format(ANSWER=json_str)
        
        # Create metadata
        metadata = {
            "gt_parse": answer_str,
            "image_path": os.path.basename(image_path),
            "task_prompt": self.task_prompt
        }
        
        # Save metadata
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return metadata_path
    
    def build_dataset(self) -> Dict[str, Any]:
        """
        Build Donut dataset from validated JSONs
        
        Returns:
            Dictionary with dataset statistics
        """
        logger.info(f"Building Donut dataset from {self.validated_json_dir}")
        
        # Find all validated JSON files
        validated_files = glob.glob(os.path.join(self.validated_json_dir, "*_validated.json"))
        if not validated_files:
            logger.warning(f"No validated JSON files found in {self.validated_json_dir}")
            return {
                "total_files": 0,
                "valid_samples": 0,
                "train_samples": 0,
                "val_samples": 0
            }
            
        logger.info(f"Found {len(validated_files)} validated JSON files")
        
        # Statistics
        stats = {
            "total_files": len(validated_files),
            "valid_samples": 0,
            "train_samples": 0,
            "val_samples": 0,
            "multi_page_samples": 0,
            "single_page_samples": 0
        }
        
        # Prepare samples
        valid_samples = []
        for file in validated_files:
            result = self._prepare_sample(file)
            if result:
                valid_samples.append(result)
        
        stats["valid_samples"] = len(valid_samples)
        logger.info(f"Prepared {len(valid_samples)} valid samples")
        
        # Shuffle and split
        import random
        random.shuffle(valid_samples)
        
        split_idx = int(len(valid_samples) * self.train_val_split)
        train_samples = valid_samples[:split_idx]
        val_samples = valid_samples[split_idx:]
        
        stats["train_samples"] = len(train_samples)
        stats["val_samples"] = len(val_samples)
        
        logger.info(f"Split into {len(train_samples)} train and {len(val_samples)} validation samples")
        
        # Process train samples
        self._process_samples(train_samples, self.train_dir, "train", stats)
        
        # Process validation samples
        self._process_samples(val_samples, self.val_dir, "validation", stats)
        
        # Create dataset index files
        self._create_dataset_index(self.train_dir, "train")
        self._create_dataset_index(self.val_dir, "validation")
        
        logger.info(f"Dataset build complete: {stats['train_samples']} train, {stats['val_samples']} validation")
        return stats
    
    def _process_samples(self, samples: List[Tuple], output_dir: str, split: str, stats: Dict[str, Any]) -> None:
        """
        Process samples for a specific split
        
        Args:
            samples: List of sample tuples
            output_dir: Output directory
            split: Split name for logging
            stats: Statistics dictionary to update
        """
        logger.info(f"Processing {len(samples)} {split} samples")
        
        for sample_id, json_str, image_paths in samples:
            # Track multi-page vs single-page
            if len(image_paths) > 1:
                stats["multi_page_samples"] += 1
            else:
                stats["single_page_samples"] += 1
            
            # Copy and prepare images
            new_image_paths = self._copy_and_prepare_images(sample_id, image_paths, output_dir)
            
            if not new_image_paths:
                logger.warning(f"No images processed for sample {sample_id}")
                continue
            
            # For simplicity, we only use the first page for training
            # This is a limitation but simplifies the process
            first_image = new_image_paths[0]
            
            # Save metadata
            self._save_metadata(sample_id, first_image, json_str, output_dir)
    
    def _create_dataset_index(self, dir_path: str, split: str) -> None:
        """
        Create dataset index file for Donut
        
        Args:
            dir_path: Directory path
            split: Split name
        """
        # Find all JSON metadata files
        json_files = glob.glob(os.path.join(dir_path, "*.json"))
        
        # Create index file
        index_path = os.path.join(self.donut_dataset_dir, f"{split}_index.txt")
        
        with open(index_path, 'w', encoding='utf-8') as f:
            for json_file in json_files:
                f.write(os.path.basename(json_file) + "\n")
        
        logger.info(f"Created dataset index for {split} with {len(json_files)} samples: {index_path}")

if __name__ == "__main__":
    # Test the dataset builder
    builder = DonutDatasetBuilder()
    stats = builder.build_dataset()
    print(f"Dataset built with {stats['train_samples']} train and {stats['val_samples']} validation samples")