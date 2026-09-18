# AIJ Robotics: что подгружать как итог

Итоговый `submission.zip` собирается из трёх частей. Готова первая; две
оставшиеся производятся на ваших GPU по фиксированному протоколу организатора.

| Часть архива | Состояние | Кто делает |
|--------------|-----------|------------|
| `README.md`, `requirements.txt`, `generate_dataset.py`, `config.yaml`, `src/` | готово | код в `aij-vla-dataset/` |
| `annotations.jsonl` | генерируется за один запуск | `generate_dataset.py` на реальных данных |
| `smolvlm2/`, `action_expert/` | требуют обучения | пайплайн из `participant.zip` на 16×H100 |

---

## 0. Одной командой

На машине с GPU и доступом к Hugging Face весь цикл делается так:

```bash
unzip aij-vla-dataset-code.zip -d aij-vla-dataset
cd aij-vla-dataset
./src/tools/run_all.sh --participant /path/to/aij_robotics --pilot 50 --dry-run  # посмотреть план
./src/tools/run_all.sh --participant /path/to/aij_robotics                       # выполнить
```

Скрипт скачивает четыре датасета на нужных коммитах, генерирует обучающую
выборку, запускает пайплайн участника и собирает `submission.zip`. Готовые
стадии пропускаются, отдельная стадия — `--stage data|dataset|train|package`.
Вручную остаётся загрузить архив на платформу.

Дальше — те же шаги по отдельности, если нужен контроль на каждом этапе.

## 1. Данные

Скачать четыре набора на указанных в задании коммитах и разложить рядом:

```text
/data/raw/
├── BridgeData2_LeRobot_v3/          b96f7216e3cff58007884656a81584c857c185ae
├── fractal20220817_data_lerobot/    fc006b5dc812220645a2e6dd0b68a0a03bd0ac6c
├── language_table_lerobot_v30/      d54542e0eebf8084edb10e2c67ef5b94bd41fcc4
└── Egocentric-100K/                 fae604b751b25337d6fd8c4c53e595910c28f68f
```

Каталоги с `meta/info.json` подхватываются как LeRobot v3, каталог с видео — как
эгоцентрический источник. Переименовывать ничего не нужно.

## 2. Датасет

```bash
unzip aij-vla-dataset-code.zip -d aij-vla-dataset
cd aij-vla-dataset
pip install -r requirements.txt

# сначала короткая проверка, что всё читается и результат воспроизводим
./src/tools/run_smoke.sh

# пробный прогон на реальных данных: 50 эпизодов с источника
python generate_dataset.py --input /data/raw --output /data/vlm/train.jsonl \
    --config config.yaml --limit-episodes 50

# полный прогон
python generate_dataset.py --input /data/raw --output /data/vlm/train.jsonl \
    --config config.yaml
```

**Что посмотреть в `/data/vlm/train.stats.json` после пробного прогона:**

| Поле | На что смотреть |
|------|-----------------|
| `sources.<имя>.gripper_calibrated` | `false` — калибровка схвата не сошлась, задания про схват для источника не строятся |
| `train.by_source` | все четыре источника представлены |
| `train.by_task` | нет типа задания с нулём примеров там, где он ожидался |
| `train.mcq_letters_by_options` | внутри каждой группы буквы распределены ровно |
| `selection.dropped_by_template_cap` | велико — стоит поднять `language.max_share_per_template` |

Размер регулируется `budget.max_samples`, `budget.max_episodes_per_source` и
`budget.max_samples_per_episode` в `config.yaml`.

## 3. Обучение (пайплайн из `participant.zip`)

В `configs/participant.yaml`:

```yaml
vlm:
  data_path: /data/vlm/train.jsonl
  eval_data_path: /data/vlm/train.val.jsonl
  media_dir: /data/vlm          # рядом должен лежать каталог images/
vla:
  suite: libero
  dataset_dir: /data/vla        # HuggingFaceVLA/libero @ v3.0
```

```bash
./scripts/run_pipeline.sh configs/participant.yaml
./scripts/validate_submission.sh runs/<run>/submission
```

Каталог `images/`, созданный генератором, должен лежать рядом с JSONL: пути в
датасете относительные и резолвятся от `vlm.media_dir`.

## 4. Сборка архива

```bash
./src/tools/make_submission.sh \
    --annotations /data/vlm/train.jsonl \
    --smolvlm2 runs/<run>/submission/smolvlm2 \
    --action-expert runs/<run>/submission/action_expert \
    --output submission.zip
```

Скрипт проверит `annotations.jsonl`, предупредит о недостающих файлах
чекпойнтов и положит в корень архива ровно то, что требует организатор.

## 5. Перед отправкой

- [ ] в корне архива ровно: `README.md`, `requirements.txt`, `generate_dataset.py`, `config.yaml`, `annotations.jsonl`, `src/`, `smolvlm2/`, `action_expert/`;
- [ ] `python src/tools/validate_annotations.py --input annotations.jsonl` — без ошибок;
- [ ] `smolvlm2/` ≈ 2.0 ГБ, `action_expert/` ≈ 1.4 ГБ (в эталонном архиве веса в fp32; вдвое меньший размер означает bf16 — сверьте с протоколом);
- [ ] в `smolvlm2/` есть `config.json`, `model.safetensors`, `generation_config.json`, `processor_config.json`, `tokenizer_config.json`, `tokenizer.json`, `chat_template.jinja`;
- [ ] в `action_expert/` есть `config.json`, `model.safetensors`, `train_config.json`, `policy_preprocessor.json`, `policy_postprocessor.json` и файлы `policy_{pre,post}processor_step_*.safetensors`;
- [ ] генерация повторяется: тот же вход, конфиг и seed дают тот же `annotations.jsonl` (проверяется `run_smoke.sh`);
- [ ] изображения и видео исходных датасетов в архив не копируются.

## 6. Ограничение по времени

На пробных прогонах генератор даёт порядка 40 эпизодов в секунду на 4 воркерах
(кадры в parquet). Чтение из mp4 медленнее, поэтому для Bridge и Fractal
выставьте `runtime.num_workers` по числу ядер. Лимит в 210 минут при этом
остаётся с большим запасом; при необходимости ограничьте
`budget.max_episodes_per_source`.
