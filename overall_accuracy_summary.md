# Model Evaluation Accuracy Table (Spider Full Dataset)

Below is the execution accuracy table for all the models evaluated so far on the full dataset across different prompting methods.

| Prompting Method | Google Gemini 2.5 Flash | Anthropic Claude Haiku 4.5 | Meta LLaMA 3.3 70B Instruct | OpenAI GPT-4o-Mini |
| :--- | :---: | :---: | :---: | :---: |
| **QDecomp** | 77.76% (804/1034) | 72.34% (748/1034) | 73.02% (755/1034) | 69.73% (721/1034) |
| **SCoT** | 77.47% (801/1034) | 67.89% (702/1034) | 64.80% (670/1034) | 54.64% (565/1034) |
| **QD-InterCol** | 77.47% (801/1034) | 73.89% (764/1034) | 75.44% (780/1034) | 70.70% (731/1034) |
| **Standard** | 76.11% (787/1034) | 72.82% (753/1034) | 73.31% (758/1034) | 71.08% (735/1034) |
| **CoT** | 73.89% (764/1034) | 69.83% (722/1034) | 68.28% (706/1034) | 65.86% (681/1034) |

> [!NOTE]  
> All models and methods have now been fully evaluated. The results above represent the final execution accuracy on the Spider full dataset.
