import json, torch, os
import warnings; warnings.filterwarnings('ignore')
from datasets import Dataset
from transformers import (
    AutoTokenizer, AutoModelForSeq2SeqLM,
    Seq2SeqTrainingArguments, Seq2SeqTrainer, DataCollatorForSeq2Seq,
)

with open('pairs.json') as f:
    raw = json.load(f)
pairs = [(d['headword'], d['ipa']) for d in raw if d.get('headword') and d.get('ipa')][:500]
print(f'Using {len(pairs)} pairs')

sources = [h for h,_ in pairs]
targets = [i for _,i in pairs]
dataset = Dataset.from_dict({'source': sources, 'target': targets})
dataset = dataset.train_test_split(test_size=0.05, seed=42)

tok = AutoTokenizer.from_pretrained('google/byt5-small')
model = AutoModelForSeq2SeqLM.from_pretrained('google/byt5-small')
MAX_LEN = 128

def prep(batch):
    mi = tok(batch['source'], max_length=MAX_LEN, truncation=True)
    lbl = tok(text_target=batch['target'], max_length=MAX_LEN, truncation=True)
    mi['labels'] = lbl['input_ids']
    return mi

tokd = dataset.map(prep, batched=True, remove_columns=['source','target'])
dc = DataCollatorForSeq2Seq(tok, model=model, padding=True)

args = Seq2SeqTrainingArguments(
    output_dir='/tmp/byt5_test3', num_train_epochs=5,
    per_device_train_batch_size=8, per_device_eval_batch_size=8,
    learning_rate=5e-5, warmup_steps=30, weight_decay=0.01,
    logging_steps=50, eval_strategy='epoch', save_strategy='epoch',
    save_total_limit=1, load_best_model_at_end=True,
    metric_for_best_model='eval_loss', greater_is_better=False,
    predict_with_generate=True, generation_max_length=MAX_LEN,
    generation_num_beams=4, fp16=False, report_to='none',
)

trainer = Seq2SeqTrainer(
    model=model, args=args,
    train_dataset=tokd['train'], eval_dataset=tokd['test'],
    data_collator=dc, tokenizer=tok,
)

trainer.train()

save_path = '/tmp/ipa_byt5_seh-fonipa'
model.save_pretrained(save_path)
tok.save_pretrained(save_path)
with open(f'{save_path}/metadata.json', 'w') as f:
    json.dump({
        'ipa_writing_system': 'seh-fonipa',
        'base_model': 'google/byt5-small',
        'source_prefix': '',
        'task': 'g2p'
    }, f, indent=2)
print(f'Saved to {save_path}')

model.to('cpu')
model.eval()
for test in 'cat hello sun phoneme abstractedness'.split():
    ids = tok(test, return_tensors='pt')
    with torch.no_grad():
        gen = model.generate(**ids, num_beams=4, max_length=MAX_LEN, early_stopping=True)
    p = tok.decode(gen[0], skip_special_tokens=True)
    print(f'  {test:20s} -> {p}')
print('OK')
