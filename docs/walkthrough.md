# 3-minute walkthrough: Experimentation Platform

A timed script for a Loom recording of about 3 minutes (screen plus camera bubble, 1080p). Say it in your own words; the lines are a guide, not a teleprompter.

**Open these tabs before you press record:** README, `output/new_checkout.png`, `experiments/generate.py`, `experiments/stats.py`, `experiments/analyze.py`, `output/readout.md`, `tests/test_experiments.py`, GitHub Actions.

| Time | On screen | What to say |
|---|---|---|
| 0:00–0:20 | Portfolio card, then the README headline | An A/B test is only useful if it ends in a decision people trust. This one ends in two: ship the new checkout, and refuse to report a second test because its data is broken. |
| 0:20–0:40 | `experiments/generate.py` | Both experiments are simulated with known truth, so I can check the method: a planted 4% conversion lift, and a planted logging bug that drops low-engagement users from treatment. |
| 0:40–1:05 | `stats.py`: the SRM check | First, validity. A chi-square test on the arm sizes. The banner test fails it, p of 7 times ten to the minus 5, so every number from it would be biased and the readout won't report one. |
| 1:05–1:30 | `stats.py`: proportion test, `new_checkout.png` | The primary metric is conversion, with a confidence interval on relative lift: plus 6.0%, from plus 1.7 to plus 10.2. The interval contains the true 4%. |
| 1:30–1:55 | `stats.py`: CUPED | CUPED adjusts revenue for each user's pre-experiment spend. It cuts variance by 68%, like running with much more traffic, without biasing the estimate. |
| 1:55–2:20 | `analyze.py`: guardrail and decision rule | Ship only if conversion is significant, revenue is positive and page load hasn't regressed more than 2%. That turns the statistics into a call a VP can act on: about $670k a year. |
| 2:20–2:40 | `output/readout.md`: power | And before the next launch: to detect a 3% lift we need 161,000 users per arm. |
| 2:40–3:00 | `tests/`, then the README top | Six tests check the statistics directly, including the textbook sample-size value, and that the healthy test ships and the broken one is refused. Links are under the video. |

## Recording checklist
- Close email, chat and notifications. Zoom the browser to 125% so code is readable.
- Run `python -m experiments.analyze` once before recording so the outputs are fresh.
- Keep to one take per section; Loom lets you trim. Aim for 2:45 to 3:10.
- Show real numbers on screen as you say them; never estimate on camera.
- Say "simulated experiments with known ground truth" when you introduce the data.

## After recording
1. Copy the Loom share link.
2. In `README.md`, replace the walkthrough line with `- [x] [3-minute Loom walkthrough](<your Loom link>)` and add the link under the title.
3. Add the link to this project's card on saigwe.github.io.
