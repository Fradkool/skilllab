"""
Train Donut module for SkillLab
Fine-tunes Donut model on resume data
"""

import os
import json
import time
from datetime import datetime
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    DonutProcessor, 
    VisionEncoderDecoderModel, 
    VisionEncoderDecoderConfig,
    Seq2SeqTrainer, 
    Seq2SeqTrainingArguments,
    default_data_collator
)
from PIL import Image
from typing import Dict, List, Any, Optional, Union, Tuple

from utils.logger import setup_logger
from utils.gpu_monitor import GPUMonitor

logger = setup_logger("train_donut")

class ResumeDonutDataset(Dataset):
    """Dataset for Donut resume extraction fine-tuning"""
    
    def __init__(
        self, 
        dataset_dir: str,
        processor: DonutProcessor,
        max_length: int = 1024,
        ignore_id: int = -100,
        task_prompt: str = "<s_docvqa><s_resume_extraction>"
    ):
        """
        Initialize Resume Donut Dataset
        
        Args:
            dataset_dir: Directory with dataset
            processor: Donut processor
            max_length: Maximum length for tokenizer
            ignore_id: Ignore ID for padding
            task_prompt: Task prompt for Donut
        """
        self.dataset_dir = dataset_dir
        self.processor = processor
        self.max_length = max_length
        self.ignore_id = ignore_id
        self.task_prompt = task_prompt
        
        # Load dataset index
        self.samples = []
        index_path = os.path.join(os.path.dirname(dataset_dir), f"{os.path.basename(dataset_dir)}_index.txt")
        
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                json_files = [line.strip() for line in f.readlines()]
            
            for json_file in json_files:
                json_path = os.path.join(dataset_dir, json_file)
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    image_path = os.path.join(dataset_dir, metadata.get("image_path", ""))
                    
                    if os.path.exists(image_path):
                        self.samples.append({
                            "image_path": image_path,
                            "gt_parse": metadata.get("gt_parse", ""),
                            "task_prompt": metadata.get("task_prompt", task_prompt)
                        })
                except Exception as e:
                    logger.error(f"Error loading sample {json_file}: {str(e)}")
        
        logger.info(f"Loaded {len(self.samples)} samples from {dataset_dir}")
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Dict[str, Any]:
        """Get a sample for training"""
        sample = self.samples[idx]
        
        # Load and process image
        image = Image.open(sample["image_path"]).convert("RGB")
        pixel_values = self.processor(image, return_tensors="pt").pixel_values.squeeze()
        
        # Add task prompt to ground truth
        gt = sample["task_prompt"] + sample["gt_parse"] + "</s>"
        
        # Tokenize ground truth with processor
        target_encoding = self.processor.tokenizer(
            gt,
            padding="max_length",
            max_length=self.max_length,
            truncation=True,
            return_tensors="pt"
        )
        
        # Replace padding with ignore_id
        labels = target_encoding.input_ids.squeeze()
        labels[labels == self.processor.tokenizer.pad_token_id] = self.ignore_id
        
        return {
            "pixel_values": pixel_values,
            "labels": labels,
            "target_text": gt
        }

