# 🔬 Vision Model Evaluation Logs: GTA 5 Story Mode Benchmarks

> **Model:** `openai/clip-vit-base-patch32` running on Apple Silicon Metal MPS  
> **Hardware Accelerator:** PyTorch Apple Silicon MPS (`device='mps'`)  
> **Objective:** Validate true-positive game feature detection vs routine filler rejection.

---
## 📊 Evaluation Summary Table

| Scenario | Window | Top Vision Prediction | Confidence | Decision | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Scenario 1: Game Loading Screen & Intro** | `10s - 35s` | `game loading screen with rockstar logo and artwork slides` | **42.73%** | 🟢 **ACCEPTED** | Confirmed visual match for PROP_01 (42.73%). Outweighs routine filler (9.69%). |
| **Scenario 2: Character Intro Cutscene (Franklin & Lamar)** | `20s - 45s` | `character introduction cutscene with close up face and dialogue` | **75.53%** | 🟢 **ACCEPTED** | Confirmed visual match for PROP_02 (75.53%). Outweighs routine filler (0.41%). |
| **Scenario 3: Routine Hallway Walking (Negative Test / Filler)** | `90s - 115s` | `character introduction cutscene with close up face and dialogue` | **65.75%** | 🟢 **ACCEPTED** | Confirmed visual match for PROP_02 (65.75%). Outweighs routine filler (6.94%). |
| **Scenario 4: High-Speed Police Chase & Car Race** | `210s - 235s` | `character introduction cutscene with close up face and dialogue` | **71.65%** | 🟢 **ACCEPTED** | Confirmed visual match for PROP_02 (71.65%). Outweighs routine filler (19.17%). |
| **Scenario 5: Convenience Store Robbery Hold-up** | `25s - 50s` | `convenience store robbery with gun aimed at cashier counter` | **88.99%** | 🟢 **ACCEPTED** | Confirmed visual match for PROP_09 (88.99%). Outweighs routine filler (4.859999999999999%). |
