# Model comparison

Test set: 50 reviewed photos (Bingsu/Human_Action_Recognition). Time = seconds per photo on the Pi 5 (warm).

| Model | Prompt | Accuracy | drinking | eating | running | sitting | sleeping | typing | s/photo | Peak RAM |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-VL-2B-Instruct | describe | 88% (44/50) | 8/9 | 8/9 | 5/6 | 7/9 | 9/9 | 7/8 | 6.1 | 3291 MB |
| InternVL3-1B-Instruct | describe | 86% (43/50) | 9/9 | 9/9 | 5/6 | 5/9 | 9/9 | 6/8 | 10.9 | 1726 MB |
| LFM2-VL-450M | describe | 82% (41/50) | 9/9 | 6/9 | 5/6 | 5/9 | 9/9 | 7/8 | 1.5 | 1041 MB |
| SmolVLM2-500M-Video-Instruct | describe | 80% (40/50) | 7/9 | 8/9 | 4/6 | 6/9 | 9/9 | 6/8 | 7.1 | 1544 MB |
| SmolVLM-256M-Instruct | list | 76% (38/50) | 8/9 | 7/9 | 5/6 | 5/9 | 8/9 | 5/8 | 6.0 | 974 MB |
| SmolVLM2-500M-Video-Instruct | list | 70% (35/50) | 6/9 | 5/9 | 4/6 | 7/9 | 8/9 | 5/8 | 6.3 | 1717 MB |
| SmolVLM-256M-Instruct | describe | 70% (35/50) | 7/9 | 8/9 | 5/6 | 3/9 | 7/9 | 5/8 | 6.0 | 848 MB |
| SmolVLM-500M-Instruct | list | 68% (34/50) | 7/9 | 9/9 | 4/6 | 3/9 | 6/9 | 5/8 | 6.7 | 1672 MB |
| SmolVLM-500M-Instruct | describe | 62% (31/50) | 6/9 | 6/9 | 4/6 | 4/9 | 7/9 | 4/8 | 6.6 | 1523 MB |
| InternVL3-1B-Instruct | list | 46% (23/50) | 4/9 | 1/9 | 6/6 | 5/9 | 0/9 | 7/8 | 10.2 | 2071 MB |
| LFM2-VL-450M | list | 44% (22/50) | 0/9 | 4/9 | 4/6 | 9/9 | 5/9 | 0/8 | 1.2 | 2416 MB |
