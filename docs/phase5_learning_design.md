# Phase 5 learning design

This document was written before the learning run.

## Question

Can a very small learned action readout, driven only by the fixed connectome-derived visual-projection response, improve orientation and approach to a visible target over an untrained policy?

## Candidate mechanisms

| Candidate | Changes | Biological plausibility | Cost / problem |
|---|---|---|---|
| Plastic scaling on all retained synapses | Millions of existing weights | Broadly related to synaptic plasticity, but the specific rule is unsupported here | High cost and high risk of destroying the Phase 3.5 stability result |
| STDP-like edge updates | Existing edge weights from spike timing | Requires meaningful spike timing and parameters not present in the bounded-rate model | Not justified by current data |
| Reward-modulated plasticity in a restricted subgraph | Selected existing weights | Potentially defensible in principle | Requires choosing a biological locus and neuromodulatory rule without evidence |
| Small learned interface/readout | Only action-logit weights after the validated readout | Weak biological claim; transparent engineering baseline | Cheapest, easiest to isolate, does not mean the connectome itself learned |

## Selected mechanism

A linear softmax policy is learned over four fixed summary features: bias, normalized left activity, normalized right activity, and normalized total activity from the annotated `visual_projection` readout. Its 4x4 action-weight matrix is the only learned parameter. The original graph, retained edges, normalized synaptic weights, neuron update, sensory cohorts, and readout population remain fixed.

Training uses episodic REINFORCE with a moving scalar baseline. This is an engineering choice, not a model of fly synaptic physiology. The phrase “the fly connectome learned” would be misleading; the accurate phrase is “a small policy readout learned from fixed connectome-derived features.”

## Task and reward

Training uses the existing bounded 2D target world as a fast proxy with the same five-sector observation and four-action space as Minecraft. Neural responses for the six possible observations are computed once by the full 139,255-neuron model and cached; this is exact because every observation window resets to zero in the Phase 4 protocol.

Targets are sampled at varied distance and bearing. Episodes last at most 24 steps and succeed within distance 1.0. Reward receives old/new agent pose and the target pose, but it does not receive sector labels or a desired action:

```text
reward = (old_distance - new_distance)
       + 0.20 * (abs(old_angle_error) - abs(new_angle_error))
       - 0.01 step cost
       - 0.02 * (translation + absolute heading change)
       + 3.0 on first reaching distance <= 1.0
```

The reward evaluates progress and movement cost. It never says “left target means turn left” or supplies an action label.

## Prespecified experiment

- Three independent training seeds.
- 400 training episodes per seed, at most 24 steps each.
- Discount factor 0.97, learning rate 0.025, exponential baseline retention 0.95, and per-episode gradient-norm clipping at 5.0.
- Targets sampled continuously within the front 140 degrees and distances 4 to 8.
- Held-out evaluation: 200 new targets per seed from separate RNG streams.
- Baseline: untrained uniform stochastic policy evaluated with fixed seeds.
- Controls: target-absent episodes, exact same-seed rerun, and shuffled-neural-feature evaluation.
- Checkpoints: untrained and each trained weight matrix retained separately.

Before seeing evaluation results, success is defined as both:

1. at least a 20% reduction in mean final target distance versus the untrained baseline; and
2. at least a 25 percentage-point increase in success rate, aggregated across held-out episodes.

The hidden-target control must not be presented as target-seeking success. Shuffled-feature performance is used to test whether improvement depends on the connectome-derived sector response rather than only an action prior.

## Bounded follow-up after the first failed gate

The prespecified 400-episode run met the distance criterion but missed the success-rate criterion and showed a strong action-prior confound under shuffled features. Its metrics, logs, and checkpoints are preserved as `learning_validation_attempt1_400ep.json`, `experiments/phase5/attempt1_400ep/`, and `checkpoints/phase5/attempt1_400ep/`. Success rates by 50-episode block were still generally higher late in training than at the start. One bounded follow-up is therefore registered: 2,000 episodes per seed with the same seeds, task distribution, reward, optimizer, held-out evaluation, controls, and pass thresholds. No further search follows if that run fails.

## Runtime estimate

Six full neural windows require roughly one second after graph loading. Training and evaluation then use cached fixed features and should take well under one minute for all three seeds. A large online deep-RL run is neither necessary nor justified.
