"""Fine-tune a Whisper checkpoint with LoRA on human-verbatim audio labels.

Training dependencies are lazy imports so production does not install PyTorch.
The output includes a merged Transformers checkpoint for later CTranslate2
conversion; it never mutates the currently deployed model.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

from scripts.asr_training.prepare_manifest import load_jsonl, validate_rows


def training_rows(manifest: Path, *, min_train=100, min_validation=20):
    rows = load_jsonl(manifest)
    errors = validate_rows(rows)
    if errors:
        raise ValueError("invalid manifest: " + "; ".join(errors))
    train = [row for row in rows if row["split"] == "train"]
    validation = [row for row in rows if row["split"] == "validation"]
    if len(train) < min_train:
        raise ValueError(f"need at least {min_train} human-transcribed train clips; found {len(train)}")
    if len(validation) < min_validation:
        raise ValueError(f"need at least {min_validation} validation clips; found {len(validation)}")
    root = manifest.parent
    output = {}
    for split, source in (("train", train), ("validation", validation)):
        output[split] = [{
            "sample_id": row["sample_id"],
            "audio": str((root / row["audio_path"]).resolve()),
            "text": row["reference_verbatim"],
        } for row in source]
        missing = [row["audio"] for row in output[split] if not Path(row["audio"]).is_file()]
        if missing:
            raise ValueError(f"{split}: {len(missing)} audio files are missing; first: {missing[0]}")
    return output


def train(args):
    try:
        import torch
        from datasets import Audio, Dataset, DatasetDict
        from peft import LoraConfig, get_peft_model
        from transformers import (
            Seq2SeqTrainer, Seq2SeqTrainingArguments, WhisperForConditionalGeneration,
            WhisperProcessor,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Install backend/requirements-training.txt in an isolated GPU environment"
        ) from exc
    if not torch.cuda.is_available() and not args.allow_non_cuda:
        raise RuntimeError("Whisper large-v3-turbo LoRA requires CUDA; use --allow-non-cuda only for a small smoke test")

    rows = training_rows(
        args.manifest, min_train=args.min_train, min_validation=args.min_validation,
    )
    dataset = DatasetDict({
        split: Dataset.from_list(values).cast_column("audio", Audio(sampling_rate=16000))
        for split, values in rows.items()
    })
    processor = WhisperProcessor.from_pretrained(args.model, language="English", task="transcribe")

    def prepare(sample):
        audio = sample["audio"]
        duration = len(audio["array"]) / audio["sampling_rate"]
        if duration > 30.0:
            raise ValueError(f"{sample['sample_id']}: {duration:.2f}s exceeds Whisper's 30s training window")
        sample["input_features"] = processor.feature_extractor(
            audio["array"], sampling_rate=audio["sampling_rate"],
        ).input_features[0]
        sample["labels"] = processor.tokenizer(sample["text"]).input_ids
        return sample

    dataset = dataset.map(prepare, remove_columns=dataset["train"].column_names)
    model = WhisperForConditionalGeneration.from_pretrained(args.model)
    model.config.forced_decoder_ids = processor.get_decoder_prompt_ids(language="English", task="transcribe")
    model.config.suppress_tokens = []
    model.config.use_cache = False
    model = get_peft_model(model, LoraConfig(
        r=args.lora_rank,
        lora_alpha=args.lora_rank * 2,
        lora_dropout=0.05,
        bias="none",
        target_modules=["q_proj", "v_proj"],
    ))

    @dataclass
    class Collator:
        def __call__(self, features):
            inputs = processor.feature_extractor.pad(
                [{"input_features": feature["input_features"]} for feature in features],
                return_tensors="pt",
            )
            labels = processor.tokenizer.pad(
                [{"input_ids": feature["labels"]} for feature in features],
                return_tensors="pt",
            )
            label_ids = labels["input_ids"].masked_fill(labels.attention_mask.ne(1), -100)
            if (label_ids[:, 0] == processor.tokenizer.bos_token_id).all().cpu().item():
                label_ids = label_ids[:, 1:]
            inputs["labels"] = label_ids
            return inputs

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(args.output),
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        gradient_checkpointing=True,
        fp16=torch.cuda.is_available(),
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=10,
        predict_with_generate=False,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        remove_unused_columns=False,
        report_to=[],
        seed=args.seed,
    )
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        data_collator=Collator(),
        processing_class=processor,
    )
    trainer.train()
    adapter_dir = args.output / "adapter"
    merged_dir = args.output / "merged-transformers"
    model.save_pretrained(adapter_dir)
    model.merge_and_unload().save_pretrained(merged_dir)
    processor.save_pretrained(merged_dir)
    print(f"saved adapter to {adapter_dir} and merged checkpoint to {merged_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="openai/whisper-large-v3-turbo")
    parser.add_argument("--epochs", type=float, default=5.0)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=16)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-train", type=int, default=100)
    parser.add_argument("--min-validation", type=int, default=20)
    parser.add_argument("--allow-non-cuda", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    train(args)


if __name__ == "__main__":
    main()