class DonutTrainer:
    """Trains Donut model on resume data"""
    
    def __init__(
        self,
        dataset_dir: str = "data/donut_dataset",
        output_dir: str = "models/donut_finetuned",
        pretrained_model: str = "naver-clova-ix/donut-base",
        max_epochs: int = 5,
        batch_size: int = 4,
        learning_rate: float = 5e-5,
        weight_decay: float = 0.01,
        gpu_monitor: Optional[GPUMonitor] = None
    ):
        """
        Initialize Donut Trainer
        
        Args:
            dataset_dir: Directory with dataset
            output_dir: Directory to save fine-tuned model
            pretrained_model: Pre-trained model to use
            max_epochs: Maximum number of epochs
            batch_size: Batch size for training
            learning_rate: Learning rate
            weight_decay: Weight decay
            gpu_monitor: Optional GPU monitor for tracking GPU usage
        """
        logger.info(f"Initializing Donut Trainer (Model: {pretrained_model}, Epochs: {max_epochs})")
        self.dataset_dir = dataset_dir
        self.output_dir = output_dir
        self.pretrained_model = pretrained_model
        self.max_epochs = max_epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.gpu_monitor = gpu_monitor
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Set device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        
        # Training paths
        self.train_dir = os.path.join(dataset_dir, "train")
        self.val_dir = os.path.join(dataset_dir, "validation")
        
        # Check if dataset exists
        if not os.path.exists(self.train_dir) or not os.path.exists(self.val_dir):
            logger.error(f"Dataset not found at {dataset_dir}")
            raise FileNotFoundError(f"Dataset not found at {dataset_dir}")
    
    def setup_model_and_processor(self) -> Tuple[VisionEncoderDecoderModel, DonutProcessor]:
        """
        Set up Donut model and processor
        
        Returns:
            Tuple of (model, processor)
        """
        logger.info("Setting up Donut model and processor")
        start_time = time.time()
        
        # Check GPU availability
        if not torch.cuda.is_available():
            logger.warning("CUDA not available. Training will be extremely slow on CPU.")
        
        if self.gpu_monitor:
            self.gpu_monitor.start_monitoring("model_setup")
        
        # Load processor
        processor = DonutProcessor.from_pretrained(self.pretrained_model)
        
        # Load model configuration
        config = VisionEncoderDecoderConfig.from_pretrained(self.pretrained_model)
        
        # Adjust configuration for fine-tuning
        config.encoder.num_hidden_layers = 8  # Reduce encoder layers to save VRAM
        config.decoder.max_position_embeddings = 1024
        config.decoder.temperature = 1.0  # Adjust decoding temperature
        
        # Load model with adjusted configuration
        model = VisionEncoderDecoderModel.from_pretrained(
            self.pretrained_model,
            config=config
        )
        
        # Resize embedding layer for new tokens if needed
        model.decoder.resize_token_embeddings(len(processor.tokenizer))
        
        # Set decoder start token to the task prompt start token
        task_start_token = processor.tokenizer.convert_tokens_to_ids("<s_docvqa>")
        model.config.decoder_start_token_id = task_start_token
        model.config.pad_token_id = processor.tokenizer.pad_token_id
        model.config.vocab_size = model.config.decoder.vocab_size
        
        # Create task-specific vocabulary for output projection to save memory
        unused_vocab_slots = max(0, processor.tokenizer.vocab_size - len(processor.tokenizer))
        if unused_vocab_slots > 0:
            logger.info(f"Reducing vocabulary size from {processor.tokenizer.vocab_size} to {len(processor.tokenizer)}")
            model.decoder.resize_token_embeddings(len(processor.tokenizer))
            config.vocab_size = len(processor.tokenizer)
        
        # Enable gradient checkpointing to save memory
        model.encoder.gradient_checkpointing_enable()
        model.decoder.gradient_checkpointing_enable()
        
        elapsed = time.time() - start_time
        logger.info(f"Model and processor setup completed in {elapsed:.2f}s")
        
        if self.gpu_monitor:
            self.gpu_monitor.stop_monitoring("model_setup")
        
        return model, processor
    
    def train(self) -> Dict[str, Any]:
        """
        Train Donut model
        
        Returns:
            Dictionary with training results
        """
        logger.info("Starting Donut training")
        start_time = time.time()
        
        # Set up model and processor
        model, processor = self.setup_model_and_processor()
        
        # Create datasets
        train_dataset = ResumeDonutDataset(
            dataset_dir=self.train_dir,
            processor=processor
        )
        
        eval_dataset = ResumeDonutDataset(
            dataset_dir=self.val_dir,
            processor=processor
        )
        
        logger.info(f"Created datasets: {len(train_dataset)} train, {len(eval_dataset)} validation samples")
        
        # Configure training arguments
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        training_args = Seq2SeqTrainingArguments(
            output_dir=os.path.join(self.output_dir, f"checkpoints_{timestamp}"),
            overwrite_output_dir=True,
            max_steps=self.max_epochs * len(train_dataset) // self.batch_size,
            per_device_train_batch_size=self.batch_size,
            per_device_eval_batch_size=self.batch_size,
            learning_rate=self.learning_rate,
            weight_decay=self.weight_decay,
            adam_beta1=0.9,
            adam_beta2=0.999,
            adam_epsilon=1e-8,
            lr_scheduler_type="cosine",
            warmup_ratio=0.1,
            fp16=True,  # Use mixed precision to save memory
            logging_steps=100,
            save_steps=len(train_dataset) // self.batch_size,  # Save once per epoch
            eval_steps=len(train_dataset) // self.batch_size,  # Evaluate once per epoch
            save_total_limit=2,  # Keep only the last 2 checkpoints
            evaluation_strategy="steps",
            predict_with_generate=True,
            generation_max_length=processor.tokenizer.model_max_length,
            generation_num_beams=1,
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            gradient_accumulation_steps=4,  # Accumulate gradients to simulate larger batch sizes
            report_to="none"  # Disable wandb, tensorboard, etc.
        )
        
        # Initialize trainer
        trainer = Seq2SeqTrainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=default_data_collator,
            tokenizer=processor.tokenizer
        )
        
        # Train model
        logger.info("Starting training")
        if self.gpu_monitor:
            self.gpu_monitor.start_monitoring("training")
        
        # Get monitoring integration if available
        monitoring = None
        try:
            from monitor.integration import get_monitoring
            monitoring = get_monitoring()
        except ImportError:
            pass
        
        # Add custom callback for monitoring integration
        class MonitoringCallback(transformers.TrainerCallback):
            def on_epoch_end(self, args, state, control, **kwargs):
                if monitoring:
                    monitoring.record_training_progress(
                        epoch=state.epoch,
                        total_epochs=trainer.args.num_train_epochs,
                        metrics={
                            "loss": state.log_history[-1].get("loss", 0.0),
                            "val_loss": state.log_history[-1].get("eval_loss", 0.0) if len(state.log_history) > 0 and "eval_loss" in state.log_history[-1] else 0.0
                        }
                    )
                    
        if monitoring:
            trainer.add_callback(MonitoringCallback())
        
        train_result = trainer.train()
        
        if self.gpu_monitor:
            self.gpu_monitor.stop_monitoring("training")
        
        # Save final model
        logger.info("Saving final model")
        trainer.save_model(self.output_dir)
        processor.save_pretrained(self.output_dir)
        
        # Save training metrics
        metrics = train_result.metrics
        trainer.log_metrics("train", metrics)
        trainer.save_metrics("train", metrics)
        trainer.save_state()
        
        # Evaluate model
        logger.info("Evaluating model")
        if self.gpu_monitor:
            self.gpu_monitor.start_monitoring("evaluation")
        
        eval_metrics = trainer.evaluate(
            max_length=processor.tokenizer.model_max_length,
            num_beams=1
        )
        
        if self.gpu_monitor:
            self.gpu_monitor.stop_monitoring("evaluation")
        
        trainer.log_metrics("eval", eval_metrics)
        trainer.save_metrics("eval", eval_metrics)
        
        elapsed = time.time() - start_time
        logger.info(f"Training completed in {elapsed:.2f}s")
        
        # Return metrics
        results = {
            "train_metrics": metrics,
            "eval_metrics": eval_metrics,
            "training_time": elapsed,
            "model_path": self.output_dir,
            "timestamp": timestamp
        }
        
        # Save results summary
        summary_path = os.path.join(self.output_dir, "training_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        return results

if __name__ == "__main__":
    # Test the Donut trainer
    from utils.gpu_monitor import GPUMonitor
    
    gpu_monitor = GPUMonitor()
    trainer = DonutTrainer(gpu_monitor=gpu_monitor)
    
    try:
        results = trainer.train()
        print(f"Training completed with eval loss: {results['eval_metrics'].get('eval_loss', 'N/A')}")
    except Exception as e:
        logger.error(f"Training failed: {str(e)}")