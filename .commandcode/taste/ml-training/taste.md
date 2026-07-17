# ml-training
- Use Kaggle (not Colab) for ML model training notebooks. Confidence: 0.60
- For byte-level tokenizers (like ByT5), use dynamic padding via DataCollatorForSeq2Seq instead of static padding='max_length' — static padding on short byte sequences creates extremely sparse loss signals and causes model collapse. Confidence: 0.70
- Don't pass 'tokenizer' to Seq2SeqTrainer constructor — it's not a valid keyword argument; the data collator handles tokenizer needs. Confidence: 0.70
- For Kaggle notebooks, use IPython.display.FileLink for download links — it displays a clear clickable link; don't replace it with shutil.move + print instructions. Confidence: 0.80
- For ML model training (especially GPU-heavy like ByT5), use the existing Colab/Kaggle notebooks instead of training locally on the dev machine. Confidence: 0.90
- When saving bf16-trained T5/ByT5 models, use `safe_serialization=False` — safetensors fails on non-contiguous tensors that result from bf16 training. Confidence: 0.70
